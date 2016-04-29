import unittest
from ..reconstruction.Buffer import Buffer
from ..zigbee.XBee_Packet import XBee_Packet

class TestReconstructionBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer = Buffer({})

        # Create a list of unique XBee packets.
        self.xbee_packets = []
        self.xbee_packets_count = 3

        for index in range(self.xbee_packets_count):
            xbee_packet = XBee_Packet()
            xbee_packet.set("specification", "rssi_ground_station")
            xbee_packet.set("sensor_id", 1)
            xbee_packet.set("from_latitude", 12.3456789)
            xbee_packet.set("from_longitude", 21.3456789)
            xbee_packet.set("from_valid", True)
            xbee_packet.set("to_latitude", 13.4567892)
            xbee_packet.set("to_longitude", 14.4567892)
            xbee_packet.set("to_valid", True)
            xbee_packet.set("rssi", index)

            self.xbee_packets.append(xbee_packet)

    def test_initialization(self):
        # If no options have been provided, an error should be raised.
        # Note that the `setUp` method already covers the case where
        # options have been provided.
        with self.assertRaises(ValueError):
            Buffer()

    def test_get(self):
        # If the buffer is empty, we should get None.
        self.assertEqual(self.buffer.get(), None)

        # If the buffer is not empty, we should get the first item.
        for xbee_packet in self.xbee_packets:
            self.buffer.put(xbee_packet)

        for index in range(self.xbee_packets_count):
            self.assertEqual(self.buffer.get(), self.xbee_packets[index])

        self.assertEqual(self.buffer.get(), None)

    def test_put(self):
        # Invalid XBee packets should not be inserted.
        with self.assertRaises(ValueError):
            self.buffer.put("foo")

        # Valid XBee packets should be inserted.
        self.buffer.put(self.xbee_packets[0])
        self.assertEqual(self.buffer.get(), self.xbee_packets[0])

    def test_count(self):
        self.assertEqual(self.buffer.count(), 0)

        for xbee_packet in self.xbee_packets:
            self.buffer.put(xbee_packet)

        self.assertEqual(self.buffer.count(), self.xbee_packets_count)

    def test_number_of_sensors(self):
        self.assertEqual(self.buffer.number_of_sensors, 0)

    def test_origin(self):
        self.assertEqual(self.buffer.origin, (0, 0))

    def test_size(self):
        self.assertEqual(self.buffer.size, (0, 0))
