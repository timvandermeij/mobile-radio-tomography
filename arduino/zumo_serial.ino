#include <Arduino.h>
#include <QTRSensors.h>
#include <ZumoReflectanceSensorArray.h>
#include <ZumoMotors.h>
#include <ZumoBuzzer.h>
#include <Pushbutton.h>

// Settings
unsigned char sensorPins[] = { 4, A3, 11, A0, A2, 5 };
int maxValue = 1023;
int loopDelay = 100; // ms

#define LED_PIN 13
#define SERIAL_INPUT 80

ZumoBuzzer buzzer;
ZumoReflectanceSensorArray reflectanceSensors(sensorPins, sizeof(sensorPins), maxValue);
ZumoMotors motors;
Pushbutton button(ZUMO_BUTTON);

void setup() {
  // Play a little welcome song
  buzzer.play(">f32>>d32");

  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);

  // Initialize the reflectance sensors module
  reflectanceSensors.init();

  // Wait for the user button to be pressed and released
  button.waitForButton();

  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(13, HIGH);
  if (Serial.available()) {
    char input[SERIAL_INPUT];
    Serial.readBytesUntil('\n', input, SERIAL_INPUT);
    int i;
    for (i = 0; i < SERIAL_INPUT; i++) {
      // Text ends at NULL or ETX
      if (input[i] == '\0' || input[i] == '\3') {
        break;
      }
      Serial.print(input[i], HEX);
      Serial.print(' ');
    }
    Serial.println(" PONG");
  }
  unsigned int sensors[6];
  int i;
  reflectanceSensors.read(sensors);
  for (i = 0; i < 6; i++) {
    Serial.print(sensors[i], DEC);
    Serial.print(' ');
  }
  Serial.print('\n');
  digitalWrite(13, LOW);
  delay(1000);
}
