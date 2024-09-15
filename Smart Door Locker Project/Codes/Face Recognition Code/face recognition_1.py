import sqlite3
import cv2
import os
import time
import serial
import tkinter as tk
from sklearn.metrics.pairwise import cosine_similarity
from tkinter import messagebox, simpledialog


# Define paths
DB_FILE = 'user_data.db'
data_path = 'training_data' 

# Step 1: setup the code 
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')



cap = cv2.VideoCapture(0) #cam opened

notify=serial.Serial(port='COM8',baudrate=9600,timeout=0.1) #connection started with arduino


#function to change the live image to gray scale and detect the face
def preprocess_image():
  while True: #so he keeps searching for a face till he finds one
    ret, frame = cap.read()
    if not ret:
        raise Exception("Could not read frame")
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    if len(faces) > 0:
     (x, y, w, h) = faces[0]  # Example: take the first detected face
     face = gray[y:y + h, x:x + w]
     cv2.imwrite('person photo.jpg',frame)
     face_resized=resize_image(face)
     if face_resized is not None:
         break

  return face_resized,x,y,w,h


#function to resize the image bc the cosine similarity doesnt work with huge image data
def resize_image(image):
    target_size = (64, 128)
    resized_image = cv2.resize(image, target_size)
    return resized_image



# Function to compute the feature vector (using Histogram of Oriented Gradients - HOG)
def compute_feature_vector(image):
    hog = cv2.HOGDescriptor()
    return hog.compute(image).flatten()


#the function that prepares the database images for face recognition and comparsion
def load_folder_images(folder_path):
    feature_vectors = []

    for filename in os.listdir(folder_path):
        if filename.endswith('.jpg'):
            image_path = os.path.join(folder_path, filename) ##reading images to compare
            image = cv2.imread(image_path)

            if image is not None:
                preprocessed_image = resize_image(image)
                feature_vector = compute_feature_vector(preprocessed_image)
                feature_vectors.append(feature_vector)

    return feature_vectors


#the main face recognition part
def compare_live_image_to_folders(): 
    preprocessed_live_image,x,y,w,h = preprocess_image()
    live_feature_vector = compute_feature_vector(preprocessed_live_image)

    conn=sqlite3.connect(DB_FILE) #open the database to get the users names and image folders we will compare with
    cursor=conn.cursor()
    cursor.execute("SELECT image_path FROM users")
    rows=cursor.fetchall()

    owners_num=len(rows)
    images_paths=[]
    for row in rows:
        images_paths.append(row[0])

    found=False

    for j in range (owners_num):
     folder_path=images_paths[j] #perpare the images folder

     cursor.execute('SELECT user_name FROM users WHERE image_path = ?',(images_paths[j],))
     name=cursor.fetchone()[0] #prepare the name to display if found

     folder_feature_vectors= load_folder_images(folder_path) #load the folders to check

     for  folder_feature_vector in (folder_feature_vectors):
        similarity = cosine_similarity([live_feature_vector], [folder_feature_vector])[0][0]

        if similarity > 0.9:  # Threshold for similarity (adjust so it works better)
            found=True
            #print(f"Match found: {image_files[i]} with similarity {similarity:.2f}") # for test before we change it to green and red box
            break
     if found:
         break
    conn.close()

    #the check and display part
    if not found:
      person_photo=cv2.imread('person photo.jpg') # just an image of the person but not a live video (a part to edit)
      cv2.rectangle(person_photo, (x, y), (x + w, y + h), (0, 0, 255), 2)
      cv2.putText(person_photo, "unKnown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
    else:
      person_photo=cv2.imread('person photo.jpg') # just an image of the person but not a live video (a part to edit)
      cv2.rectangle(person_photo, (x, y), (x + w, y + h), (0, 255, 0), 2)
      cv2.putText(person_photo, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.imshow('the person on the door',person_photo)
    return found


    
#step 1:collecting the data
def collect_training_data(user_id, user_name):
    print("Starting data collection...")  # Debugging print

    if not cap.isOpened():
        print("Error: Camera could not be accessed")
        return

    count = 0

    # Create directories for saving the images if they do not exist
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        print(f"Created directory: {data_path}")

    user_folder = os.path.join(data_path, user_name)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
        print(f"Created user folder: {user_folder}")

    while count < 50:  # Collect 50 images per user
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame from camera")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            count += 1
            face = gray[y:y + h, x:x + w]
            cv2.imwrite(f'{user_folder}/{user_name}_{count}.jpg', face)  # Save face images
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, f'Collecting Data {count}/50', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 0, 0), 2)

        cv2.imshow('Collecting Training Data', frame)

        if cv2.waitKey(200) & 0xFF == ord('q'):
            print("Data collection manually stopped.")
            break

    cv2.destroyAllWindows()
    print(f"Collected {count} images for user {user_name}.")

    return user_folder # to add it to the database


# Step 2: Initialize the SQLite database and create the table
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT NOT NULL,
            image_path TEXT 
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# Step 3: Function to add a new user to the database
def add_user_to_db(user_id, user_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (user_id, user_name) VALUES (?, ?)',
                       (user_id, user_name))
        conn.commit()
        image_source=collect_training_data(user_id, user_name)
        cursor.execute('UPDATE users SET image_path = ? WHERE user_id = ?',
                       (image_source,user_id))
        conn.commit()
        
        messagebox.showinfo("Success", f"User {user_name} added successfully!")

    except sqlite3.IntegrityError:
        messagebox.showerror("Error", f"User with ID {user_id} already exists.")

    # collecting the data and getting the path to the images of the user

    conn.close()


# Step 4: Function to delete a user from the database
def delete_user_from_db(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    messagebox.showinfo("Success", f"User with ID {user_id} removed successfully.")


# Step 5: Function to open the door
def open_the_door():
    ######connection part
    notify.write(b'o')


############################################################################


 # GUI Functions
def add_new_user():
    try:
        user_id = int(entry_user_id.get())
        user_name = entry_user_name.get()
        add_user_to_db(user_id, user_name)
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid user ID.")


def delete_user():
    try:
        user_id = int(entry_user_id.get())
        delete_user_from_db(user_id)
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid user ID.")


def update_password():
    notify.write(b'u')
    messagebox.showinfo("alert", "type the new password on the keypad!")
        
   
# Step 6: Set up the GUI

def setup_gui_strange():

   root=tk.Tk()
   root.title("strange on the door")

   # Buttons for Adding user or just open the door
   tk.Button(root, text="Add User and open door", command=setup_gui_users).grid(row=1, column=0, padx=10, pady=10)
   tk.Button(root, text="just open door ", command=open_the_door).grid(row=1, column=1, padx=10, pady=10)
   
   root.mainloop()


def setup_gui_users():

    #open the door
    notify.write(b'o') #notify the arduino to open the door
    
    # Set up the main window
    root = tk.Tk()
    root.title("Smart Home User Management")

    # Labels and Entries for User ID, Name, and Password
    tk.Label(root, text="User ID:").grid(row=0, column=0, padx=10, pady=5)
    global entry_user_id
    entry_user_id = tk.Entry(root)
    entry_user_id.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(root, text="User Name:").grid(row=1, column=0, padx=10, pady=5)
    global entry_user_name
    entry_user_name = tk.Entry(root)
    entry_user_name.grid(row=1, column=1, padx=10, pady=5)


    # Buttons for Adding, Deleting, and Updating Users
    tk.Button(root, text="Add User", command=add_new_user).grid(row=2, column=0, padx=10, pady=10)
    tk.Button(root, text="Delete User", command=delete_user).grid(row=2, column=1, padx=10, pady=10)
    tk.Button(root, text="Update Password", command=update_password).grid(row=3, column=0,columnspan=2,  padx=10,
                                                                          pady=10)
    # Run the GUI
    root.mainloop()




# the code start

def main_fn():
  initialize_db()
  recognised=False
  count=0
  while count<30:
   found=compare_live_image_to_folders()
   if found :
       recognised=True
   count+=1
   if cv2.waitKey(100) & 0xFF == ord('q'):
    print("Face redognition manually stopped.")
    break
  if recognised:
      setup_gui_users()
  else:
      setup_gui_strange()  
  cv2.destroyAllWindows()
  cap.release()
main_fn()