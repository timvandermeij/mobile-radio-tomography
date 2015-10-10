# TODO: Fix the start-up delay such that sensors start transmitting immediately.
# TODO: Unit testing.
# TODO: RSSI list and transmission to ground station.

import serial
import json
import time
from xbee import ZigBee
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Physical(XBee_Sensor):
    STATUS_OK = "\x00"

    def __init__(self, sensor_id, settings, scheduler):
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
        self.scheduler = scheduler
        self.next_timestamp = self.scheduler.get_next_timestamp()
        self._serial_connection = None
        self._sensor = None
        self._address = None

    def activate(self):
        """
        Activate the sensor by sending a packet if it is not a ground station.
        The sensor always receives packets asynchronously.
        """

        # Lazily initialize the serial connection and ZigBee object.
        if self._serial_connection == None and self._sensor == None:
            self._serial_connection = serial.Serial("/dev/ttyUSB{}".format(self.id - 1),
                                                    self.settings.get("baud_rate"))
            self._sensor = ZigBee(self._serial_connection, callback=self._receive)

            # Set this sensor's address.
            self._sensor.send("at", command="SH")
            self._sensor.send("at", command="SL")

        if self.id > 0 and time.time() >= self.next_timestamp:
            self._send()
            self.next_timestamp = self.scheduler.get_next_timestamp()

    def deactivate(self):
        """
        Deactivate the sensor and close the serial connection.
        """

        self._sensor.halt()
        self._serial_connection.close()

    def _send(self):
        """
        Send a packet to each other sensor in the network.
        """

        packet = {
            "from": self.id,
            "timestamp": time.time()
        }
        for sensor_address in self.settings.get("sensors"):
            # Unescape the string as it is escaped in JSON.
            sensor_address = sensor_address.decode("string_escape")

            if sensor_address != self._address:
                self._sensor.send("tx", dest_addr_long=sensor_address,
                                  dest_addr="\xFF\xFE", frame_id="\x01",
                                  data=json.dumps(packet))

    def _receive(self, packet):
        """
        Receive and process a received packet from another sensor in the network.
        """

        if self.id > 0:
            if packet["id"] == "rx":
                payload = json.loads(packet["rf_data"])

                print("Sensor {} received a packet from sensor {}.".format(self.id, payload["from"]))

                # Synchronize the scheduler using the timestamp in the payload.
                self.next_timestamp = self.scheduler.synchronize(payload)

                # Request the RSSI value for the received packet.
                self._sensor.send("at", command="DB")
            elif packet["id"] == "at_response":
                if packet["command"] == "DB":
                    # RSSI value has been received.
                    rssi = ord(packet["parameter"])
                    print("Sensor {} received the packet with RSSI -{} dBm.".format(self.id, rssi))
                elif packet["command"] == "SH":
                    # Serial number (high) has been received.
                    if self._address == None:
                        self._address = packet["parameter"]
                    else:
                        self._address = packet["parameter"] + self._address
                elif packet["command"] == "SL":
                    # Serial number (low) has been received.
                    if self._address == None:
                        self._address = packet["parameter"]
                    else:
                        self._address = self._address + packet["parameter"]
