import unittest
from mock import patch, call, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..settings import Arguments

class TestControlInfraredSensor(unittest.TestCase):
    def setUp(self):
        # We need to mock the pylirc module as we do not want to use actual 
        # LIRC communication. We assume the pylirc module works as expected.
        self.pylirc_mock = MagicMock()
        modules = {
            'pylirc': self.pylirc_mock
        }

        self.patcher = patch.dict('sys.modules', modules)
        self.patcher.start()

        from ..control.Infrared_Sensor import Infrared_Sensor
        # Skip configuration checks since we emulate the behavior of LIRC. We 
        # test the configuration checks in test_initialize.
        self.old_configure = Infrared_Sensor._configure
        Infrared_Sensor._configure = MagicMock()

        thread_manager = Thread_Manager()

        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("infrared_sensor")
        self.infrared_sensor = Infrared_Sensor(self.settings, thread_manager)
        self.mock_callback = MagicMock()

    def tearDown(self):
        # Reset mock configure method so that we do not lose the original 
        # method during multiple tests.
        from ..control.Infrared_Sensor import Infrared_Sensor
        Infrared_Sensor._configure = self.old_configure

        # Stop all active patchers. Useful for when a test fails midway so that 
        # it does not affect other tests.
        patch.stopall()

    def test_initialize(self):
        # Test initialization of infrared sensor with a local variable rather 
        # than the one already created at setUp.
        thread_manager = Thread_Manager()

        # Test whether we check that we have /etc/lirc installed
        methods = {
            'isdir.return_value': False
        }
        patcher = patch('os.path', **methods)
        patcher.start()
        from ..control.Infrared_Sensor import Infrared_Sensor
        Infrared_Sensor._configure = self.old_configure
        with self.assertRaises(OSError) as cm:
            infrared_sensor = Infrared_Sensor(self.settings, thread_manager)

        self.assertIn("not installed", cm.exception.message)
        patcher.stop()

        # Test whether we check that the remote exists
        methods = {
            'isdir.return_value': True,
            'isfile.return_value': False
        }
        patcher = patch('os.path', **methods)
        patcher.start()
        with self.assertRaises(OSError) as cm:
            infrared_sensor = Infrared_Sensor(self.settings, thread_manager)

        self.assertIn("does not exist", cm.exception.message)
        patcher.stop()

    def test_register(self):
        # We must have an existing button.
        with self.assertRaises(KeyError):
            self.infrared_sensor.register("!nonexistent malformed button!", self.mock_callback)

        # We must have a (normal) callback.
        with self.assertRaises(ValueError):
            self.infrared_sensor.register("start", None)

        # We must have callable functions for all given callbacks.
        with self.assertRaises(ValueError):
            self.infrared_sensor.register("stop", self.mock_callback, "not a function")

    def test_callbacks(self):
        # Test normal event callback.
        self.infrared_sensor.register("start", self.mock_callback)

        self.infrared_sensor._handle_lirc_code(None)
        self.assertFalse(self.mock_callback.called)
        self.infrared_sensor._handle_lirc_code(['start'])
        self.assertEqual(self.mock_callback.call_count, 1)

        # Test additional release callback.
        self.mock_callback.reset_mock()
        mock_callback = MagicMock()
        mock_release_callback = MagicMock()

        self.infrared_sensor.register("stop", mock_callback, mock_release_callback)

        self.infrared_sensor._handle_lirc_code(None)
        self.assertFalse(mock_callback.called)
        self.assertFalse(mock_release_callback.called)

        self.infrared_sensor._handle_lirc_code(['stop'])
        self.assertEqual(mock_callback.call_count, 1)
        self.assertFalse(mock_release_callback.called)

        self.infrared_sensor._handle_lirc_code(None)
        self.assertEqual(mock_callback.call_count, 1)
        self.assertEqual(mock_release_callback.call_count, 1)
        # Start button was not pressed.
        self.assertFalse(self.mock_callback.called)
