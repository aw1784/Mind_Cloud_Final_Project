// Libraries
#include <Servo.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>

#define TEMPERATURE A1 
#define LDR A2
#define lighting_system 6
#define MOTOR 5

void correctKEY(int temperature);
void incorrectKEY();
void checkKEY(int temperature);
int readKeypad(int temperature);
void SET_LED_MODE(int LED);
int speed_decider(int temp);
void lighting_system_brightness(int status);
void resetSystemIfNoMovement();
void reset();
int update_password();

Servo myservo; // initialize servo motor
int pirPin = A4;
int buzz = A5;
int OFF_LED_blue = A0;
int MED_LED_green = 4;
int MAX_LED_red = 2;
unsigned long motorStartTime = 0;  // To track when the motor starts
unsigned long lastMovementTime = 0;  // To track last movement from the PIR sensor
bool motorActive = false;
const byte ROWS = 4;   // four rows
const byte COLS = 4;   // four columns
int count=0;
char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[ROWS] = {13, 12,11, 10};   // array for keypad rows
byte colPins[COLS] = {9, 8, 7,A3}; // array for keypad columns 

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

char KEY[4] = {'1','2','3','4'};  // Put the wanted password keys here
char attempt[4] = {0, 0, 0, 0};    // create an array for the four attempts 
int z = 0;



void setup() 
{
  Serial.begin(9600);
  pinMode(MOTOR, OUTPUT);
  pinMode(LDR, INPUT);
  pinMode(lighting_system, OUTPUT);
  pinMode(buzz, OUTPUT);
  pinMode(OFF_LED_blue, OUTPUT);
  pinMode(MED_LED_green, OUTPUT);
  pinMode(MAX_LED_red, OUTPUT);
  pinMode(pirPin,INPUT);
  digitalWrite(pirPin, LOW);
  myservo.attach(3);
  myservo.write(0); // Start with the servo in the closed position
}

void loop() 
{
     // calculating temperature
    int temperature = analogRead(TEMPERATURE);
    temperature = map(temperature, 20, 358, -40, 125);
    Serial.print("Password: ");
  
  
    while (readKeypad(temperature) <= 3)// Wait until 4 keys have been entered
    { 
        if (Serial.available()) 
        {
          char command = Serial.read();

          if (command == 'o') // For Openning the Door regarding the Password
          {
               // openDoor;
              correctKEY(temperature);
              if (count==1)
              {
                  temperature = analogRead(TEMPERATURE);
                  temperature = map(temperature, 20, 358, -40, 125);
                  analogWrite(MOTOR, speed_decider(temperature)); // Adjust motor speed based on temperature
                  lighting_system_brightness(analogRead(LDR));
                  digitalWrite(buzz, LOW);

              }
          }
          else if (command == 'u')// For Updatting Password 
          {
              Serial.println ("Enter new password: ");
              while (update_password() <= 3){}
              Serial.print("Password: ");
          }
        
        }
        if (count==1)
        {
          temperature = analogRead(TEMPERATURE);
          temperature = map(temperature, 20, 358, -40, 125);
          analogWrite(MOTOR, speed_decider(temperature)); // Adjust motor speed based on temperature
          lighting_system_brightness(analogRead(LDR));
          digitalWrite(buzz, LOW);
    
        }
        temperature = analogRead(TEMPERATURE);
  	    temperature = map(temperature, 20, 358, -40, 125);

        if (myservo.read()==0)
        {
          if (digitalRead(pirPin)==HIGH)
          {
            Serial.println("Warning Someone inside");
            delay(100);
            digitalWrite(pirPin,LOW);
            Serial.print("Password: ");
          }
        }
       resetSystemIfNoMovement();  // Check if 30 minutes have passed without movement
    } 
}

// Functions:-
int readKeypad(int temperature) 
{
  char key = keypad.getKey();
  if (key != NO_KEY) 
  {
    switch (key) 
    {
      case '*':       // the password should be entered after this symbol
        z = 0;        // reset the attempt index
        break;
      case '#':       // the password should be finished by this symbol
        delay(100);   // debounce
        checkKEY(temperature);  // call this function 
        break;
      default:
      
        attempt[z] = key;
        Serial.print("*");
        if (z==3)
        {
          checkKEY(temperature);
          z=0;
          Serial.println();
          return 4;
        }
      
        else
        {
          z++;
        }
        break;
    }
  }
  return z;
}

void checkKEY(int temperature) 
{
  int correct = 0;
  for (int i = 0; i < 4; i++) // loop to let users enter four keys
  {   
    if (attempt[i] == KEY[i]) // compare the entered key with the password  
    { 
      correct++; // increase it, whenever there is a correct key
    }
  }
  if (correct == 4)  // if the correct keys become four keys do .. 
  {
    correctKEY(temperature);
    for (int zz = 0; zz < 4; zz++) 
    {
      attempt[zz] = 0;
    }
    z = 0; // Reset the attempt counter
  } 
  else 
  {
    incorrectKEY();
    for (int zz = 0; zz < 4; zz++) 
    {
      attempt[zz] = 0;
    }
    z = 0; // Reset the attempt counter
  }

}

void correctKEY(int temperature) {
  myservo.write(180); // Move servo to open position
  analogWrite(MOTOR, speed_decider(temperature)); // Adjust motor speed based on temperature
  lighting_system_brightness(analogRead(LDR));
  digitalWrite(buzz, LOW);
  Serial.println("");
  Serial.println("PASSED");
  delay(10000);
  myservo.write(0); // Return servo to the closed position after delay
  count=1;
  motorStartTime = millis();  // Start the motor timer
  motorActive = true;
}

void incorrectKEY() 
{
  digitalWrite(buzz, HIGH);
  delay(500);
  digitalWrite(buzz, LOW);
  Serial.println("");
  Serial.println("INCORRECT");
  
}


int update_password()
{
  char key = keypad.getKey();
  if (key != NO_KEY) 
  {
    switch (key) 
    {
      case '*':       // the password should be entered after this symbol
        z = 0;        // reset the attempt index
        break;
      case '#':       // the password should be finished by this symbol
        delay(100);   // debounce
        if (z!=3)
        {
          z=0;
          Serial.println("Password not complete(Must be 4 char not contain (*or #) )");
        }
        break;

      default:
      
        KEY[z] = key;
        Serial.print("*");
        if (z==3)
        {
          z=0;
          Serial.println();
          return 4;
        }
      
        else
        {
          z++;
        }
        break;
    }
  }
  return z;
}

void SET_LED_MODE(int LED) {
  // Reset all LEDs
  digitalWrite(OFF_LED_blue, LOW);
  digitalWrite(MED_LED_green, LOW);
  digitalWrite(MAX_LED_red, LOW);
  if (LED==0)  // for blue LED as it connected to A0 
  {
    digitalWrite(OFF_LED_blue,HIGH);
  }
  // Turn on the LED for the current mode
  else
  {
    digitalWrite(LED, HIGH);
  }
}

int speed_decider(int temp) {
  if (temp < 20) 
  {
    int blue=0;
    digitalWrite(buzz, LOW);
    SET_LED_MODE(blue);
    return 0;
  } 
  else if (temp < 30) 
  {
    digitalWrite(buzz, LOW);
    SET_LED_MODE(MED_LED_green);
    return 127;
  } 
  else 
  {
    SET_LED_MODE(MAX_LED_red);
    return 255;
  }
}
void lighting_system_brightness(int status)
{
  int data =255 - map(status,1022,0,255,0);
  analogWrite(lighting_system, data); 
  delay(1);
  
}
void resetSystemIfNoMovement() 
{
  if (motorActive && (millis() - motorStartTime >= 1800000)) // 30 minutes = 1800000 ms
  { 
    if (digitalRead(pirPin) == LOW) 
    {
      Serial.println("No movement detected in 30 minutes, resetting system.");
      reset();
    } 
    else 
    {
      lastMovementTime = millis();  // Reset movement timer if PIR detects movement
    }
  }
}
void reset()
{
  digitalWrite(OFF_LED_blue, LOW);
  digitalWrite(MED_LED_green, LOW);
  digitalWrite(MAX_LED_red, LOW);
  analogWrite(MOTOR, 0);
  digitalWrite(lighting_system,LOW);
  motorActive = false;
  count = 0;
}