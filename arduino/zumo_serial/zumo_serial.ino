#include <Arduino.h>
#include <QTRSensors.h>
#include <ZumoReflectanceSensorArray.h>
#include <ZumoMotors.h>
#include <ZumoBuzzer.h>
#include <Pushbutton.h>

// Settings
unsigned char sensorPins[] = { 4, A3, 11, A0, A2, 5 };
int maxValue = 1023; // Maximum value read in the reflectance sensor
int loopDelay = 100; // Sleep delay in ms for each serial/sensor loop
int baudRate = 9600; // Bits per second to transfer over the serial connection

// Environmental defines
#define LED_PIN 13
#define SERIAL_INPUT 80

// Objects used in multiple functions
ZumoBuzzer buzzer;
ZumoReflectanceSensorArray reflectanceSensors(sensorPins, sizeof(sensorPins), maxValue);
ZumoMotors motors;
Pushbutton button(ZUMO_BUTTON);

void setup() {
  pinMode(LED_PIN, OUTPUT);

  // Play a little welcome song
  buzzer.play(">f32>>d32");

  // Initialize serial communication
  Serial.begin(baudRate);

  // Initialize the reflectance sensors module
  reflectanceSensors.init();

  // Wait for connection to be started
  while (!Serial.available()) {
    delay(100);
  }

  char input[SERIAL_INPUT];
  Serial.readBytesUntil('\n', input, SERIAL_INPUT);

  // Sound off buzzer to denote Zumo is ready to start.
  buzzer.play("L16 cdegreg4");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);

  // If we have serial input, then parse it as two motor speeds.
  if (Serial.available()) {
    int motor1 = Serial.parseInt();
    int motor2 = Serial.parseInt();
    motors.setSpeeds(motor1, motor2);
	// Ignore the rest of the line, which might simply be a newline.
    char input[SERIAL_INPUT];
    Serial.readBytesUntil('\n', input, SERIAL_INPUT);
  }

  // Produce serial output for the raw reflectance sensor values
  unsigned int sensors[6];
  int i;
  reflectanceSensors.read(sensors);
  for (i = 0; i < 6; i++) {
    Serial.print(sensors[i], DEC);
    Serial.print(' ');
  }
  Serial.print('\n');
  digitalWrite(LED_PIN, LOW);
  delay(loopDelay);
}
