import time
from xbee import ZigBee
from ..settings import Arguments, Settings

class XBee_Response_Status(object):
    OK = "\x00"

class XBee_Configurator(object):
    def __init__(self, settings, usb_manager):
        """
        Initialize the XBee configurator.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_configurator")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._usb_manager = usb_manager
        self._serial_connection = self._usb_manager.get_xbee_device()
        self._sensor = ZigBee(self._serial_connection)
        time.sleep(self.settings.get("startup_delay"))

    def _encode_value(self, value):
        """
        Encode a given value, if possible, by converting the human-readable
        integer to a hexadecimal representation.
        """

        if isinstance(value, int):
            # Convert to a string, zero-fill and create the hexadecimal representation.
            value = str(value)
            value = value.zfill(len(value) + len(value) % 2).decode("hex")
        elif not isinstance(value, str):
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
        if "status" in response and response["status"] == XBee_Response_Status.OK:
            return self._decode_value(response["parameter"])

        return None

    def set(self, command, value):
        """
        Set a property value on the XBee chip.
        """

        self._sensor.send("at", command=command, parameter=self._encode_value(value))
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == XBee_Response_Status.OK)

    def write(self):
        """
        Write queued changes to the XBee chip.
        """

        self._sensor.send("at", command="WR")
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == XBee_Response_Status.OK)
