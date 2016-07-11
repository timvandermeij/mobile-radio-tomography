import serial
from mock import MagicMock
from ..core.USB_Manager import USB_Device_Baud_Rate
from ..zigbee.XBee_Configurator import XBee_Configurator, XBee_Response_Status
from ..settings import Arguments
from core_usb_manager import USBManagerTestCase
from settings import SettingsTestCase

class TestZigBeeXBeeConfigurator(USBManagerTestCase, SettingsTestCase):
    def setUp(self):
        super(TestZigBeeXBeeConfigurator, self).setUp()

        self.arguments = Arguments("settings.json", [
            "--port", self._xbee_port, "--startup-delay", "0"
        ])
        self.settings = self.arguments.get_settings("xbee_configurator")

        self.usb_manager.index()
        self.configurator = XBee_Configurator(self.arguments, self.usb_manager)

        # Mock the sensor as we cannot test with the actual hardware.
        self.configurator._sensor = MagicMock()

    def test_initialization(self):
        # Verify that only `Arguments` objects can be used to initialize.
        XBee_Configurator(self.arguments, self.usb_manager)
        with self.assertRaises(TypeError):
            XBee_Configurator(self.settings, self.usb_manager)
        with self.assertRaises(TypeError):
            XBee_Configurator(None, self.usb_manager)

        self.assertIsInstance(self.configurator._serial_connection, serial.Serial)
        self.assertEqual(self.configurator._serial_connection.port, self._xbee_port)
        self.assertEqual(self.configurator._serial_connection.baudrate,
                         USB_Device_Baud_Rate.XBEE)

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

    def test_get(self):
        # Verify that unsuccessful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {}
        response = self.configurator.get("ID")
        self.configurator._sensor.send.assert_called_once_with("at", command="ID")
        self.assertIsNone(response)
        self.configurator._sensor.send.reset_mock()

        # Verify that successful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {
            "status": XBee_Response_Status.OK,
            "parameter": "\x02"
        }
        response = self.configurator.get("ID")
        self.configurator._sensor.send.assert_called_once_with("at", command="ID")
        self.assertEqual(response, 2)

    def test_set(self):
        # Verify that unsuccessful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {}
        response = self.configurator.set("ID", 2)
        self.configurator._sensor.send.assert_called_once_with("at", command="ID", parameter="\x02")
        self.assertFalse(response)
        self.configurator._sensor.send.reset_mock()

        # Verify that successful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {
            "status": XBee_Response_Status.OK
        }
        response = self.configurator.set("ID", 2)
        self.configurator._sensor.send.assert_called_once_with("at", command="ID", parameter="\x02")
        self.assertTrue(response)

    def test_write(self):
        # Verify that unsuccessful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {}
        response = self.configurator.write()
        self.configurator._sensor.send.assert_called_once_with("at", command="WR")
        self.assertFalse(response)
        self.configurator._sensor.send.reset_mock()

        # Verify that successful requests are handled.
        self.configurator._sensor.wait_read_frame.return_value = {
            "status": XBee_Response_Status.OK
        }
        response = self.configurator.write()
        self.configurator._sensor.send.assert_called_once_with("at", command="WR")
        self.assertTrue(response)
