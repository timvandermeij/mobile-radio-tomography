import struct
import unittest
from ..zigbee.XBee_Custom_Packet import XBee_Custom_Packet

class TestXBeeCustomPacket(unittest.TestCase):
    def setUp(self):
        self.custom_packet = XBee_Custom_Packet()

    def test_initialization(self):
        # The packet must be empty.
        self.assertEqual(self.custom_packet._contents, {})

        # The specifications dictionary must be set.
        self.assertIsInstance(self.custom_packet._specifications, dict)

    def test_serialize(self):
        # A specification must be provided.
        with self.assertRaises(KeyError):
            self.custom_packet.serialize()

        # A provided specification must exist.
        self.custom_packet.set("specification", "foo")
        with self.assertRaises(KeyError):
            self.custom_packet.serialize()

        # All fields from the specification must be provided.
        self.custom_packet.set("specification", "memory_map_chunk")
        with self.assertRaises(KeyError):
            self.custom_packet.serialize()

        # When all fields are provided, the specification field must be
        # unset and the packed message must be valid.
        self.custom_packet.set("specification", "memory_map_chunk")
        self.custom_packet.set("latitude", 123456789.12)
        self.custom_packet.set("longitude", 123496785.34)
        packed_message = self.custom_packet.serialize()
        self.assertEqual(self.custom_packet.get("specification"), None)
        self.assertEqual(packed_message, "\x01H\xe1zT4o\x9dA\xf6(\\E\xa5q\x9dA")

    def test_unserialize(self):
        # Empty strings must be refused.
        with self.assertRaises(struct.error):
            self.custom_packet.unserialize("")

        # Invalid specifications must be refused.
        with self.assertRaises(KeyError):
            self.custom_packet.unserialize("\xFF\x01")

        # Valid messages must be unpacked.
        self.custom_packet.unserialize("\x01H\xe1zT4o\x9dA\xf6(\\E\xa5q\x9dA")
        self.assertEqual(self.custom_packet._contents, {
            "specification": "memory_map_chunk",
            "latitude": 123456789.12,
            "longitude": 123496785.34
        })
