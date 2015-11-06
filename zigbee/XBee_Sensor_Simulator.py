import time
import socket
import random
import copy
import Queue
from XBee_Packet import XBee_Packet
from XBee_Sensor import XBee_Sensor
from XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..settings import Arguments

class XBee_Sensor_Simulator(XBee_Sensor):
    def __init__(self, arguments, location_callback=None, receive_callback=None, viewer=None):
        """
        Initialize the sensor with a unique, non-blocking UDP socket.
        """

        if isinstance(arguments, Arguments):
            self.settings = arguments.get_settings("xbee_sensor_simulator")
        else:
            raise ValueError("'arguments' must be an instance of Arguments")

        if location_callback == None or receive_callback == None:
            raise TypeError("Missing required location and receive callbacks")

        self.id = self.settings.get("xbee_id")
        self.viewer = viewer
        self.scheduler = XBee_TDMA_Scheduler(self.id, arguments)
        self._location_callback = location_callback
        self._receive_callback = receive_callback
        self._next_timestamp = self.scheduler.get_next_timestamp()
        self._data = []
        self._queue = Queue.Queue()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self._socket.setblocking(0)

    def activate(self):
        """
        Activate the sensor to send and receive packets.
        The ground sensor (with ID 0) can only receive packets.
        """

        if self.id > 0 and time.time() >= self._next_timestamp:
            self._next_timestamp = self.scheduler.get_next_timestamp()
            self._send()

        try:
            packet = XBee_Packet()
            packet.unserialize(self._socket.recv(self.settings.get("buffer_size")))
            self._receive(packet)
        except socket.error:
            pass

    def deactivate(self):
        """
        Deactivate the sensor by closing the socket.
        """

        self._socket.close()

    def enqueue(self, packet, to=None):
        """
        Enqueue a custom packet to send to another XBee device.
        """

        if not isinstance(packet, XBee_Packet):
            raise TypeError("Only XBee_Packet objects can be enqueued")

        packet.set("_type", "custom")
        if to != None:
            self._queue.put({
                "packet": packet,
                "to": to
            })
        else:
            # No destination ID has been provided, therefore we broadcast
            # the packet to all sensors in the network except for ourself
            # and the ground sensor.
            for to_id in xrange(1, self.settings.get("number_of_sensors") + 1):
                if to_id == self.id:
                    continue

                self._queue.put({
                    "packet": copy.deepcopy(packet),
                    "to": to_id
                })

    def _send(self):
        """
        Send packets to all other sensors in the network.
        """

        ip = self.settings.get("ip")
        port = self.settings.get("port")

        if self.viewer:
            self.viewer.clear_arrows()
        for i in xrange(1, self.settings.get("number_of_sensors") + 1):
            if i == self.id:
                continue

            packet = XBee_Packet()
            packet.set("_from", self._location_callback())
            packet.set("_from_id", self.id)
            packet.set("_timestamp", time.time())
            self._socket.sendto(packet.serialize(), (ip, port + i))
            if self.viewer:
                self.viewer.draw_arrow(self.id, i)

        # Send custom packets to their destination. Since the time slots are
        # limited in length, so is the number of custom packets we transfer
        # in each sweep.
        limit = self.settings.get("custom_packet_limit")
        while not self._queue.empty():
            if limit == 0:
                break

            limit -= 1
            item = self._queue.get()
            self._socket.sendto(item["packet"].serialize(), (ip, port + item["to"]))
            if self.viewer:
                self.viewer.draw_arrow(self.id, item["to"], "green")

        # Send the sweep data to the ground sensor.
        for packet in self._data:
            self._socket.sendto(packet.serialize(), (ip, port))
            if self.viewer:
                self.viewer.draw_arrow(self.id, 0, "blue")

        self._data = []

        if self.viewer:
            self.viewer.refresh()

    def _receive(self, packet):
        """
        Receive and process packets from all other sensors in the network.
        """

        if packet.get("_type") == "custom":
            packet.unset("_type")
            self._receive_callback(packet)
        else:
            if self.id > 0:
                self._next_timestamp = self.scheduler.synchronize(packet)

                # Sanitize and complete the packet for the ground station.
                packet.set("_to", self._location_callback())
                packet.set("_rssi", random.randint(0, 60))
                packet.unset("_from_id")
                packet.unset("_timestamp")
                self._data.append(packet)
            else:
                print("> Ground station received {}".format(packet.serialize()))
