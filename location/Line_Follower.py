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
    LINE = 0xb0110
    INTERSECTION = 0xb1001

class Line_Follower(object):
    def __init__(self, location, direction, intersection_callback, settings):
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

        if not isinstance(direction, Line_Follower_Direction):
            raise ValueError("Direction must be one of the defined types")

        self._location = location
        self._direction = direction
        self._intersection_callback = intersection_callback
        self._state = Line_Follower_State.AT_INTERSECTION

        self._sensors = settings.get("sensors")
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

    def update(self):
        """
        Update the state and location of the vehicle by reading and interpreting
        the values from the line follower.
        """

        # Read the state of four of the six LEDs. We only read the two innermost
        # and the two outermost LEDs to clearly make a distinction between a
        # straight line and an intersection of lines.
        sensor_0 = self.gpio.input(self._sensors[0])
        sensor_2 = self.gpio.input(self._sensors[2])
        sensor_3 = self.gpio.input(self._sensors[3])
        sensor_5 = self.gpio.input(self._sensors[5])

        # Represent the state as an integer to allow for bit manipulations.
        state = 0
        for sensor in [sensor_0, sensor_2, sensor_3, sensor_5]:
            state = state << 1
            state += sensor

        # Check if we have a line on the left or on the right, i.e., if we are
        # at an intersection.
        line = state & Line_Follower_Bit_Mask.LINE
        intersection = state & Line_Follower_Bit_Mask.INTERSECTION
        if line and not intersection:
            self._state = Line_Follower_State.AT_LINE
        else:
            self._state = Line_Follower_State.AT_INTERSECTION
            
            # Update the location using the direction.
            if self._direction == Line_Follower_Direction.UP:
                self._location[1] += 1
            elif self._direction == Line_Follower_Direction.DOWN:
                self._location[1] -= 1
            elif self._direction == Line_Follower_Direction.LEFT:
                self._location[0] -= 1
            else:
                self._location[0] += 1

            # Notify the listener (callback) and pass the new location.
            self._intersection_callback(self_location)

    def set_direction(self, direction):
        """
        Set the direction of the vehicle.
        """

        if not isinstance(direction, Line_Follower_Direction):
            raise ValueError("Direction must be one of the defined types")

        self._direction = direction
