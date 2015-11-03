import unittest
import socket
import time
import random
import copy
import Queue
from ..settings import Arguments
from ..zigbee.XBee_Packet import XBee_Packet
from ..zigbee.XBee_TDMA_Scheduler import XBee_TDMA_Scheduler
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class TestXBeeSensorSimulator(unittest.TestCase):
    def location_callback(self):
        """
        Get the current GPS location (latitude and longitude pair).
        """

        return (random.uniform(1.0, 50.0), random.uniform(1.0, 50.0))

    def receive_callback(self, packet):
        pass

    def setUp(self):
        # We need to mock the Matplotlib module as we do not want to use
        # plotting facilities during the tests.
        self.matplotlib_mock = MagicMock()
        modules = {
            'matplotlib': self.matplotlib_mock,
            'matplotlib.pyplot': self.matplotlib_mock.pyplot
        }

        self.patcher = patch.dict('sys.modules', modules)
        self.patcher.start()
        from ..zigbee.XBee_Viewer import XBee_Viewer

        self.id = 1
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("xbee_sensor_simulator")
        self.scheduler = XBee_TDMA_Scheduler(self.id, self.arguments)
        self.viewer = XBee_Viewer(self.arguments)
        self.sensor = XBee_Sensor_Simulator(self.id, self.arguments,
                                            self.scheduler, self.viewer,
                                            self.location_callback,
                                            self.receive_callback)

        self.viewer.draw_points()

    def test_initialization(self):
        # The ID of the sensor must be set.
        self.assertEqual(self.sensor.id, self.id)

        # The next timestamp must be set.
        self.assertNotEqual(self.sensor._next_timestamp, 0)

        # Both the location and the receive callback must be set.
        self.assertTrue(hasattr(self.sensor._location_callback, "__call__"))
        self.assertTrue(hasattr(self.sensor._receive_callback, "__call__"))

        # The sweep data list must be empty.
        self.assertEqual(self.sensor._data, [])

        # The custom packet queue must be empty.
        self.assertTrue(isinstance(self.sensor._queue, Queue.Queue))
        self.assertEqual(self.sensor._queue.qsize(), 0)

    def test_enqueue(self):
        # Packets that are not XBee_Packet objects should be refused.
        with self.assertRaises(TypeError):
            packet = {
                "foo": "bar"
            }
            self.sensor.enqueue(packet)

        # Packets that do not contain a destination should be broadcasted.
        # We subtract one because we do not send to ourself.
        packet = XBee_Packet()
        packet.set("foo", "bar")
        self.sensor.enqueue(packet)
        self.assertEqual(self.sensor._queue.qsize(),
                         self.settings.get("number_of_sensors") - 1)
        self.sensor._queue = Queue.Queue()

        # Valid packets should be enqueued.
        packet = XBee_Packet()
        packet.set("to_id", 2)
        packet.set("foo", "bar")
        self.sensor.enqueue(packet)
        self.assertEqual(packet, self.sensor._queue.get())
        self.assertEqual(packet.get("_type"), "custom")

    def test_send(self):
        # After sending, the sweep data list must be empty.
        self.sensor._send()
        self.assertEqual(self.sensor._data, [])

        # If the queue contains packets, some of them must be sent.
        packet = XBee_Packet()
        packet.set("to_id", 2)
        packet.set("foo", "bar")
        self.sensor.enqueue(packet)
        queue_length_before = self.sensor._queue.qsize()
        self.sensor._send()
        custom_packet_limit = self.sensor.settings.get("custom_packet_limit")
        queue_length_after = max(0, queue_length_before - custom_packet_limit)
        self.assertEqual(self.sensor._queue.qsize(), queue_length_after)

    def test_receive(self):
        # Create a packet from sensor 2 to the current sensor.
        packet = XBee_Packet()
        packet.set("_from_id", 2)
        packet.set("_timestamp", time.time())
        
        # After receiving that packet, the next timestamp must be synchronized.
        # Note that we must make a copy as the receive method will change the packet!
        copied_packet = copy.deepcopy(packet)
        self.sensor._receive(packet)
        self.assertEqual(self.sensor._next_timestamp,
                         self.scheduler.synchronize(copied_packet))

    def test_deactivate(self):
        # After deactivation the socket should be closed.
        self.sensor.deactivate()
        with self.assertRaises(socket.error):
            self.sensor._socket.sendto("foo", ("127.0.0.1", 100))
