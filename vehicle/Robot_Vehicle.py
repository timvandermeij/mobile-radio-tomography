import RPIO
import RPi.GPIO
from dronekit import LocationLocal, LocationGlobal, Attitude
from Vehicle import Vehicle
from ..location.Line_Follower import Line_Follower_Direction, Line_Follower_State
from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

class Robot_State(object):
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

class Robot_State_Rotate(Robot_State):
    def __init__(self, rotate_direction, target_direction, current_direction):
        super(Robot_State_Rotate, self).__init__("rotate")
        # Direction in which we are rotating (-1 is left, 1 is right)
        self.rotate_direction = rotate_direction
        # Target direction (Line_Follower_Direction enum)
        self.target_direction = target_direction
        # The current direction (Line_Follower_Direction enum)
        self.current_direction = current_direction

class Robot_Vehicle(Vehicle):
    _line_follower_class = Line_Follower_Raspberry_Pi

    def __init__(self, arguments, geometry):
        super(Robot_Vehicle, self).__init__(arguments, geometry)

        self.settings = arguments.get_settings("vehicle_robot")

        # Motor direction pins (LOW = forward, HIGH = backward)
        self._direction_pins = self.settings.get("direction_pins")
        # Motor speed pins (PWM values)
        self._speed_pins = self.settings.get("speed_pins")

        # PWM range for both motors (minimum and maximum values)
        self._speed_pwms = self.settings.get("speed_pwms")
        # Speed range for both motors in m/s
        self._speeds = self.settings.get("speeds")

        # Speed difference in m/s to adjust when we diverge from a line.
        self._diverged_speed = self.settings.get("diverged_speed")

        # Servo objects corresponding to the speed PWM pins of both motors.
        # First item is left motor, second item is right motor.
        self._speed_servos = []

        # The home location coordinates of the robot. The robot should be 
        # placed at the intersection corresponding to these coordinates to 
        # begin with.
        self._home_location = self.settings.get("home_location")
        self._location = self._home_location
        # The starting direction of the robot. The robot should be aligned with 
        # this direction to begin with.
        self._direction = self.settings.get("home_direction")

        self._line_follower = self._line_follower_class(self._home_location, self._direction, self.line_follower_callback, arguments)
        # The delay of the sensor reading loop in the line follower thread.
        self._line_follower_delay = self.settings.get("line_follower_delay")

        # The delay of the robot vehicle state loop.
        self._loop_delay = self.settings.get("vehicle_delay")

        self._waypoints = []
        self._current_waypoint = 0

        # Whether the robot is currently armed and driving around.
        self._running = False
        # Current state of the robot. Possible states are:
        # - intersection: The robot is standing still at an intersection.
        # - rotate: The robot is rotating at an intersection. See
        #   Robot_State_Rotate
        self._state = Robot_State("intersection")

    def setup(self):
        # Initialize the RPi.GPIO module. Doing it this way instead of using
        # an alias during import allows unit tests to access it too.
        self.gpio = RPi.GPIO

        # Disable warnings about pins being in use.
        self.gpio.setwarnings(False)

        # Use board numbering which corresponds to the pin numbers on the
        # P1 header of the board.
        self.gpio.setmode(self.gpio.BOARD)

        for pin in self._direction_pins:
            self.gpio.setup(pin, self.gpio.OUT)

        self._speed_servos = [Servo(pin, self._speeds, self._speed_pwms) for pin in self._speed_pins]

    def _state_loop(self):
        while self._running:
            # TODO: Handle moving away from an intersection after we are done 
            # there.
            if isinstance(self._state, Robot_State_Rotate):
                if self._state.current_direction == self._state.target_direction:
                    # When we are done rotating, stand still again before 
                    # determining our next moves.
                    self._state = Robot_State("intersection")
                    self.set_speeds(0, 0)

                    self._direction = self._state.current_direction
                    self._line_follower.set_direction(self._direction)
            elif self._state.name == "intersection":
                if self._location == self.get_waypoint():
                    # TODO: Figure out what to do after seeing an intersection 
                    # (measurements, moving to next intersection, or turning).
                    self._state = Robot_State("line")

            time.sleep(self._loop_delay)

    def _line_follower_loop(self):
        while self._running:
            self._line_follower.activate()
            sensor_values = self._line_follower.read()
            self._line_follower.update(sensor_values)
            self._line_follower.deactive()
            time.sleep(self._line_follower_delay)

    def line_follower_callback(self, event, data):
        if event == "intersection":
            self._location = (data[0], data[1])
            self._state = State(event)
        elif event == "diverged":
            direction = -1 if data == "left" else 1
            if isinstance(self._state, Robot_State_Rotate):
                if direction == self._state.rotate_direction:
                    # We are rotating on an intersection to move to our next 
                    # direction, thus track whether we found a new line. Only 
                    # do so when we see the line from the side that we are 
                    # moving to, not when we rotate away from it again.
                    direction = (self._state.current_direction + direction) % 4
                    self._state.current_direction = direction
            else:
                # We went off the line, so steer the motors such that the robot 
                # gets back to the line.
                speed = self.speed
                speed_difference = direction * self._diverged_speed
                self.set_speeds(speed - speed_difference, speed + speed_difference)

    def set_speeds(left_speed, right_speed):
        for i, speed in [(0, left_speed), (1, right_speed)]:
            pwm = self._speed_servos[i].get_pwm(speed)
            self.set_servo(self._speed_servos[i], pwm)

    @property
    def use_simulation(self):
        # We do not support simulation (physical environments only)
        return False

    @property
    def home_location(self):
        return LocationGlobal(0.0, 0.0, 0.0)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        if value.name == "RTL":
            self._waypoints = [self._home_location]
        elif value.name == "HALT":
            self._running = False

    @property
    def armed(self):
        return self._running

    @armed.setter
    def armed(self, value):
        if value:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        self._running = True
        thread.start_new_thread(self._line_follower_loop, ())
        thread.start_new_thread(self._state_loop, ())

    def deactivate(self):
        self._running = False

    def add_waypoint(self, location):
        if isinstance(location, LocationLocal):
            self._waypoints.append((location.north, location.east))
        else:
            print("Warning: Using non-local locations")
            self._waypoints.append((location.lat, location.lon))

    def clear_waypoints(self):
        self._waypoints = []

    def get_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self._current_waypoint

        if waypoint >= len(self._waypoints):
            return None

        wp = self._waypoints[waypoint]
        return LocationLocal(wp[0], wp[1], 0.0)

    def get_next_waypoint(self):
        return self._current_waypoint

    def set_next_waypoint(self, waypoint=-1):
        if waypoint == -1:
            waypoint = self._current_waypoint + 1

        self._current_waypoint = waypoint

    def count_waypoints(self):
        return len(self._waypoints)

    def simple_goto(self, location):
        self._waypoints = []
        self.add_waypoint(location)

    @property
    def location(self):
        return LocationLocal(self._location[0], self._location[1], 0.0)

    @property
    def speed(self):
        # Take the maximum speed for now; in any event that they are different, 
        # we would not have any accurate speed ratings for now.
        return max(servo.get_value() for servo in self._speed_servos)

    @speed.setter
    def speed(self, value):
        if self._running:
            for servo in self._speed_servos:
                pwm = servo.get_pwm(value)
                self.set_servo(servo, pwm)

    # TODO: Implement velocity. This would need to be based on the current 
    # direction/attitude and the speeds of both motors...

    def _get_yaw(self):
        # TODO: Perhaps we want a more precise attitude... gyroscope?
        if isinstance(self._state, Robot_State_Rotate):
            direction = self._state.current_direction
        else:
            direction = self._direction

        if direction == Line_Follower_Direction.UP:
            yaw = 0.0
        elif direction == Line_Follower_Direction.RIGHT:
            yaw = 0.5 * math.pi
        elif direction == Line_Follower_Direction.DOWN:
            yaw = math.pi
        elif direction == Line_Follower_Direction.LEFT:
            yaw = 1.5 * math.pi
        else:
            raise ValueError("Invalid direction '{}'".format(direction))

        return yaw

    @property
    def attitude(self):
        yaw = self._get_yaw()

        return Attitude(0.0, 0.0, yaw)

    def set_yaw(self, heading, relative=False, direction=1):
        if self._state.name != "intersection":
            # We can only rotate on an intersection where we can see all 
            # cardinal lines.
            return

        if relative:
            heading = self._get_yaw() + heading

        target_direction = int(round(2*heading/math.pi)) % 4
        self._set_direction(target_direction, direction)

    def _set_direction(self, target_direction, rotate_direction=0):
        if rotate_direction == 0:
            rotate_direction = int(math.copysign(1, target_direction-self._direction))

        self._state = Robot_State_Rotate(rotate_direction, target_direction, self._direction)
        self._line_follower.set_state(Line_Follower_State.AT_INTERSECTION)

    def set_servo(self, servo, pwm):
        RPIO.PWM.set_servo(servo.pin, pwm)
        servo.set_current_pwm(pwm)
