import serial
import time
import random
import copy
import Queue
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
        self._queue = Queue.Queue()
        self._node_identifier_set = False
        self._verbose = self.settings.get("verbose")

        # Prepare the packet and sensor data.
        self._custom_packet_limit = self.settings.get("custom_packet_limit")
        self._number_of_sensors = self.settings.get("number_of_sensors")
        self._sensors = self.settings.get("sensors")
        for index, address in enumerate(self._sensors):
            self._sensors[index] = address.decode("string_escape")

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

    def enqueue(self, packet):
        """
        Enqueue a custom packet to send to another XBee device.
        Valid packets must be XBee_Packet objects and must contain
        the ID of the destination XBee device.
        """

        if not isinstance(packet, XBee_Packet):
            raise TypeError("Only XBee_Packet objects can be enqueued")

        packet.set("_type", "custom")
        if packet.get("to_id") != None:
            self._queue.put(packet)
        else:
            # No destination ID has been provided, therefore we broadcast
            # the packet to all sensors in the network except for ourself
            # and the ground sensor.
            for index in xrange(1, self.settings.get("number_of_sensors") + 1):
                if index == self.id:
                    continue

                packet.set("to_id", index)
                self._queue.put(copy.deepcopy(packet))

    def _send(self):
        """
        Send a packet to each other sensor in the network.
        """

        packet = XBee_Packet()
        packet.set("_from", self._location_callback())
        packet.set("_from_id", self.id)
        packet.set("_timestamp", time.time())
        for index in xrange(1, self._number_of_sensors + 1):
            if index == self.id:
                continue

            self._sensor.send("tx", dest_addr_long=self._sensors[index],
                              dest_addr="\xFF\xFE", frame_id="\x00",
                              data=packet.serialize())

            if self._verbose:
                print("--> Sending to sensor {}.".format(index))

        # Send custom packets to their destination. Since the time slots are
        # limited in length, so is the number of custom packets we transfer
        # in each sweep.
        limit = self._custom_packet_limit
        while not self._queue.empty():
            if limit == 0:
                break

            limit -= 1
            packet = self._queue.get()
            to_id = packet.get("to_id")
            self._sensor.send("tx", dest_addr_long=self._sensors[to_id],
                              dest_addr="\xFF\xFE", frame_id="\x00",
                              data=packet.serialize())

        # Send the sweep data to the ground sensor and clear the list
        # for the next round.
        for frame_id in self._data.keys():
            packet = self._data[frame_id]
            if packet.get("_rssi") == None:
                continue

            self._sensor.send("tx", dest_addr_long=self._sensors[0],
                              dest_addr="\xFF\xFE", frame_id="\x00",
                              data=packet.serialize())

            self._data.pop(frame_id)

            if self._verbose:
                print("--> Sending to ground station.")

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

            if packet.get("_type") == "custom":
                packet.unset("_type")
                print("[{}] Custom packet received {}".format(time.time(), packet.serialize()))
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
