import json
import unittest
from ..zigbee.XBee_Packet import XBee_Packet

class TestXBeePacket(unittest.TestCase):
    def setUp(self):
        self.packet = XBee_Packet()

    def test_initialization(self):
        # The packet must be empty.
        self.assertEqual(self.packet._contents, {})

    def test_set(self):
        # A given key and value should be present in the contents.
        self.packet.set("foo", "bar")
        self.assertEqual(self.packet._contents["foo"], "bar")

    def test_unset(self):
        # A given key should not be present in the contents.
        self.packet._contents["foo"] = "bar"
        self.packet.unset("foo")
        self.assertFalse("foo" in self.packet._contents)

        # Verify that unsetting a nonexistent key does not throw
        # a KeyError, but instead does nothing.
        self.packet.unset("foo")

    def test_get(self):
        # The value of a present key should be fetched.
        self.packet._contents["foo"] = "bar"
        self.assertEqual(self.packet.get("foo"), "bar")

        # "None" should be returned for a nonexistent key.
        self.assertEqual(self.packet.get("quux"), None)

    def test_serialize(self):
        # A JSON string of the contents dictionary should be returned.
        self.packet._contents["foo"] = "bar"
        serialized = self.packet.serialize()
        dictionary = {
            "foo": "bar"
        }
        self.assertEqual(serialized, json.dumps(dictionary))

    def test_unserialize(self):
        # The contents dictionary should be filled with the keys
        # and values from the JSON string.
        dictionary = {
            "foo": "bar"
        }
        self.packet.unserialize(json.dumps(dictionary))
        self.assertEqual(self.packet._contents, dictionary)
