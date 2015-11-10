import struct
import unittest
from ..zigbee.XBee_Packet import XBee_Packet

class TestXBeePacket(unittest.TestCase):
    def setUp(self):
        self.packet = XBee_Packet()

    def test_initialization(self):
        # The packet must be empty.
        self.assertEqual(self.packet._contents, {})

        # The specifications dictionary must be set.
        self.assertIsInstance(self.packet._specifications, dict)

        # The packet must be private by default.
        self.assertTrue(self.packet._private)

    def test_set(self):
        # A given key and value should be present in the contents.
        self.packet.set("foo", "bar")
        self.assertEqual(self.packet._contents["foo"], "bar")

        # When an invalid specification is set, the private property
        # must not be updated.
        private = self.packet._private
        self.packet.set("specification", "foo")
        self.assertEqual(private, self.packet._private)

        # When a valid specification is set, the private property
        # must be updated.
        self.packet.set("specification", "memory_map_chunk")
        self.assertFalse(self.packet._private)

    def test_unset(self):
        # A given key should not be present in the contents.
        self.packet._contents["foo"] = "bar"
        self.packet.unset("foo")
        self.assertNotIn("foo", self.packet._contents)

        # Verify that unsetting a nonexistent key does not throw
        # a KeyError, but instead does nothing.
        self.packet.unset("foo")

    def test_get(self):
        # The value of a present key should be fetched.
        self.packet._contents["foo"] = "bar"
        self.assertEqual(self.packet.get("foo"), "bar")

        # "None" should be returned for a nonexistent key.
        self.assertEqual(self.packet.get("quux"), None)

    def test_get_all(self):
        # All contents should be fetched.
        self.packet._contents["foo"] = "bar"
        self.packet._contents["baz"] = "quux"
        self.assertEqual(self.packet.get_all(), {
            "foo": "bar",
            "baz": "quux"
        })

    def test_serialize(self):
        # A specification must be provided.
        with self.assertRaises(KeyError):
            self.packet.serialize()

        # A provided specification must exist.
        self.packet.set("specification", "foo")
        with self.assertRaises(KeyError):
            self.packet.serialize()

        # All fields from the specification must be provided.
        self.packet.set("specification", "memory_map_chunk")
        with self.assertRaises(KeyError):
            self.packet.serialize()

        # When all fields are provided, the specification field must be
        # unset and the packed message must be valid.
        self.packet.set("specification", "memory_map_chunk")
        self.packet.set("latitude", 123456789.12)
        self.packet.set("longitude", 123496785.34)
        packed_message = self.packet.serialize()
        self.assertEqual(packed_message, "\x01H\xe1zT4o\x9dA\xf6(\\E\xa5q\x9dA")

    def test_unserialize(self):
        # Empty strings must be refused.
        with self.assertRaises(struct.error):
            self.packet.unserialize("")

        # Invalid specifications must be refused.
        with self.assertRaises(KeyError):
            self.packet.unserialize("\xFF\x01")

        # Valid messages must be unpacked.
        self.packet.unserialize("\x01H\xe1zT4o\x9dA\xf6(\\E\xa5q\x9dA")
        self.assertEqual(self.packet._contents, {
            "specification": "memory_map_chunk",
            "latitude": 123456789.12,
            "longitude": 123496785.34
        })
        self.assertFalse(self.packet._private)

    def test_is_private(self):
        # The private property should be returned.
        private = self.packet.is_private()
        self.assertEqual(self.packet._private, private)
