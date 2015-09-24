import sys
import time
import json
import socket
import matplotlib.pyplot as plt
import numpy as np
from random import randint
from settings.Settings import Settings
from math import *

class Viewer:
    def __init__(self, settings):
        # Initialize the viewer with a correctly scaled plot.
        self.points = []
        self.arrows = []
        self.settings = settings

        plt.xlim(0, self.settings.get("size"))
        plt.ylim(0, self.settings.get("size"))
        plt.gca().set_aspect("equal", adjustable="box")
        plt.ion()
        plt.show()

    def draw_points(self):
        # Draw a static point for each sensor in a circular shape. The
        # spacing between the points is equal. We add an offset to display
        # the circle in the middle of the plot.
        offset = self.settings.get("size") / 2
        for angle in np.arange(0, 2 * pi, (2 * pi) / self.settings.get("number_of_sensors")):
            x = offset + (cos(angle) * self.settings.get("circle_radius"))
            y = offset + (sin(angle) * self.settings.get("circle_radius"))
            self.points.append((x, y))
            plt.plot(x, y, linestyle="None", marker="o", color="black", markersize=10)

    def draw_arrow(self, point_from, point_to):
        # Draw an arrow from a given point to another given point.
        options = {
            "arrowstyle": "<-, head_width=1, head_length=1",
            "color": "red",
            "linewidth": 2
        }
        arrow = plt.annotate("", self.points[point_from - 1], self.points[point_to - 1], arrowprops=options)
        self.arrows.append(arrow)

    def refresh(self):
        plt.draw()

    def clear_arrows(self):
        # Remove all arrows from the plot.
        for arrow in self.arrows:
            arrow.remove()

        self.arrows = []

class TDMA_Scheduler(object):
    def __init__(self, settings, id):
        self.settings = settings
        self.id = id
        self.timestamp = 0

    def get_next_timestamp(self):
        # Get the next timestamp for starting transmission of packets.
        if self.timestamp == 0:
            self.timestamp = time.time() + ((self.id / self.settings.get("number_of_sensors")) *
                             self.settings.get("sweep_delay"))
        else: 
            self.timestamp += self.settings.get("sweep_delay")
        
        return self.timestamp

    def synchronize(self, packet):
        # Synchronize the scheduler after receiving a packet from
        # another sensor in the network. The transmission timestamp of this
        # sensor is the received transmission timestamp plus the number of
        # slots inbetween that sensor and this sensor.
        slot_time = self.settings.get("sweep_delay") / self.settings.get("number_of_sensors")
        from_sensor = int(packet["from"])
        timestamp = float(packet["timestamp"])
        if from_sensor < self.id:
            self.timestamp = timestamp + ((self.id - from_sensor) * slot_time)
        else:
            # Calculate how much time remains to complete the current round.
            completed_round = (self.settings.get("number_of_sensors") - from_sensor + 1) * slot_time
            self.timestamp = timestamp + completed_round + ((self.id - 1) * slot_time)

        return self.timestamp

class XBee_Sensor(object):
    def __init__(self, id, settings, viewer):
        # Initialize the sensor with its ID and a unique, non-blocking UDP socket.
        self.id = id
        self.settings = settings
        self.viewer = viewer
        self.next_timestamp = 0
        self.scheduler = TDMA_Scheduler(self.settings, self.id)
        self.next_timestamp = self.scheduler.get_next_timestamp()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.settings.get("ip"), self.settings.get("port") + self.id))
        self.socket.setblocking(0)

    def activate(self):
        # Activate the sensor to send and receive packets.
        if time.time() >= self.next_timestamp:
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
            print("-> {} sending at {}...".format(self.id, packet["timestamp"]))
        
        self.viewer.refresh()

    def _receive(self):
        # Receive packets from all other sensors.
        try:
            packet = json.loads(self.socket.recv(self.settings.get("buffer_size")))
            self.next_timestamp = self.scheduler.synchronize(packet)
            print("{} receiving at {}...".format(self.id, time.time()))
        except socket.error:
            pass

def main(argv):
    settings = Settings("settings.json", "xbee_sensor_simulator")

    viewer = Viewer(settings)
    viewer.draw_points()

    sensors = []
    for sensor_id in range(1, settings.get("number_of_sensors") + 1):
        sensor = XBee_Sensor(sensor_id, settings, viewer)
        sensors.append(sensor)

    while True:
        for sensor in sensors:
            sensor.activate()
        
        time.sleep(settings.get("loop_delay"))

if __name__ == "__main__":
    main(sys.argv[1:])
