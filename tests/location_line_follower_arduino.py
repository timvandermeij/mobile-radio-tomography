import serial
from mock import patch, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..location.Line_Follower import Line_Follower_Direction
from ..location.Line_Follower_Arduino import Line_Follower_Arduino
from ..settings import Arguments
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from settings import SettingsTestCase

class TestLocationLineFollowerArduino(ThreadableTestCase, SettingsTestCase,
                                      USBManagerTestCase):
    def setUp(self):
        super(TestLocationLineFollowerArduino, self).setUp()

        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP

        self.arguments = Arguments("settings.json", [
            "--readable-leds", "0", "2", "3", "5", "--line-threshold", "300"
        ])
        self.settings = self.arguments.get_settings("line_follower_arduino")

        self.mock_callback = MagicMock()
        self.thread_manager = Thread_Manager()
        self.usb_manager.index()
        self.line_follower = Line_Follower_Arduino(
            self.location, self.direction, self.mock_callback, self.settings,
            self.thread_manager, usb_manager=self.usb_manager, delay=0
        )

    def test_initialization(self):
        # The settings argument must be `Arguments` or `Settings`
        with self.assertRaises(TypeError):
            Line_Follower_Arduino(
                self.location, self.direction, self.mock_callback,
                None, self.thread_manager, usb_manager=self.usb_manager, delay=0
            )

        # A `USB_Manager` must be provided.
        with self.assertRaisesRegexp(TypeError, "'usb_manager' must be provided"):
            Line_Follower_Arduino(
                self.location, self.direction, self.mock_callback,
                self.settings, self.thread_manager, usb_manager=None, delay=0
            )

        # `Arguments` is accepted (like `Settings` in `setUp`).
        Line_Follower_Arduino(
            self.location, self.direction, self.mock_callback, self.arguments,
            self.thread_manager, usb_manager=self.usb_manager, delay=0
        )

    def test_interface(self):
        # Verify that the serial connection is set
        self.assertIsInstance(self.line_follower._serial_connection,
                              serial.Serial)
        self.assertEqual(self.line_follower._serial_connection,
                         self.line_follower.get_serial_connection())

        # Enable and disable do not influence anything.
        self.line_follower.enable()
        self.line_follower.disable()

    def mock_read(self):
        """
        Wrapper function for `Serial.readline` that is used by `test_read`
        to return a read line and deactivate the line follower.
        """

        self.line_follower.deactivate()
        return "0.1 0.2 0.3 0.4 0.5 0.6"

    def test_read(self):
        for exception in (serial.SerialException, TypeError):
            with patch.object(serial.Serial, 'readline', side_effect=exception) as readline_mock:
                # Exceptions are handled when the line follower is running.
                self.line_follower._running = True
                with self.assertRaises(exception):
                    self.line_follower.read()

                readline_mock.assert_called_once_with()

                # Exceptions are ignored and the method immediately ends when 
                # the line follower is not running.
                readline_mock.reset_mock()
                self.line_follower._running = False
                self.assertIsNone(self.line_follower.read())
                readline_mock.assert_called_once_with()

        # Invalid values are silently ignored.
        self.line_follower._running = False
        with patch.object(serial.Serial, 'readline', return_value=None):
            self.assertIsNone(self.line_follower.read())
        with patch.object(serial.Serial, 'readline', return_value="0.1 uhm"):
            self.assertIsNone(self.line_follower.read())

        # If the vehicle is deactivated while reading a value, then the method 
        # also stops early.
        self.line_follower._running = True
        with patch.object(serial.Serial, 'readline', wraps=self.mock_read):
            self.assertIsNone(self.line_follower.read())

        self.line_follower._running = True
        with patch.object(serial.Serial, 'readline',
                          return_value="100.99 42 400.1 300 777.5 999.87"):
            sensor_values = self.line_follower.read()
            self.assertEqual(sensor_values, [0, 1, 0, 1])
