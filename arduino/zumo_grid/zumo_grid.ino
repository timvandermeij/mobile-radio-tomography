// Based on the Zumo maze solver code, and written by Folkert Bleichrodt

#include <QTRSensors.h>
#include <ZumoReflectanceSensorArray.h>
#include <ZumoMotors.h>
#include <ZumoBuzzer.h>
#include <Pushbutton.h>
#include <SoftwareSerial.h>

// SENSOR_THRESHOLD is a value to compare reflectance sensor
// readings to to decide if the sensor is over a black line
#define SENSOR_THRESHOLD 350

// ABOVE_LINE is a helper macro that takes a reflectance sensor measurement
// and returns 1 if the sensor is over the line and 0 if otherwise
#define ABOVE_LINE(sensor)((sensor) > SENSOR_THRESHOLD)

// Motor speed when turning. TURN_SPEED should always
// have a positive value, otherwise the Zumo will turn
// in the wrong direction.
#define TURN_SPEED 250

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

// Factor to determine how many units of line thickness we should advance.
#define OVERSHOOT_FACTOR_WHITESPACE 1.25
#define OVERSHOOT_FACTOR_INTERSECTION 2.0

// Baud rate of the serial interface
#define BAUD_RATE 9600

// Pin number of the LED output pin, by Arduino pin numbering.
#define LED_PIN 13

// Sleep delay in ms for each serial check loop
#define LOOP_DELAY 10

// Sleep delay in ms when the vehicle is halted
#define HALT_DELAY 500

// Maximum length of a serial input line that we ever receive
#define SERIAL_INPUT 80

// Length of a command code in the serial interface
#define COMMAND_LENGTH 4

// RX pin of the serial interface
#define RX_PIN A5

// TX pin of the serial interface
#define TX_PIN A1

// Serial loop waiting delay when no data is available
#define SERIAL_DELAY 10

ZumoBuzzer buzzer;
ZumoReflectanceSensorArray reflectanceSensors;
ZumoMotors motors;
Pushbutton button(ZUMO_BUTTON);
SoftwareSerial softSerial(RX_PIN, TX_PIN);

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

  motors.setSpeeds(0, 0);

  softSerial.begin(BAUD_RATE);

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

  // Wait for serial interface.
  ignore_input();

  digitalWrite(LED_PIN, LOW);

  // Calibrate the Zumo by sweeping it from left to right
  for (int i = 0; i < 4; i ++)
  {
    // Allow skipping calibration, if the user can press
    // the button that is. This usually means that the
    // motors are disabled for testing purposes, and
    // we would be unable to get through calibration.
    if (button.isPressed())
    {
      break;
    }

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
      if (button.isPressed())
      {
        break;
      }

      reflectanceSensors.calibrate();
      reflectanceSensors.read(sensors);
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

  if (!button.isPressed())
  {
    // Turn left.
    turn('L');
  }

  motors.setSpeeds(0, 0);

  digitalWrite(LED_PIN, HIGH);

  // Sound off buzzer to denote Zumo is ready to start.
  buzzer.play("L16 cdegreg4");
}

bool has_immediate_command() {
  if (softSerial.available() > 0) {
    char command = softSerial.peek();
    return (command == '\a' || command == '\x03');
  }
  return false;
}

void check_immediate_command() {
  if (has_immediate_command()) {
    char command = softSerial.read();
    if (command == '\a') {
      buzzer.play(">d32>>b32");
    }
    else if (command == '\x03') {
      // Halt the vehicle and ignore all commands
      // until we receive a "CONT" command.
      buzzer.play(">b32>>b32>>b32>>b32");
      motors.setSpeeds(0, 0);

      bool halted = true;
      while (halted) {
        while (softSerial.available() == 0) {
          digitalWrite(LED_PIN, HIGH);
          delay(HALT_DELAY);
          digitalWrite(LED_PIN, LOW);
          delay(HALT_DELAY);
        }
        digitalWrite(LED_PIN, HIGH);

        if (has_immediate_command()) {
          if (softSerial.read() == '\a') {
            buzzer.play(">d32>>b32");
          }
        }

        char command[COMMAND_LENGTH+1];
        read_string(command, COMMAND_LENGTH);
        if (strcmp(command, "CONT") == 0) {
          halted = false;
        }
        ignore_input();
      }
    }
  }
}

void check_command(char command[COMMAND_LENGTH+1]) {
  read_string(command, COMMAND_LENGTH);
  if (strcmp(command, "GOTO") == 0) {
    // Go to specific grid coordinates.
    // Read two coordinates.
    goto_row = read_int();
    goto_col = read_int();
  }
  else if (strcmp(command, "DIRS") == 0) {
    // Change direction
    safe_read();
    turn_to(safe_read());
  }
  else if (strcmp(command, "HOME") == 0) {
    // Override current location and direction.
    // Use for setting home location at start.
    cur_row = read_int();
    cur_col = read_int();
    safe_read();
    zumo_direction = safe_read();

    softSerial.print("ACKH ");
    softSerial.print(cur_row);
    softSerial.print(" ");
    softSerial.print(cur_col);
    softSerial.print(" ");
    softSerial.print(zumo_direction);
    softSerial.print("\n");
  }
  else if (strcmp(command, "SPDS") == 0) {
    int motor1 = read_int();
    int motor2 = read_int();
    motors.setSpeeds(motor1, motor2);
  }
}

void loop() {
  // If we have serial input, then parse the message.
  check_immediate_command();
  if (softSerial.available() > COMMAND_LENGTH) {
    char command[COMMAND_LENGTH+1];
    check_command(command);

    // Ignore the rest of the line, which might simply be a newline.
    ignore_input();

    if (goto_row >= 0 && goto_col >= 0) {
      softSerial.print("ACKG ");
      softSerial.print(goto_row);
      softSerial.print(" ");
      softSerial.print(goto_col);
      softSerial.print("\n");

      zumo_goto(goto_row, goto_col);
      goto_row = -1;
      goto_col = -1;
    }
  }
  delay(LOOP_DELAY);
}

char safe_read() {
  while (!softSerial.available()) {
    delay(SERIAL_DELAY);
  }
  return softSerial.read();
}

char safe_peek() {
  while (!softSerial.available()) {
    delay(SERIAL_DELAY);
  }
  return softSerial.peek();
}

void ignore_input() {
  // Ignore input until end of line
  char c = safe_read();
  while (c != '\n') {
    c = safe_read();
  }
}

void read_string(char buffer[], int length) {
  // Read a string of at most length from the serial
  // interface, and put the string into the buffer.
  // We read until this length, or when we read
  // a newline. The newline is not added to the buffer.
  // The buffer must be at least size length+1, and
  // is filled with the read characters and a '\0' pad.
  int i = 0;
  char c = '\0';
  while (i < length && c != '\n') {
    c = safe_read();
    buffer[i] = c;
    i++;
  }
  buffer[i] = '\0';
}

int read_int() {
  // Read an integer from the serial interface, and
  // return its value. Leading non-digits are skipped,
  // and this function returns -1 if no digits are
  // read before a newline is reached. Otherwise, the
  // digits are parsed into an integer. The parsing
  // stops when a non-digit is found. This non-digit
  // is left in the serial stream.
  int res = 0;
  int sign = 1;
  char c = safe_peek();
  // Ignore leading non-integers
  while ((c < '0' || c > '9') && c != '\n') {
    if (c == '-') {
      sign = -1 * sign;
    }
    softSerial.read();
    c = safe_peek();
  }
  if (c == '\n') {
    return -1;
  }
  // Parse integers until first non-digit
  while (c >= '0' && c <= '9') {
    softSerial.read();
    res = res * 10 + (c - '0');
    c = safe_peek();
  }
  return sign * res;
}

void zumo_goto(int row, int col) {
  int nRows = row - cur_row;
  int nCols = col - cur_col;

  softSerial.print("DIFF ");
  softSerial.print(nRows);
  softSerial.print(" ");
  softSerial.print(nCols);
  softSerial.print("\n");

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

  softSerial.print("LOCA ");
  softSerial.print(row);
  softSerial.print(" ");
  softSerial.print(col);
  softSerial.print(" ");
  softSerial.print(zumo_direction);
  softSerial.print("\n");
}

void advance(float factor) {
    // Advance passed intersection
    motors.setSpeeds(SPEED, SPEED);
    delay(OVERSHOOT(LINE_THICKNESS * factor));
    motors.setSpeeds(0,0);
}

void goto_dir(char dir, int count) {
  // Are we already there?
  if (dir == 'O') {
    return;
  }
  turn_to(dir);
  for (int i = 0; i < count; i++) {
    followSegment();
    advance(OVERSHOOT_FACTOR_INTERSECTION);
    softSerial.print("PASS ");
    softSerial.print(i);
    softSerial.print("\n");
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
  softSerial.print("GDIR ");
  softSerial.print(dir);
  softSerial.print("\n");
}

// Turns according to the parameter dir, which should be
// 'L' (left), 'R' (right), 'S' (straight), or 'B' (back).
void turn(char dir) {
  // count and last_status help
  // keep track of how much further
  // the Zumo needs to turn.
  unsigned short count = 0;
  unsigned short last_status = 0;
  unsigned int sensors[6];

  // dir tests for which direction to turn
  switch (dir) {
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
      while (count < 2) {
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
      while (count < 2) {
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


void followSegment() {
  unsigned int position;
  unsigned int sensors[6];
  int offset_from_center;
  int power_difference;
  bool following = true;
  bool advanced = false;

  while (following) {
    check_immediate_command();

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
    if (power_difference > SPEED) {
      power_difference = SPEED;
    }
    else if (power_difference < -SPEED) {
      power_difference = -SPEED;
    }

    if (power_difference < 0) {
      motors.setSpeeds(SPEED + power_difference, SPEED);
    }
    else {
      motors.setSpeeds(SPEED, SPEED - power_difference);
    }

    // We use the inner four sensors (1, 2, 3, and 4) for
    // determining whether there is a line straight ahead, and the
    // sensors 0 and 5 for detecting lines going to the left and
    // right.

    if (!ABOVE_LINE(sensors[0]) && !ABOVE_LINE(sensors[1]) &&
        !ABOVE_LINE(sensors[2]) && !ABOVE_LINE(sensors[3]) &&
        !ABOVE_LINE(sensors[4]) && !ABOVE_LINE(sensors[5])) {
      // There is no line visible ahead, and we didn't see any
      // intersection. Try to advance in case it is a glitchy
      // surface, but if we tried that already then stop.
      if (!advanced) {
        advance(OVERSHOOT_FACTOR_WHITESPACE);
        advanced = true;
      }
      else {
        following = false;
      }
    }
    else if (ABOVE_LINE(sensors[0]) || ABOVE_LINE(sensors[5])) {
      // Found an intersection.
      following = false;
    }
  }
}
