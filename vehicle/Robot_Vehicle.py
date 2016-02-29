import RPIO
import RPi.GPIO
from dronekit import LocationLocal, LocationGlobal, Attitude
from Vehicle import Vehicle
from ..location.Line_Follower import Line_Follower_Direction
from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

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

        self._speed_servos = []

        self._home_location = self.settings.get("home_location")
        self._location = self._home_location
        self._direction = self.settings.get("home_direction")

        self._line_follower = self._line_follower_class(self._home_location, self._direction, self.line_follower_callback, arguments)
        self._line_follower_delay = self.settings.get("line_follower_delay")

        self._waypoints = []
        self._current_waypoint = 0

        self._running = False

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

    def _line_follower_loop(self):
        while self._running:
            self._line_follower.activate()
            sensor_values = self._line_follower.read()
            self._line_follower.update(sensor_values)
            self._line_follower.deactive()
            time.sleep(self._line_follower_delay)

    def line_follower_callback(self, event, data):
        pass

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
        self._running = value
        if self._running:
            thread.start_new_thread(self._line_follower_loop, ())

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

    @property
    def attitude(self):
        # TODO: Perhaps we want a more precise attitude... gyroscope?
        if self._direction == Line_Follower_Direction.UP:
            yaw = 0.0
        elif self._direction == Line_Follower_Direction.DOWN:
            yaw = math.pi
        elif self._direction == Line_Follower_Direction.LEFT:
            yaw = 1.5 * math.pi
        elif self._direction == Line_Follower_Direction.RIGHT:
            yaw = 0.5 * math.pi

        return Attitude(0.0, 0.0, yaw)

    def set_servo(self, servo, pwm):
        RPIO.PWM.set_servo(servo.pin, pwm)
        servo.set_current_pwm(pwm)
