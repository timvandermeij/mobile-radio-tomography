// Based on the Zumo maze solver code, and written by Folkert Bleichrodt

#include <QTRSensors.h>
#include <ZumoReflectanceSensorArray.h>
#include <ZumoMotors.h>
#include <ZumoBuzzer.h>
#include <Pushbutton.h>

// SENSOR_THRESHOLD is a value to compare reflectance sensor
// readings to to decide if the sensor is over a black line
#define SENSOR_THRESHOLD 300

// ABOVE_LINE is a helper macro that takes a reflectance sensor measurement
// and returns 1 if the sensor is over the line and 0 if otherwise
#define ABOVE_LINE(sensor)((sensor) > SENSOR_THRESHOLD)

// Motor speed when turning. TURN_SPEED should always
// have a positive value, otherwise the Zumo will turn
// in the wrong direction.
#define TURN_SPEED 200

// Motor speed when driving straight. SPEED should always
// have a positive value, otherwise the Zumo will travel in the
// wrong direction.
#define SPEED 200

// Thickness of a grid line in inches
#define LINE_THICKNESS .75

// When the motor speed of the zumo is set by
// motors.setSpeeds(200,200), 200 is in ZUNITs/Second.
// A ZUNIT is a fictitious measurement of distance
// and only helps to approximate how far the Zumo has
// traveled. Experimentally it was observed that for
// every inch, there were approximately 17142 ZUNITs.
// This value will differ depending on setup/battery
// life and may be adjusted accordingly. This value
// was found using a 75:1 HP Motors with batteries
// partially discharged.
#define INCHES_TO_ZUNITS 17142.0

// When the Zumo reaches the end of a segment it needs
// to find out three things: if it has reached the finish line,
// if there is a straight segment ahead of it, and which
// segment to take. OVERSHOOT tells the Zumo how far it needs
// to overshoot the segment to find out any of these things.
#define OVERSHOOT(line_thickness)(((INCHES_TO_ZUNITS * (line_thickness)) / SPEED))

// Baud rate of the serial interface
#define BAUD_RATE 9600

// Pin number of the LED output pin, by Arduino pin numbering.
#define LED_PIN 13

// Sleep delay in ms for each serial check loop
#define LOOP_DELAY 10

// Maximum length of a serial input line that we ever receive
#define SERIAL_INPUT 80

// Length of a command code in the serial interface
#define COMMAND_LENGTH 4

ZumoBuzzer buzzer;
ZumoReflectanceSensorArray reflectanceSensors;
ZumoMotors motors;
Pushbutton button(ZUMO_BUTTON);

// current row and column
int cur_row, cur_col;
char zumo_direction;
int goto_row, goto_col;

void setup() {
  // current position
  cur_row = 0;
  cur_col = 0;
  goto_row = -1;
  goto_col = -1;
  // current direction
  zumo_direction = 'N';

  Serial.begin(BAUD_RATE);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  unsigned int sensors[6];
  unsigned short count = 0;
  unsigned short last_status = 0;
  int turn_direction = 1;
  int motor_speed;
  reflectanceSensors.init();

  // Play a little welcome song to denote that the vehicle is ready and is
  // waiting for a serial connection.
  buzzer.play(">f32>>d32");

  // Wait for connection to be started
  while (!Serial.available()) {
    delay(100);
  }

  char input[SERIAL_INPUT];
  Serial.readBytesUntil('\n', input, SERIAL_INPUT);

  // Calibrate the Zumo by sweeping it from left to right
  for (int i = 0; i < 4; i ++)
  {
    // Zumo will turn clockwise if turn_direction = 1.
    // If turn_direction = -1 Zumo will turn counter-clockwise.
    turn_direction *= -1;

    // Turn direction.
    motor_speed = turn_direction * TURN_SPEED;
    motors.setSpeeds(motor_speed, -1 * motor_speed);

    // This while loop monitors line position
    // until the turn is complete.
    while (count < 2)
    {
      reflectanceSensors.calibrate();
      reflectanceSensors.readLine(sensors);
      if (turn_direction < 0)
      {
        // If the right  most sensor changes from (over white space -> over
        // line or over line -> over white space) add 1 to count.
        count += ABOVE_LINE(sensors[5]) ^ last_status;
        last_status = ABOVE_LINE(sensors[5]);
      }
      else
      {
        // If the left most sensor changes from (over white space -> over
        // line or over line -> over white space) add 1 to count.
        count += ABOVE_LINE(sensors[0]) ^ last_status;
        last_status = ABOVE_LINE(sensors[0]);
      }
    }

    count = 0;
    last_status = 0;
  }

  // Turn left.
  turn('L');

  motors.setSpeeds(0, 0);

  // Sound off buzzer to denote Zumo is ready to start.
  buzzer.play("L16 cdegreg4");
}

void loop() {
  // If we have serial input, then parse the message.
  if (Serial.available() > COMMAND_LENGTH) {
    char command[COMMAND_LENGTH+1];
    Serial.readBytes(command, COMMAND_LENGTH);
    command[COMMAND_LENGTH] = '\0';
    if (strcmp(command, "GOTO") == 0)
    {
      // Read two coordinates.
      goto_row = Serial.parseInt();
      goto_col = Serial.parseInt();
    }
    else if (strcmp(command, "DIRS") == 0)
    {
      Serial.read();
      turn_to(Serial.read());
    }

    // Ignore the rest of the line, which might simply be a newline.
    char input[SERIAL_INPUT];
    Serial.readBytesUntil('\n', input, SERIAL_INPUT);

    if (goto_row >= 0 && goto_col >= 0)
    {
      Serial.print("ACKG ");
      Serial.print(goto_row);
      Serial.print(" ");
      Serial.print(goto_col);
      Serial.print("\n");

      zumo_goto(goto_row, goto_col);
      goto_row = -1;
      goto_col = -1;
    }
  }
  delay(LOOP_DELAY);
}

void zumo_goto(int row, int col) {
  int nRows = row - cur_row;
  int nCols = col - cur_col;

  Serial.print("DIFF ");
  Serial.print(nRows);
  Serial.print(" ");
  Serial.print(nCols);
  Serial.print("\n");

  char row_dir, col_dir;

  if (nRows > 0) {
    row_dir = 'N';
  }
  else if (nRows < 0) {
    row_dir = 'S';
  }
  else {
    row_dir = 'O';
  }
  if (nCols > 0) {
    col_dir = 'E';
  }
  else if (nCols < 0) {
    col_dir = 'W';
  }
  else {
    col_dir = 'O';
  }

  // First do row direction
  if (turnsToFace(row_dir) < turnsToFace(col_dir)) {
    goto_dir(row_dir, abs(nRows));
    goto_dir(col_dir, abs(nCols));
  }
  else {
    goto_dir(col_dir, abs(nCols));
    goto_dir(row_dir, abs(nRows));
  }

  cur_col = col;
  cur_row = row;

  Serial.print("LOCA ");
  Serial.print(row);
  Serial.print(" ");
  Serial.print(col);
  Serial.print(" ");
  Serial.print(zumo_direction);
  Serial.print("\n");
}


void goto_dir(char dir, int count) {
  // Are we already there?
  if (dir == 'O') {
    return;
  }
  turn_to(dir);
  for (int i = 0; i < count; i++) {
    followSegment();
    // Advance passed intersection
    motors.setSpeeds(SPEED, SPEED);
    delay(OVERSHOOT(LINE_THICKNESS*1.25));
    motors.setSpeeds(0,0);
    Serial.print("PASS ");
    Serial.print(i);
    Serial.print("\n");
  }
}

int turnsToFace(char dir) {
  if (dir == 'O') {
    return 99;
  }
  if (dir == zumo_direction) {
    return 0;
  }
  switch (dir) {
    case 'N':
      return (zumo_direction == 'S') ? 2 : 1;
      break;
    case 'W':
      return (zumo_direction == 'E') ? 2 : 1;
      break;
    case 'S':
      return (zumo_direction == 'N') ? 2 : 1;
      break;
    case 'E':
      return (zumo_direction == 'W') ? 2 : 1;
      break;
  }
}

void turn_to(char dir) {
  if (dir == zumo_direction) {
    return;
  }
  switch (zumo_direction) {
    case 'N':
      switch (dir) {
        case 'W':
          turn('L');
          break;
        case 'E':
          turn('R');
          break;
        case 'S':
          // Turn back
          turn('L');
          turn('L');
          break;
      }
      break;
    case 'W':
      switch (dir) {
        case 'N':
          turn('R');
          break;
        case 'S':
          turn('L');
          break;
        case 'E':
          // Turn back
          turn('L');
          turn('L');
          break;
      }
      break;
    case 'S':
      switch (dir) {
        case 'W':
          turn('R');
          break;
        case 'E':
          turn('L');
          break;
        case 'N':
          // Turn back
          turn('L');
          turn('L');
          break;
      }
      break;
    case 'E':
      switch (dir) {
        case 'N':
          turn('L');
          break;
        case 'S':
          turn('R');
          break;
        case 'W':
          // Turn back
          turn('L');
          turn('L');
          break;
      }
      break;
  }

  // Store new direction
  zumo_direction = dir;
  Serial.print("GDIR ");
  Serial.print(dir);
  Serial.print("\n");
}

// Turns according to the parameter dir, which should be
// 'L' (left), 'R' (right), 'S' (straight), or 'B' (back).
void turn(char dir)
{

  // count and last_status help
  // keep track of how much further
  // the Zumo needs to turn.
  unsigned short count = 0;
  unsigned short last_status = 0;
  unsigned int sensors[6];

  // dir tests for which direction to turn
  switch (dir)
  {
    // Since we are using the sensors to coordinate turns instead of timing
    // the turns, we can treat a left turn the same as a direction reversal:
    // they differ only in whether the zumo will turn 90 degrees or 180 degrees
    // before seeing the line under the sensor. If 'B' is passed to the turn
    // function when there is a left turn available, then the Zumo will turn
    // onto the left segment.
    case 'L':
    case 'B':
      // Turn left.
      motors.setSpeeds(-TURN_SPEED, TURN_SPEED);

      // This while loop monitors line position
      // until the turn is complete.
      while (count < 2)
      {
        reflectanceSensors.readLine(sensors);

        // Increment count whenever the state of the sensor changes
        // (white->black and black->white) since the sensor should
        // pass over 1 line while the robot is turning, the final
        // count should be 2
        count += ABOVE_LINE(sensors[1]) ^ last_status;
        last_status = ABOVE_LINE(sensors[1]);
      }

      break;

    case 'R':
      // Turn right.
      motors.setSpeeds(TURN_SPEED, -TURN_SPEED);

      // This while loop monitors line position
      // until the turn is complete.
      while (count < 2)
      {
        reflectanceSensors.readLine(sensors);
        count += ABOVE_LINE(sensors[4]) ^ last_status;
        last_status = ABOVE_LINE(sensors[4]);
      }

      break;

    case 'S':
      // Don't do anything!
      break;
  }
}


void followSegment()
{
  unsigned int position;
  unsigned int sensors[6];
  int offset_from_center;
  int power_difference;
  bool following = true;

  while (following)
  {
    // Get the position of the line.
    position = reflectanceSensors.readLine(sensors);

    // The offset_from_center should be 0 when we are on the line.
    offset_from_center = ((int)position) - 2500;

    // Compute the difference between the two motor power settings,
    // m1 - m2.  If this is a positive number the robot will turn
    // to the left.  If it is a negative number, the robot will
    // turn to the right, and the magnitude of the number determines
    // the sharpness of the turn.
    power_difference = offset_from_center / 3;

    // Compute the actual motor settings.  We never set either motor
    // to a negative value.
    if (power_difference > SPEED)
    {
      power_difference = SPEED;
    }
    else if (power_difference < -SPEED)
    {
      power_difference = -SPEED;
    }

    if (power_difference < 0)
    {
      motors.setSpeeds(SPEED + power_difference, SPEED);
    }
    else
    {
      motors.setSpeeds(SPEED, SPEED - power_difference);
    }

    // We use the inner four sensors (1, 2, 3, and 4) for
    // determining whether there is a line straight ahead, and the
    // sensors 0 and 5 for detecting lines going to the left and
    // right.

    if (!ABOVE_LINE(sensors[0]) && !ABOVE_LINE(sensors[1]) &&
        !ABOVE_LINE(sensors[2]) && !ABOVE_LINE(sensors[3]) &&
        !ABOVE_LINE(sensors[4]) && !ABOVE_LINE(sensors[5]))
    {
      // There is no line visible ahead, and we didn't see any
      // intersection.  Must be a dead end.
      following = false;
    }
    else if (ABOVE_LINE(sensors[0]) || ABOVE_LINE(sensors[5]))
    {
      // Found an intersection.
      following = false;
    }
  }
}
