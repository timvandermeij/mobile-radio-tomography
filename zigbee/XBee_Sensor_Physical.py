import serial
import time
import random
from xbee import ZigBee
from XBee_Packet import XBee_Packet
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Physical(XBee_Sensor):
    def __init__(self, sensor_id, settings, scheduler, location_callback):
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
        self._location_callback = location_callback
        self._next_timestamp = self.scheduler.get_next_timestamp()
        self._serial_connection = None
        self._sensor = None
        self._address = None
        self._data = {}
        self._node_identifier_set = False
        self._verbose = self.settings.get("verbose")

    def activate(self):
        """
        Activate the sensor by sending a packet if it is not a ground station.
        The sensor always receives packets asynchronously.
        """

        # Lazily initialize the serial connection and ZigBee object.
        if self._serial_connection == None and self._sensor == None:
            self._serial_connection = serial.Serial(self.settings.get("port"),
                                                    self.settings.get("baud_rate"))
            self._sensor = ZigBee(self._serial_connection, callback=self._receive)
            time.sleep(self.settings.get("startup_delay"))

        if not self._node_identifier_set:
            # Request this sensor's ID and address.
            self._sensor.send("at", command="NI")
            self._sensor.send("at", command="SH")
            self._sensor.send("at", command="SL")
            return

        if self.id > 0 and time.time() >= self._next_timestamp:
            self._next_timestamp = self.scheduler.get_next_timestamp()
            self._send()

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

        packet = XBee_Packet()
        packet.set("_from", self._location_callback())
        packet.set("_from_id", self.id)
        packet.set("_timestamp", time.time())
        sensors = self.settings.get("sensors")
        for index, sensor_address in enumerate(sensors):
            # Unescape the string as it is escaped in JSON.
            sensor_address = sensor_address.decode("string_escape")

            # Do not send to yourself or the ground sensor.
            if sensor_address != self._address and index > 0:
                self._sensor.send("tx", dest_addr_long=sensor_address,
                                  dest_addr="\xFF\xFE", frame_id="\x00",
                                  data=packet.serialize())

                if self._verbose:
                    print("--> Sending to sensor {}.".format(index))

        # Send the sweep data to the ground sensor and clear the list for 
        # the next round. Note that we use a copy to make sure that the
        # sweep data list does not change in size during iteration.
        ground_sensor_address = sensors[0].decode("string_escape")
        data = self._data.copy()
        for frame_id, packet in data.iteritems():
            if packet == None or packet.get("_rssi") == None:
                continue

            self._sensor.send("tx", dest_addr_long=ground_sensor_address,
                              dest_addr="\xFF\xFE", frame_id="\x00",
                              data=packet.serialize())

            if self._verbose:
                print("--> Sending to ground station.")

            self._data[frame_id] = None

    def _receive(self, raw_packet):
        """
        Receive and process a raw packet from another sensor in the network.
        """

        if raw_packet["id"] == "rx":
            try:
                packet = XBee_Packet()
                packet.unserialize(raw_packet["rf_data"])
            except:
                # The raw packet is malformed, so drop it.
                return

            if self.id == 0:
                print("[{}] Ground station received {}".format(time.time(), packet.serialize()))
                return

            if self._verbose:
                print("<-- Received from sensor {}.".format(packet.get("_from_id")))

            # Synchronize the scheduler using the timestamp in the packet.
            self._next_timestamp = self.scheduler.synchronize(packet)

            # Sanitize and complete the packet for the ground station.
            packet.set("_to", self._location_callback())
            packet.unset("_from_id")
            packet.unset("_timestamp")

            # Generate a frame ID to be able to match this packet and the
            # associated RSSI (DB command) request.
            frame_id = chr(random.randint(1, 255))
            self._data[frame_id] = packet

            # Request the RSSI value for the received packet.
            self._sensor.send("at", command="DB", frame_id=frame_id)
        elif raw_packet["id"] == "at_response":
            if raw_packet["command"] == "DB":
                # RSSI value has been received. Update the original packet.
                if raw_packet["frame_id"] in self._data:
                    original_packet = self._data[raw_packet["frame_id"]]
                    original_packet.set("_rssi", ord(raw_packet["parameter"]))
            elif raw_packet["command"] == "SH":
                # Serial number (high) has been received.
                if self._address == None:
                    self._address = raw_packet["parameter"]
                elif raw_packet["parameter"] not in self._address:
                    self._address = raw_packet["parameter"] + self._address
            elif raw_packet["command"] == "SL":
                # Serial number (low) has been received.
                if self._address == None:
                    self._address = raw_packet["parameter"]
                elif raw_packet["parameter"] not in self._address:
                    self._address = self._address + raw_packet["parameter"]
            elif raw_packet["command"] == "NI":
                # Node identifier has been received.
                self.id = int(raw_packet["parameter"])
                self.scheduler.id = self.id
                self._node_identifier_set = True

                if self._verbose:
                    print("Node identifier set to {}.".format(self.id))
