from xbee import ZigBee
import serial
import time
from ..settings import Arguments, Settings

class XBee_Configurator(object):
    STATUS_OK = "\x00"

    def __init__(self, settings):
        """
        Open a serial connection to the XBee chip.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_configurator")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._serial_connection = serial.Serial(self.settings.get("port"),
                                                self.settings.get("baud_rate"))
        self._sensor = ZigBee(self._serial_connection)
        time.sleep(self.settings.get("startup_delay"))

    def __del__(self):
        """
        Close the serial connection to the XBee chip.
        """

        self._serial_connection.close()

    def _encode_value(self, value):
        """
        Encode a given value, if possible, by converting the human-readable
        integer to a hexadecimal representation.
        """

        if type(value) == int:
            # Convert to a string, zero-fill and create the hexadecimal representation.
            value = str(value)
            value = value.zfill(len(value) + len(value) % 2).decode("hex")
        elif type(value) != str:
            raise TypeError("Unsupported type for conversion to hexadecimal.")

        return value

    def _decode_value(self, value):
        """
        Decode a given value, if required, by converting the hexadecimal
        representation to a human-readable string.
        """

        try:
            int(value, 16)
        except ValueError:
            value = "".join(char.encode("hex").upper() for char in value)

        return int(value)

    def get(self, command):
        """
        Get a property value from the XBee chip.
        """

        self._sensor.send("at", command=command)
        response = self._sensor.wait_read_frame()
        if "status" in response and response["status"] == self.STATUS_OK:
            return self._decode_value(response["parameter"])

        return None

    def set(self, command, value):
        """
        Set a property value on the XBee chip.
        """

        self._sensor.send("at", command=command, parameter=self._encode_value(value))
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == self.STATUS_OK)

    def write(self):
        """
        Write queued changes to the XBee chip.
        """

        self._sensor.send("at", command="WR")
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == self.STATUS_OK)
