from xbee import ZigBee
import serial

class XBee_Configurator(object):
    STATUS_OK = "\x00"

    def __init__(self, id, port, baud_rate):
        # Open a serial connection and initialize the sensor (ZigBee) object.
        self.id = id
        self._serial_connection = serial.Serial(port, baud_rate)
        self._sensor = ZigBee(self._serial_connection)

    def __del__(self):
        # Close the serial connection.
        self._serial_connection.close()

    def _encode_value(self, value):
        if type(value) == int:
            # Convert to a string, zero-fill and create a hexadecimal representation.
            value = str(value)
            value = value.zfill(len(value) + len(value) % 2).decode("hex")
        elif type(value) != str:
            raise TypeError("Unsupported type for conversion to hexadecimal.")

        return value

    def _decode_value(self, value):
        # Check if a given value needs to be decoded.
        try:
            int(value, 16)
        except ValueError:
            # Convert the hexadecimal representation to a readable string.
            value = "".join(char.encode("hex").upper() for char in value)
            value = value.lstrip("0")

        return value

    def get(self, command):
        # Get a property value from the sensor.
        self._sensor.send("at", command=command)
        response = self._sensor.wait_read_frame()
        if "status" in response and response["status"] == self.STATUS_OK:
            return self._decode_value(response["parameter"])

        return None

    def set(self, command, value):
        # Set a property value on the sensor.
        self._sensor.send("at", command=command, parameter=self._encode_value(value))
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == self.STATUS_OK)

    def write(self):
        # Write queued changes to the sensor.
        self._sensor.send("at", command="WR")
        response = self._sensor.wait_read_frame()
        return ("status" in response and response["status"] == self.STATUS_OK)
