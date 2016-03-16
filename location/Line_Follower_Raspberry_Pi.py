import time
import RPi.GPIO
from Line_Follower import Line_Follower
from ..settings import Arguments, Settings

class Line_Follower_Raspberry_Pi(Line_Follower):
    def __init__(self, location, direction, callback, settings, thread_manager, usb_manager, delay=0):
        """
        Initialize the line follower object for the Raspberry Pi. Note that the
        pin numbers in the settings file are the pin numbers for the connection
        on the Raspberry Pi. These should be connected, in order, to the pins 4,
        17 (A3), 11, 14 (A0), 16 (A2) and 5 on the Zumo rover.
        """

        super(Line_Follower_Raspberry_Pi, self).__init__(location, direction, callback, thread_manager, delay)

        if isinstance(settings, Arguments):
            settings = settings.get_settings("line_follower_raspberry_pi")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._sensors = settings.get("led_pins")
        if len(self._sensors) != 6:
            raise ValueError("Exactly six sensors must be defined for the Zumo robot")

        self._emitter_pin = settings.get("emitter_pin")
        self._write_delay = settings.get("write_delay")
        self._readable_leds = settings.get("readable_leds")
        self._max_value = settings.get("max_value")
        self._charge_delay = settings.get("charge_delay")
        self._line_threshold = settings.get("line_threshold")

        # Initialize the RPi.GPIO module. Doing it this way instead of using
        # an alias during import allows unit tests to access it too.
        self.gpio = RPi.GPIO

        # Disable warnings about pins being in use.
        self.gpio.setwarnings(False)

        # Use board numbering which corresponds to the pin numbers on the
        # P1 header of the board.
        self.gpio.setmode(self.gpio.BOARD)

    def enable(self):
        """
        Enable the line follower by turning on its IR LEDs.
        """

        self.gpio.setup(self._emitter_pin, self.gpio.OUT)
        self.gpio.output(self._emitter_pin, True)
        time.sleep(self._write_delay)

    def disable(self):
        """
        Disable the line follower by turning off its IR LEDs.
        """

        self.gpio.setup(self._emitter_pin, self.gpio.OUT)
        self.gpio.output(self._emitter_pin, False)
        time.sleep(self._write_delay)

    def read(self):
        """
        Read the values of the line follower's IR LEDs.
        """

        # Initialize the sensor values with the maximum value
        # returned by the A/D conversion. Drive the sensor lines
        # high and charge them for a fixed amount of time.
        sensor_values = []
        for led in self._readable_leds:
            sensor_values.append(self._max_value)
            self.gpio.setup(self._sensors[led], self.gpio.OUT)
            self.gpio.output(self._sensors[led], True)

        time.sleep(self._charge_delay)

        # Drive the sensor lines low and set them as inputs.
        # Disable the internal pull-up resistors.
        for led in self._readable_leds:
            self.gpio.setup(self._sensors[led], self.gpio.IN, pull_up_down=self.gpio.PUD_DOWN)
            self.gpio.setup(self._sensors[led], self.gpio.IN)

        # Determine the values of the sensors. The documentation of
        # the Zumo reflectance sensor array states that strong
        # reflectance causes a low voltage decay time and weak
        # reflectance causes a high voltage decay time. We have
        # initialized the sensor values above with the maximum
        # values, so we assume the weakest possible reflectance, i.e.,
        # we assume that the vehicle is on a line and therefore that
        # the measured signal is constantly high (because a black
        # surface has a weak reflectance). When the signal does become
        # low, we update the sensor value with the elapsed time since
        # the start, which then is a measure of how reflective the
        # surface is.
        start_time = time.time()
        while ((time.time() - start_time) * 1e6) < self._max_value:
            elapsed_time = (time.time() - start_time) * 1e6
            for index, led in enumerate(self._readable_leds):
                led_value = self.gpio.input(self._sensors[led])
                if not led_value and elapsed_time < sensor_values[index]:
                    sensor_values[index] = elapsed_time

        # Convert the sensor values to binary. If the sensor value is
        # above a threshold value, we say that the vehicle is above a line.
        sensor_values = [int(sensor_value > self._line_threshold) for sensor_value in sensor_values]

        return sensor_values
