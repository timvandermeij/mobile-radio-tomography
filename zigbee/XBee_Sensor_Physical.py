# TODO: Fix hang after keyboard interrupt (destructor, asynchronicity).
# TODO: Implement network discovery to remove the hardcoded sensors array.
# TODO: Fix the start-up delay such that sensors start transmitting immediately.
# TODO: Unit testing.

from xbee import ZigBee
import serial
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Physical(XBee_Sensor):
    STATUS_OK = "\x00"
    SENSORS = [
        "\x00\x13\xa2\x00@\xe6n\xb9", # Address of sensor 1
        "\x00\x13\xa2\x00@\xe6o5" # Address of sensor 2
    ]

    def __init__(self, sensor_id, settings):
        """
        Initialize the sensor.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_sensor_physical")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self.id = sensor_id
        self._serial_connection = serial.Serial("/dev/ttyUSB{}".format(self.id - 1),
                                                self.settings.get("baud_rate"))
        self._sensor = ZigBee(self._serial_connection, callback=self._receive)

    def __del__(self):
        """
        Stop the sensor and close the serial connection.
        """

        self._sensor.halt()
        self._serial_connection.close()

    def activate(self):
        """
        Activate the sensor by sending a packet if it is not a ground station.
        The sensor always receives packets asynchronously.
        """

        if self.id > 0:
            self._send()

    def _send(self):
        """
        Send a packet to a sensor in the network.
        """

        self._sensor.send("tx", dest_addr_long=self.SENSORS[self.id % 2], dest_addr="\xFF\xFE",
                          frame_id="\x01", data="Data from sensor {}".format(self.id))

    def _receive(self, packet):
        """
        Receive and process a received packet from another sensor in the network.
        """

        if "rf_data" in packet:
            print("Sensor {} received '{}'".format(self.id, packet["rf_data"]))

            # Request the RSSI value for the received packet.
            self._sensor.send("at", command="DB")
        elif "parameter" in packet:
            rssi = ord(packet["parameter"])
            print("Sensor {} received the packet with RSSI {}.".format(self.id, rssi))
