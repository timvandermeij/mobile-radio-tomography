import unittest
import pty
import os
import serial
from mock import patch
from ..settings import Arguments
from ..zigbee.XBee_Configurator import XBee_Configurator
from xbee import ZigBee

class TestXBeeConfigurator(unittest.TestCase):
    def setUp(self):
        # Create a virtual serial port.
        master, slave = pty.openpty()
        self.port = os.ttyname(slave)

        self.arguments = Arguments("settings.json", ["--port={}".format(self.port)])
        self.settings = self.arguments.get_settings("xbee_configurator")
        self.configurator = XBee_Configurator(self.arguments)

    def test_initialization(self):
        self.assertIsInstance(self.configurator._serial_connection, serial.Serial)
        self.assertEqual(self.configurator._serial_connection.port, self.port)
        self.assertEqual(self.configurator._serial_connection.baudrate,
                         self.settings.get("baud_rate"))
        self.assertIsInstance(self.configurator._sensor, ZigBee)

    def test_encode_value(self):
        # Integers should be encoded as hexadecimal.
        integer = 1234
        calculated = self.configurator._encode_value(integer)
        self.assertEqual(calculated, "\x124")

        # Strings should not be altered.
        string = "2"
        calculated = self.configurator._encode_value(string)
        self.assertEqual(calculated, string)

        # Other types are not accepted.
        boolean = False
        with self.assertRaises(TypeError):
            self.configurator._encode_value(boolean)

    def test_decode_value(self):
        # Escape characters should be decoded.
        value = "\x01"
        calculated = self.configurator._decode_value(value)
        self.assertEqual(calculated, 1)

        # Other characters should remain the same.
        value = "2"
        calculated = self.configurator._decode_value(value)
        self.assertEqual(calculated, int(value))

    @patch("xbee.ZigBee.wait_read_frame")
    def test_get(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be None. The case of a response that is not None is
        # covered by the decode value unit test above.
        response = self.configurator.get("ID")
        self.assertTrue(response == None)

    @patch("xbee.ZigBee.wait_read_frame")
    def test_get(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be False. The most important functionality, namely the
        # parameter preparation, is already tested in the encode value
        # unit test above.
        response = self.configurator.set("ID", 1234)
        self.assertFalse(response)

    @patch("xbee.ZigBee.wait_read_frame")
    def test_get(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be False.
        response = self.configurator.write()
        self.assertFalse(response)
