import RPi.GPIO
from ..settings import Arguments, Settings

class Line_Follower_Direction(object):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class Line_Follower_State(object):
    AT_LINE = 1
    AT_INTERSECTION = 2

class Line_Follower_Bit_Mask(object):
    LINE = 0b0110
    LINE_LEFT = 0b1000
    LINE_RIGHT = 0b0001
    INTERSECTION = 0b1001

class Line_Follower(object):
    def __init__(self, location, direction, callback, settings):
        """
        Initialize the line follower object. We assume that we are working
        with the Zumo Robot for Arduino v1.2 (assembled with 75:1 HP motors),
        which has a line follower with six LEDs.

        Note that the pin numbers in the settings file are the pin numbers for
        the connection on the Raspberry Pi. These should be connected, in order,
        to the pins 4, 17 (A3), 11, 14 (A0), 16 (A2) and 5 on the Zumo rover.
        """

        if isinstance(settings, Arguments):
            settings = settings.get_settings("line_follower")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        if not isinstance(location, tuple):
            raise ValueError("Location must be a tuple")

        if type(direction) != int or not 1 <= direction <= 4:
            raise ValueError("Direction must be one of the defined types")

        self._location = location
        self._direction = direction
        self._callback = callback
        self._state = Line_Follower_State.AT_LINE

        self._sensors = settings.get("led_pins")
        if len(self._sensors) != 6:
            raise ValueError("Exactly six sensors must be defined for the Zumo robot")

        # Initialize the RPi.GPIO module. Doing it this way instead of using
        # an alias during import allows unit tests to access it too.
        self.gpio = RPi.GPIO

        # Disable warnings about pins being in use.
        self.gpio.setwarnings(False)

        # Use board numbering which corresponds to the pin numbers on the
        # P1 header of the board.
        self.gpio.setmode(self.gpio.BOARD)

        # Configure the input pins.
        for sensor in self._sensors:
            self.gpio.setup(sensor, self.gpio.IN)

    def activate(self):
        raise NotImplementedError("Subclasses must implement activate()")

    def deactivate(self):
        raise NotImplementedError("Subclasses must implement deactivate()")

    def read(self):
        """
        Read the values of four of the six LEDs. We only read the two innermost
        and the two outermost LEDs to clearly make a distinction between a
        straight line and an intersection of lines.
        """

        sensor_values = []
        for sensor in [0, 2, 3, 5]:
            sensor_values.append(self.gpio.input(self._sensors[sensor]))

        return sensor_values

    def update(self, sensor_values):
        """
        Update the state and location of the vehicle by reading and interpreting
        the sensor values from the line follower.
        """

        if type(sensor_values) != list or len(sensor_values) != 4:
            raise ValueError("Sensor values must be a list with four elements")

        # Represent the state as an integer to allow for bit manipulations.
        state = 0
        for sensor_value in sensor_values:
            state = state << 1
            state += sensor_value

        # Check if we are at a line or at an intersection and update the
        # state and location of the vehicle accordingly.
        line = state & Line_Follower_Bit_Mask.LINE
        intersection = state & Line_Follower_Bit_Mask.INTERSECTION
        if line and not intersection:
            self._state = Line_Follower_State.AT_LINE
        elif line and intersection:
            if self._state == Line_Follower_State.AT_INTERSECTION:
                # Do not keep updating the location when the vehicle is
                # waiting at an intersection.
                return

            self._state = Line_Follower_State.AT_INTERSECTION

            # Update the location using the direction.
            if self._direction == Line_Follower_Direction.UP:
                self._location = (self._location[0], self._location[1] + 1)
            elif self._direction == Line_Follower_Direction.DOWN:
                self._location = (self._location[0], self._location[1] - 1)
            elif self._direction == Line_Follower_Direction.LEFT:
                self._location = (self._location[0] - 1, self._location[1])
            elif self._direction == Line_Follower_Direction.RIGHT:
                self._location = (self._location[0] + 1, self._location[1])

            # Notify the listener (callback) and pass the new location.
            self._callback("intersection", self._location)
        elif not line and intersection:
            # The rover has diverged from the grid. Determine where the
            # line on the grid is (left or right) so the rover controller
            # can correct its path. If we detect a line on the left and
            # on the right, we do nothing as we do not know where to
            # correct the path to. The same holds for the situation where
            # we do not detect any lines, which is why the else clause
            # is missing below.
            if intersection == Line_Follower_Bit_Mask.INTERSECTION:
                return

            is_line_left = (intersection == Line_Follower_Bit_Mask.LINE_LEFT)
            is_line_right = (intersection == Line_Follower_Bit_Mask.LINE_RIGHT)
            self._callback("diverged", "left" if is_line_left else "right")

    def set_direction(self, direction):
        """
        Set the direction of the vehicle.
        """

        if type(direction) != int or not 1 <= direction <= 4:
            raise ValueError("Direction must be one of the defined types")

        self._direction = direction
