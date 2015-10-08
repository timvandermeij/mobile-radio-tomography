import unittest
import json
import time
import socket
from random import randint
from ..settings import Arguments
from ..zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..zigbee.XBee_Viewer import XBee_Viewer
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class TestXBeeSensorSimulator(unittest.TestCase):
    def setUp(self):
        self.id = 1
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("xbee_sensor_simulator")
        self.scheduler = XBee_TDMA_Scheduler(self.id, self.arguments)
        self.viewer = XBee_Viewer(self.arguments)
        self.sensor = XBee_Sensor_Simulator(self.id, self.arguments,
                                            self.scheduler, self.viewer)

        self.viewer.draw_points()

    def test_initialization(self):
        # The ID of the sensor must be set.
        self.assertEqual(self.sensor.id, self.id)

        # The next timestamp must be set.
        self.assertNotEqual(self.sensor.next_timestamp, 0)

        # The RSSI values list must contain only None entries.
        self.assertEqual(self.sensor.rssi_values,
                         [None for _ in range(self.settings.get("number_of_sensors"))])

    def test_send(self):
        # After sending, the RSSI values list must be reset.
        self.sensor._send()
        self.assertEqual(self.sensor.rssi_values,
                         [None for _ in range(self.settings.get("number_of_sensors"))])

    def test_receive(self):
        # Create a packet from sensor 2 to the current sensor.
        packet = {
            "from": 2,
            "to": self.id,
            "timestamp": time.time(),
            "rssi": randint(1,60)
        }
        
        # After receiving that packet, the next timestamp must be synchronized.
        self.sensor._receive(packet)
        self.assertEqual(self.sensor.next_timestamp, self.scheduler.synchronize(packet))
