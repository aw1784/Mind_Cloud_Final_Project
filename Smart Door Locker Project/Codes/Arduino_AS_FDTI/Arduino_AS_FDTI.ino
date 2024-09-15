//The data sender board
/*The TX (Data Send) of this chip is connected to the RX
(Data Receive) pin of the other chip*/
//Also connect the ground pins of both chips.

void setup(){
  	Serial.begin(9600);
}

void loop(){
  
 if (Serial.available()) 
  {
    char command = Serial.read();
 	
    if (command == 'o') 
    {
      Serial.write(command);
     
    }
    else if (command == 'u')
    {
      Serial.write(command);
    }
        
  }
}