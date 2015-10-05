import time
import json
import socket
from random import randint
from XBee_Sensor import XBee_Sensor

class XBee_Sensor_Simulator(XBee_Sensor):
    def __init__(self, id, arguments, scheduler, viewer):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.id = id
        self.settings = arguments.get_settings("xbee_sensor_simulator")
        self.viewer = viewer
        self.scheduler = scheduler
        self.next_timestamp = self.scheduler.get_next_timestamp()
        self.rssi_values = [None for _ in range(self.settings.get("number_of_sensors"))]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self.socket.setblocking(0)

    def __del__(self):
        self.socket.close()

    def activate(self):
        # Activate the sensor to send and receive packets.
        # The ground sensor (with ID 0) can only receive packets.
        if self.id > 0 and time.time() >= self.next_timestamp:
            self._send()
            self.next_timestamp = self.scheduler.get_next_timestamp()

        self._receive()

    def _send(self):
        # Send packets to all other sensors.
        self.viewer.clear_arrows()
        for i in range(1, self.settings.get("number_of_sensors") + 1):
            if i == self.id:
                continue

            packet = {
                "from": self.id,
                "to": i,
                "timestamp": time.time(),
                "rssi": -randint(1,60)
            }
            self.socket.sendto(json.dumps(packet), (self.settings.get("ip"), self.settings.get("port") + i))
            self.viewer.draw_arrow(self.id, i)
        
        # Send the RSSI values to the ground sensor and clear them for the next round
        packet = {
            "from": self.id,
            "to": 0,
            "rssi_values": self.rssi_values
        }
        self.socket.sendto(json.dumps(packet), (self.settings.get("ip"), self.settings.get("port")))
        self.viewer.draw_arrow(self.id, 0, "blue")
        self.rssi_values = [None for _ in range(self.settings.get("number_of_sensors"))]

        self.viewer.refresh()

    def _receive(self):
        # Receive packets from all other sensors.
        try:
            packet = json.loads(self.socket.recv(self.settings.get("buffer_size")))
            if self.id > 0:
                self.rssi_values[packet["from"] - 1] = packet["rssi"]
                self.next_timestamp = self.scheduler.synchronize(packet)
            else:
                print("> Ground station received {}".format(packet["rssi_values"]))
        except socket.error:
            pass
