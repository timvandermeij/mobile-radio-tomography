from xbee import ZigBee
import serial
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Physical(XBee_Sensor):
    STATUS_OK = "\x00"

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
        self._sensor = ZigBee(self._serial_connection, callback=self.receive)

    def __del__(self):
        """
        Stop the sensor and close the serial connection.
        """

        self._sensor.halt()
        self._serial_connection.close()

    # TODO: Implement this.
    def activate(self):
        pass

    # TODO: Fix packet delays. Most likely due to broadcasting: it is suggested that
    # first doing a network discovery and then unicasting to each sensor is more
    # performant. Otherwise look into packetization timeout and baud rate/CTS/RTS.
    # TODO: Document that exactly one sensor needs to be a coordinator.
    def _send(self):
        """
        Send a packet to all sensors in the network (broadcasting). Because of
        the broadcasting, we do not receive an acknowledgement, therefore this
        method returns nothing.
        """

        # Broadcast the packet.
        self._sensor.send("tx", dest_addr_long="\x00\x00\x00\x00\x00\x00\xFF\xFF", dest_addr="\xFF\xFE",
                          frame_id="\x01", data="Data from sensor {}".format(self.id))

        # Request the RSSI value.
        self._sensor.send("at", command="DB")

    # TODO: Implement this by moving the method below after changing the base class.
    def _receive(self):
        pass

    # TODO: Somehow the asynchronicity makes the terminal hang when a keyboard
    # interrupt happens.
    def receive(self, packet):
        """
        Print a received packet from another sensor in the network.
        """
        
        if "rf_data" in packet:
            print("[Sensor {}] Received packet '{}'".format(self.id, packet))
            response = self._sensor.send("at", command="DB")
        elif "parameter" in packet:
            print("The RSSI value is {}.".format(ord(packet["parameter"])))
