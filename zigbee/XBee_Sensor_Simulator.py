import thread
import time
import socket
import random
import copy
import Queue
from XBee_Packet import XBee_Packet
from XBee_Sensor import XBee_Sensor

class XBee_Sensor_Simulator(XBee_Sensor):
    def __init__(self, arguments, thread_manager, usb_manager,
                 location_callback, receive_callback, valid_callback):
        """
        Initialize the simulated XBee sensor.
        """

        self._type = "xbee_sensor_simulator"

        super(XBee_Sensor_Simulator, self).__init__(arguments, thread_manager, usb_manager,
                                                    location_callback, receive_callback, valid_callback)

        self._data = []
        self._queue = Queue.Queue()
        self._active = False
        self._loop_delay = self._settings.get("loop_delay")
        self._ip = self._settings.get("ip")
        self._port = self._settings.get("port")
        self._socket = None

    def get_identity(self):
        """
        Get the identity (ID, address and join status) of this sensor.
        """

        identity = {
            "id": self._id,
            "address": "{}:{}".format(self._ip, self._port),
            "joined": True
        }
        return identity

    def setup(self):
        """
        Setup a unique, non-blocking UDP socket connection.
        """

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._ip, self._port + self._id))
        self._socket.setblocking(0)

    def activate(self):
        """
        Activate the sensor to send and receive packets.
        The ground sensor (with ID 0) can only receive packets.
        """

        super(XBee_Sensor_Simulator, self).activate()

        if not self._active:
            if self._socket is None:
                self.setup()

            self._active = True
            thread.start_new_thread(self._loop, ())

    def _loop(self):
        """
        Execute the sensor loop. This runs in a separate thread.
        """

        try:
            while self._active:
                if self._id > 0 and time.time() >= self._next_timestamp:
                    self._next_timestamp = self._scheduler.get_next_timestamp()
                    self._send()

                # Check if there is data to be processed.
                try:
                    data = self._socket.recv(self._settings.get("buffer_size"))
                except socket.error:
                    time.sleep(self._loop_delay)
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

        if self._active or self._socket is not None:
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
            for to_id in xrange(1, self._settings.get("number_of_sensors") + 1):
                if to_id == self._id:
                    continue

                self._queue.put({
                    "packet": copy.deepcopy(packet),
                    "to": to_id
                })

    def discover(self, callback):
        """
        Discover other XBee devices in the network.

        This method is only used on the ground station in the control panel
        to refresh the status of the other XBee devices.
        """

        # The simulator does not use XBee device discovery because it does not
        # use the actual XBee library that provides this functionality. We
        # simulate the process by calling the callback with the packet manually.
        for vehicle in xrange(1, self._settings.get("number_of_sensors") + 1):
            packet = {
                "id": self._id + vehicle,
                "address": "{}:{}".format(self._ip, self._port + self._id + vehicle)
            }
            callback(packet)

    def _send(self):
        """
        Send packets to all other sensors in the network.
        """

        for i in xrange(1, self._settings.get("number_of_sensors") + 1):
            if i == self._id:
                continue

            packet = self.make_rssi_broadcast_packet()
            packet.set("sensor_id", self._id)
            self._socket.sendto(packet.serialize(), (self._ip, self._port + i))

        # Send custom packets to their destination. Since the time slots are
        # limited in length, so is the number of custom packets we transfer
        # in each sweep.
        self._send_custom_packets()

        # Send the sweep data to the ground sensor.
        for packet in self._data:
            self._socket.sendto(packet.serialize(), (self._ip, self._port))

        self._data = []

    def _send_custom_packets(self):
        """
        Send custom packets to their destinations.
        """

        limit = self._settings.get("custom_packet_limit")
        while not self._queue.empty():
            if limit == 0:
                break

            limit -= 1
            item = self._queue.get()
            self._socket.sendto(item["packet"].serialize(), (self._ip, self._port + item["to"]))

    def _receive(self, packet):
        """
        Receive and process packets from all other sensors in the network.
        """

        if not self.check_receive(packet):
            if self._id > 0:
                self._next_timestamp = self._scheduler.synchronize(packet)

                # Create and complete the packet for the ground station.
                ground_station_packet = self.make_rssi_ground_station_packet(packet)
                ground_station_packet.set("rssi", random.randint(0, 60))
                self._data.append(ground_station_packet)
            else:
                print("> Ground station received {}".format(packet.get_all()))
