import unittest
import socket
import time
from mock import patch
from ..settings import Arguments
from ..zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..zigbee.XBee_Viewer import XBee_Viewer
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class TestXBeeSensorSimulator(unittest.TestCase):
    @patch("matplotlib.pyplot.show")
    def setUp(self, mock_show):
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

        # The sweep data list must be empty.
        self.assertEqual(self.sensor.data, [])

    def test_send(self):
        # After sending, the RSSI values list must be reset.
        self.sensor._send()
        self.assertEqual(self.sensor.data, [])

    def test_receive(self):
        # Create a packet from sensor 2 to the current sensor.
        packet = {
            "from_id": 2,
            "timestamp": time.time()
        }
        
        # After receiving that packet, the next timestamp must be synchronized.
        # Note that we must make a copy as the receive method will change the packet!
        copy = packet.copy()
        self.sensor._receive(packet)
        self.assertEqual(self.sensor.next_timestamp, self.scheduler.synchronize(copy))

    def test_deactivate(self):
        # After deactivation the socket should be closed.
        self.sensor.deactivate()
        with self.assertRaises(socket.error):
            self.sensor.socket.sendto("foo", ("127.0.0.1", 100))
