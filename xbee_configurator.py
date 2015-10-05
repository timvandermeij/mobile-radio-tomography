from xbee import ZigBee
import serial
import time

class XBee_Configurator(object):
    STATUS_OK = "\x00"
    COLORS = {
        "green": "\033[92m",
        "red": "\033[91m",
        "end": "\033[0m"
    }

    def __init__(self, id, source, baud_rate):
        # Open a serial connection and initialize the sensor (ZigBee) object.
        self.id = id
        self._serial_connection = serial.Serial(source, baud_rate)
        self.sensor = ZigBee(self._serial_connection)

    def __del__(self):
        # Close the serial connection.
        self._serial_connection.close()

    def get(self, command):
        # Get a property value from the sensor.
        self._report("Getting the value of '{}'...".format(command))
        self.sensor.send("at", command=command)
        response = self.sensor.wait_read_frame()
        if "status" in response and response["status"] == self.STATUS_OK:
            value = response["parameter"]

            # Check if the value needs to be decoded.
            try:
                int(value, 16)
            except ValueError:
                # Convert the hexadecimal representation to a readable string.
                value = "".join(char.encode("hex").upper() for char in value)
                value = value.lstrip("0")

            self._report("Done getting the value of '{}': {}.".format(command, value),
                         self.COLORS["green"])
        else:
            self._report("Failed getting the value of '{}'.".format(command),
                         self.COLORS["red"])

    def set(self, command, value):
        # Set a property value on the sensor.
        self._report("Setting '{}' to '{}'...".format(command, value))

        converted_value = value
        if type(value) == int:
            # Convert to a string, zero-fill and create a hexadecimal representation.
            converted_value = str(converted_value)
            converted_value = converted_value.zfill(len(converted_value) +
                                                    len(converted_value) % 2).decode("hex")
        elif type(value) != str:
            raise TypeError("Unsupported type for conversion to hexadecimal.")

        self.sensor.send("at", command=command, parameter=converted_value)
        response = self.sensor.wait_read_frame()
        if "status" in response and response["status"] == self.STATUS_OK:
            self._report("Done setting '{}' to '{}'.".format(command, value),
                         self.COLORS["green"])
        else:
            self._report("Failed setting '{}' to '{}'.".format(command, value),
                         self.COLORS["red"])

    def write(self):
        # Write queued changes to the sensor.
        self._report("Writing queued changes...")
        self.sensor.send("at", command="WR")
        response = self.sensor.wait_read_frame()
        if "status" in response and response["status"] == self.STATUS_OK:
            self._report("Done writing queued changes.", self.COLORS["green"])
        else:
            self._report("Failed writing queued changes.", self.COLORS["red"])

    def _report(self, message, color=None):
        if color == None:
            print("[Sensor {}] {}".format(self.id, message))
        else:
            print("{}[Sensor {}] {}{}".format(color, self.id, message, self.COLORS["end"]))

def main():
    id = 4
    xbee_configurator = XBee_Configurator(id, "/dev/ttyUSB1", 9600)
    xbee_configurator.set("ID", 5678)
    xbee_configurator.set("NI", str(id))
    xbee_configurator.write()
    xbee_configurator.get("ID")
    xbee_configurator.get("NI")
    del xbee_configurator

if __name__ == "__main__":
    main()
