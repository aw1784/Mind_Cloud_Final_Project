#the libraries and modules we will use
import sqlite3
import cv2
import os
import serial
import tkinter as tk
from sklearn.metrics.pairwise import cosine_similarity
from tkinter import messagebox


# Define paths
DB_FILE = 'user_data.db'
data_path = 'training_data' 

# Step 1: setup the code 
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') #the Haarcascade calssifier used  for face detection

cap = cv2.VideoCapture(0) #cam opened

notify=serial.Serial(port='COM8',baudrate=9600,timeout=0.1) #connection started with arduino


#function to change the live image to gray scale and detect the face
def preprocess_image():
  while True: #so he keeps searching for a face till he finds one
    ret, frame = cap.read()
    if not ret:
        raise Exception("Could not read frame")
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #changing the color
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5) #detecting the face
    if len(faces) > 0:
     (x, y, w, h) = faces[0]  # take the dimensions of first detected face
     face = gray[y:y + h, x:x + w] #cut the photo to fit teh face
     cv2.imwrite('person photo.jpg',frame) #save the frame for displaying and the colored boxes
     face_resized=resize_image(face) #resizng for the computing of feature vector
     if face_resized is not None: #check that we really detected a face
         break

  return face_resized,x,y,w,h


#function to resize the image 
def resize_image(image):
    target_size = (64, 128)
    resized_image = cv2.resize(image, target_size)
    return resized_image



# Function to compute the feature vector (using Histogram of Oriented Gradients - HOG)
def compute_feature_vector(image):
    hog = cv2.HOGDescriptor() #creating instatition of the class that we will use to commpute the feature vector
    return hog.compute(image).flatten() #compute the feature vector but because it return a multidiensional array we flatten it for the cosine similarity(it deals only with 1d arrays)


#the function that prepares the database images for face recognition and comparsion
def load_folder_images(folder_path):
    feature_vectors = [] #to save all the vectors of the  database images

    for filename in os.listdir(folder_path): #loading the images from a single homeowner folder
        if filename.endswith('.jpg'): #finding every immage and read it
            image_path = os.path.join(folder_path, filename) #preparing the path to the image to read it
            image = cv2.imread(image_path)

            if image is not None: #if we find the image
                preprocessed_image = resize_image(image) #resize it only because we change it to gray and cut it to fit the face wehn we capture it
                feature_vector = compute_feature_vector(preprocessed_image) 
                feature_vectors.append(feature_vector)

    return feature_vectors


#the main face recognition part
def compare_live_image_to_folders(): 
    preprocessed_live_image,x,y,w,h = preprocess_image() #taking the image and the dimension of the face to put a box around it
    live_feature_vector = compute_feature_vector(preprocessed_live_image)

    conn=sqlite3.connect(DB_FILE) #open the database to get the users names and image folders we will compare with
    cursor=conn.cursor()
    cursor.execute("SELECT image_path FROM users") #taking all the column of image paths
    rows=cursor.fetchall()

    owners_num=len(rows) #calculating how many homeowners we have
    images_paths=[] #to put all the paths in an araray
    for row in rows:
        images_paths.append(row[0])

    found=False #the indicator that will tell us if there is a match

    for j in range (owners_num): 
     folder_path=images_paths[j] #perpare the images folder for a single hommeowner

     cursor.execute('SELECT user_name FROM users WHERE image_path = ?',(images_paths[j],))
     name=cursor.fetchone()[0] #prepare the name to display if found

     folder_feature_vectors= load_folder_images(folder_path) #load the folders to check

     for  folder_feature_vector in (folder_feature_vectors):
        similarity = cosine_similarity([live_feature_vector], [folder_feature_vector])[0][0] #it compares the 1d arrays and return the similarity between them

        if similarity > 0.9:  # Threshold for similarity 
            found=True
            break #breaks the inner loob (between images in a single homeowner folder)
     if found:
         break #breaks the outer loob (between all homeowners'folders)
    conn.close() #close the database

    #the check and display part
    if not found:
      person_photo=cv2.imread('person photo.jpg') #read the frame we saved earlier
      cv2.rectangle(person_photo, (x, y), (x + w, y + h), (0, 0, 255), 2) #use the dimensions to draw a rectangle and type unknown
      cv2.putText(person_photo, "unKnown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
    else:
      person_photo=cv2.imread('person photo.jpg') 
      cv2.rectangle(person_photo, (x, y), (x + w, y + h), (0, 255, 0), 2)#use the dimensions to draw a rectangle and type the name of the homeowner
      cv2.putText(person_photo, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

    cv2.imshow('the person on the door',person_photo) #show the full picture
    return found


    
#step 1:collecting the data
def collect_training_data(user_id, user_name):
    print("Starting data collection...")  

    if not cap.isOpened():
        print("Error: Camera could not be accessed")
        return

    count = 0

    # Create directories for saving the images if they do not exist
    if not os.path.exists(data_path): #folder for all the  homeowners
        os.makedirs(data_path)
        print(f"Created directory: {data_path}")

    user_folder = os.path.join(data_path, user_name)
    if not os.path.exists(user_folder): #folder of every single new homeowner
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

        if cv2.waitKey(100) & 0xFF == ord('q'): #delay so the person can change from his face position fro better accuracy 
            break #breaks if 'q' is pressed

    cv2.destroyAllWindows()
    messagebox.showinfo("DONE", f"Collected {count} images for user {user_name}.")
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


# Step 3: Function to add a new user to the database
def add_user_to_db(user_id, user_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (user_id, user_name) VALUES (?, ?)',
                       (user_id, user_name))
        conn.commit() #check if the user exists

         # collecting the data and getting the path to the images of the user
        image_source=collect_training_data(user_id, user_name) 
        cursor.execute('UPDATE users SET image_path = ? WHERE user_id = ?',
                       (image_source,user_id)) #updating with the image path so we dont start collecting data before we check for the inputs validation
        conn.commit()
        
        messagebox.showinfo("Success", f"User {user_name} added successfully!")

    except sqlite3.IntegrityError:
        messagebox.showerror("Error", f"User with ID {user_id} already exists.")
    
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
    notify.write(b'o') #tell the arduino to  open the door


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
    notify.write(b'u') #tell the arduino to wait for an input from the keypad to update password
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
  recognised=False #the flag we will use so in any moment we detect the homeowner  we dont care aboutt he rest of the  time
  count=0
  while count<30: #loob to detect the faces for 3 seconds
   found=compare_live_image_to_folders()
   if found :
       recognised=True
   count+=1
   if cv2.waitKey(100) & 0xFF == ord('q'): #delay so the owner has time to look properly to the camera
    break #breaks if 'q' is pressed
  if recognised:
      setup_gui_users()
  else:
      setup_gui_strange()  
  cv2.destroyAllWindows()
  cap.release()
main_fn()