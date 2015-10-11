import time
import json
import socket
import random
from XBee_Sensor import XBee_Sensor
from ..settings import Arguments, Settings

class XBee_Sensor_Simulator(XBee_Sensor):
    def __init__(self, sensor_id, settings, scheduler, viewer):
        """
        Initialize the sensor with a unique, non-blocking UDP socket.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_sensor_simulator")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self.id = sensor_id
        self.viewer = viewer
        self.scheduler = scheduler
        self.next_timestamp = self.scheduler.get_next_timestamp()
        self.data = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self.socket.setblocking(0)

    def activate(self):
        """
        Activate the sensor to send and receive packets.
        The ground sensor (with ID 0) can only receive packets.
        """

        if self.id > 0 and time.time() >= self.next_timestamp:
            self._send()
            self.next_timestamp = self.scheduler.get_next_timestamp()

        try:
            packet = json.loads(self.socket.recv(self.settings.get("buffer_size")))
            self._receive(packet)
        except socket.error:
            pass

    def deactivate(self):
        """
        Deactivate the sensor by closing the socket.
        """

        self.socket.close()

    def _send(self):
        """
        Send packets to all other sensors in the network.
        """

        self.viewer.clear_arrows()
        for i in range(1, self.settings.get("number_of_sensors") + 1):
            if i == self.id:
                continue

            packet = {
                "from": self._get_location(),
                "from_id": self.id,
                "timestamp": time.time()
            }
            self.socket.sendto(json.dumps(packet), (self.settings.get("ip"), self.settings.get("port") + i))
            self.viewer.draw_arrow(self.id, i)
        
        # Send the sweep data to the ground sensor and clear the list for the next round.
        for packet in self.data:
            self.socket.sendto(json.dumps(packet), (self.settings.get("ip"), self.settings.get("port")))
            self.viewer.draw_arrow(self.id, 0, "blue")

        self.viewer.refresh()

        self.data = []

    def _receive(self, packet):
        """
        Receive and process packets from all other sensors in the network.
        """

        if self.id > 0:
            self.next_timestamp = self.scheduler.synchronize(packet)

            # Sanitize and complete the packet for the ground station.
            packet["to"] = self._get_location()
            packet["rssi"] = random.randint(0, 60)
            packet.pop("from_id")
            packet.pop("timestamp")
            self.data.append(packet)
        else:
            print("> Ground station received {}".format(packet))

    def _get_location(self):
        """
        Get the current GPS location (latitude and longitude pair) of the sensor.
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))
