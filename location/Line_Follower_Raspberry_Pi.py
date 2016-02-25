import time
import RPi.GPIO
from Line_Follower import Line_Follower
from ..settings import Arguments, Settings

class Line_Follower_Raspberry_Pi(Line_Follower):
    def __init__(self, location, direction, callback, settings):
        """
        Initialize the line follower object for the Raspberry Pi. Note that the
        pin numbers in the settings file are the pin numbers for the connection
        on the Raspberry Pi. These should be connected, in order, to the pins 4,
        17 (A3), 11, 14 (A0), 16 (A2) and 5 on the Zumo rover.
        """

        super(Line_Follower_Raspberry_Pi, self).__init__(location, direction, callback)

        if isinstance(settings, Arguments):
            settings = settings.get_settings("line_follower")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._sensors = settings.get("led_pins")
        if len(self._sensors) != 6:
            raise ValueError("Exactly six sensors must be defined for the Zumo robot")

        self._emitter_pin = settings.get("emitter_pin")
        self._write_delay = settings.get("write_delay")

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
        """
        Activate the line follower by turning on its IR LEDs.
        """

        self.gpio.setup(self._emitter_pin, self.gpio.OUT)
        self.gpio.output(self._emitter_pin, True)
        time.sleep(self._write_delay)

    def deactivate(self):
        """
        Deactivate the line follower by turning off its IR LEDs.
        """

        self.gpio.setup(self._emitter_pin, self.gpio.OUT)
        self.gpio.output(self._emitter_pin, False)
        time.sleep(self._write_delay)

    def read(self):
        """
        Read the values of four of the six LEDs. We only read the two innermost
        and the two outermost LEDs to clearly make a distinction between a
        straight line and an intersection of lines.
        """

        # TODO: extend
        sensor_values = []
        for sensor in [0, 2, 3, 5]:
            sensor_values.append(self.gpio.input(self._sensors[sensor]))

        return sensor_values
