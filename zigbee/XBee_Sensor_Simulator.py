import thread
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
    def __init__(self, arguments, thread_manager, usb_manager,
                 location_callback, receive_callback, valid_callback):
        """
        Initialize the sensor with a unique, non-blocking UDP socket.
        """

        super(XBee_Sensor_Simulator, self).__init__(thread_manager, usb_manager,
                                                    location_callback, receive_callback, valid_callback)

        if isinstance(arguments, Arguments):
            self.settings = arguments.get_settings("xbee_sensor_simulator")
        else:
            raise ValueError("'arguments' must be an instance of Arguments")

        self.id = self.settings.get("xbee_id")
        self.scheduler = XBee_TDMA_Scheduler(self.id, arguments)
        self._next_timestamp = self.scheduler.get_next_timestamp()
        self._data = []
        self._queue = Queue.Queue()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self._socket.setblocking(0)
        self._active = False
        self._loop_delay = self.settings.get("loop_delay")

    def activate(self):
        """
        Activate the sensor to send and receive packets.
        The ground sensor (with ID 0) can only receive packets.
        """

        super(XBee_Sensor_Simulator, self).activate()

        if not self._active:
            self._active = True
            thread.start_new_thread(self._loop, ())

    def _loop(self):
        """
        Execute the sensor loop. This runs in a separate thread.
        """

        try:
            while self._active:
                if self.id > 0 and time.time() >= self._next_timestamp:
                    self._next_timestamp = self.scheduler.get_next_timestamp()
                    self._send()

                # Check if there is data to be processed.
                try:
                    data = self._socket.recv(self.settings.get("buffer_size"))
                except socket.error:
                    continue

                # Unserialize the data (byte-encoded string).
                packet = XBee_Packet()
                packet.unserialize(data)
                self._receive(packet)

                time.sleep(self._loop_delay)
        except:
            super(XBee_Sensor_Simulator, self).interrupt()

    def deactivate(self):
        """
        Deactivate the sensor by closing the socket.
        """

        super(XBee_Sensor_Simulator, self).deactivate()

        if self._active:
            self._active = False
            self._socket.close()

    def enqueue(self, packet, to=None):
        """
        Enqueue a custom packet to send to another XBee device.
        """

        if not isinstance(packet, XBee_Packet):
            raise TypeError("Only XBee_Packet objects can be enqueued")

        if packet.is_private():
            raise ValueError("Private packets cannot be enqueued")

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

        for i in xrange(1, self.settings.get("number_of_sensors") + 1):
            if i == self.id:
                continue

            packet = self.make_rssi_broadcast_packet()
            packet.set("sensor_id", self.id)
            self._socket.sendto(packet.serialize(), (ip, port + i))

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

        # Send the sweep data to the ground sensor.
        for packet in self._data:
            self._socket.sendto(packet.serialize(), (ip, port))

        self._data = []

    def _receive(self, packet):
        """
        Receive and process packets from all other sensors in the network.
        """

        if not self.check_receive(packet):
            if self.id > 0:
                self._next_timestamp = self.scheduler.synchronize(packet)

                # Create and complete the packet for the ground station.
                ground_station_packet = self.make_rssi_ground_station_packet(packet)
                ground_station_packet.set("rssi", random.randint(0, 60))
                self._data.append(ground_station_packet)
            else:
                print("> Ground station received {}".format(packet.get_all()))
