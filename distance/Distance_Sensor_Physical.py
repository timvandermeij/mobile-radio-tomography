import time
import RPi.GPIO
from ..settings import Settings
from Distance_Sensor import Distance_Sensor

class Distance_Sensor_Physical(Distance_Sensor):
    def __init__(self):
        """
        Initialize the physical distance sensor by, most importantly, setting
        the echo and trigger pin numbers.
        """

        self.settings = Settings("settings.json", "distance_sensor_physical")

        # Initialize the RPi.GPIO module. Doing it this way instead of using
        # an alias during import allows unit tests to access it too.
        self.gpio = RPi.GPIO

        # Disable warnings about pins being in use.
        self.gpio.setwarnings(False)

        # Use board numbering which corresponds to the pin numbers on the
        # P1 header of the board.
        self.gpio.setmode(self.gpio.BOARD)

        # Configure the input and output pins.
        self.gpio.setup(self.settings.get("echo_pin"), self.gpio.IN)
        self.gpio.setup(self.settings.get("trigger_pin"), self.gpio.OUT)
        
        # Set trigger to false.
        self.gpio.output(self.settings.get("trigger_pin"), False)
        time.sleep(self.settings.get("interval_delay"))

    def get_distance(self):
        """
        Perform a single distance measurement.
        """

        # Trigger the sensor to start measuring.
        self.gpio.output(self.settings.get("trigger_pin"), True)
        time.sleep(self.settings.get("trigger_delay"))
        self.gpio.output(self.settings.get("trigger_pin"), False)

        # Set the start time when the sensor is starting to send a signal.
        start = time.time()
        while self.gpio.input(self.settings.get("echo_pin")) == 0:
            start = time.time()

        # Move the end time when the signal has not been returned yet.
        end = time.time()
        while self.gpio.input(self.settings.get("echo_pin")) == 1:
            end = time.time()

        return self._convert_elapsed_time_to_distance(end - start)

    def _convert_elapsed_time_to_distance(self, elapsed_time):
        """
        Calculate the distance (in centimeters) from the elapsed time between
        sending and receiving the signal. We divide by two since the signal
        travels the distance twice (back and forth).
        """

        distance_meters = (elapsed_time * self.settings.get("speed_of_sound")) / 2
        return distance_meters / 100
