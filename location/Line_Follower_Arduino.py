from serial import SerialException
from Line_Follower import Line_Follower
from ..core.USB_Manager import USB_Manager
from ..settings import Arguments, Settings

class Line_Follower_Arduino(Line_Follower):
    def __init__(self, location, direction, callback, settings, thread_manager,
                 usb_manager=None, delay=0):
        """
        Initialize the line follower object for the Arduino.
        """

        super(Line_Follower_Arduino, self).__init__(location, direction, callback,
                                                    thread_manager, delay)

        if isinstance(settings, Arguments):
            settings = settings.get_settings("line_follower_arduino")
        elif not isinstance(settings, Settings):
            raise TypeError("'settings' must be an instance of Settings or Arguments")

        if not isinstance(usb_manager, USB_Manager):
            raise TypeError("'usb_manager' must be provided to the Arduino line follower")

        self._readable_leds = settings.get("readable_leds")
        self._line_threshold = settings.get("line_threshold")

        # Initialize the serial connection.
        self._serial_connection = usb_manager.get_ttl_device()
        self._serial_connection.reset_input_buffer()

    def get_serial_connection(self):
        return self._serial_connection

    def enable(self):
        """
        Enable the line follower by turning on its IR LEDs.
        """

        # The Arduino will do this when it reads the raw sensor values.
        pass

    def disable(self):
        """
        Disable the line follower by turning off its IR LEDs.
        """

        # The Arduino will do this when it reads the raw sensor values.
        pass

    def read(self):
        """
        Read the values of the line follower's IR LEDs.
        """

        # Read a line with raw sensor values. This is blocking until such a line is presented
        # over the serial connection, so this should be run in a separate thread.
        raw_sensor_values = None
        while raw_sensor_values is None:
            try:
                line = self._serial_connection.readline()
            except (SerialException, TypeError) as e:
                # Ignore serial exceptions when we are stopped, since they are 
                # about reading from closed ports and consequently bad file 
                # descriptors.
                if not self._running:
                    return None

                raise e

            try:
                split_line = line.lstrip('\0').rstrip().split(' ')
                raw_sensor_values = [
                    float(sensor_value) for sensor_value in split_line
                ]
            except (ValueError, AttributeError):
                # Ignore lines that we cannot parse.
                pass

            if not self._running:
                return None

        # Keep only the values of the LEDs we are interested in.
        sensor_values = []
        for index, value in enumerate(raw_sensor_values):
            if index in self._readable_leds:
                sensor_values.append(value)

        # Convert the sensor values to binary. If the sensor value is
        # above a threshold value, we say that the vehicle is above a line.
        sensor_values = [
            int(value > self._line_threshold) for value in sensor_values
        ]

        return sensor_values
