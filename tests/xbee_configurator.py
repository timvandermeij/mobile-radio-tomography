import serial
from mock import patch
from xbee import ZigBee
from ..core.USB_Manager import USB_Device_Baud_Rate
from ..zigbee.XBee_Configurator import XBee_Configurator
from ..settings import Arguments
from core_usb_manager import USBManagerTestCase
from settings import SettingsTestCase

class TestXBeeConfigurator(USBManagerTestCase, SettingsTestCase):
    def setUp(self):
        super(TestXBeeConfigurator, self).setUp()

        self.arguments = Arguments("settings.json", ["--port", self._xbee_port])
        self.settings = self.arguments.get_settings("xbee_configurator")

        self.usb_manager.index()
        self.configurator = XBee_Configurator(self.settings, self.usb_manager)

    def test_initialization(self):
        # Verify that only `Settings` and `Arguments` objects can be used to initialize.
        XBee_Configurator(self.arguments, self.usb_manager)
        XBee_Configurator(self.settings, self.usb_manager)
        with self.assertRaises(ValueError):
            XBee_Configurator(None, self.usb_manager)

        self.assertIsInstance(self.configurator._serial_connection, serial.Serial)
        self.assertEqual(self.configurator._serial_connection.port, self._xbee_port)
        self.assertEqual(self.configurator._serial_connection.baudrate,
                         USB_Device_Baud_Rate.XBEE)
        self.assertIsInstance(self.configurator._sensor, ZigBee)

    def test_encode_value(self):
        # Integers should be encoded as hexadecimal.
        calculated_integer = self.configurator._encode_value(1234)
        self.assertEqual(calculated_integer, "\x124")

        # Strings should not be altered.
        calculated_string = self.configurator._encode_value("2")
        self.assertEqual(calculated_string, "2")

        # Other types are not accepted.
        with self.assertRaises(TypeError):
            self.configurator._encode_value([])

    def test_decode_value(self):
        # Escape characters should be decoded.
        calculated = self.configurator._decode_value("\x01")
        self.assertEqual(calculated, 1)

        # Other characters should remain the same.
        calculated = self.configurator._decode_value("2")
        self.assertEqual(calculated, 2)

    @patch("xbee.ZigBee.wait_read_frame")
    def test_get(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be None. The case of a response that is not None is
        # covered by the decode value unit test above.
        response = self.configurator.get("ID")
        self.assertIsNone(response)

    @patch("xbee.ZigBee.wait_read_frame")
    def test_set(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be False. The most important functionality, namely the
        # parameter preparation, is already tested in the encode value
        # unit test above.
        response = self.configurator.set("ID", 1234)
        self.assertFalse(response)

    @patch("xbee.ZigBee.wait_read_frame")
    def test_write(self, mock_wait_read_frame):
        # We cannot test with an actual sensor, so the response should
        # always be False.
        response = self.configurator.write()
        self.assertFalse(response)
