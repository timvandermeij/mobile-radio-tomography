# Library imports
from mock import patch, MagicMock, PropertyMock

# Package imports
from ..core.Thread_Manager import Thread_Manager
from ..core.USB_Manager import USB_Manager
from ..settings.Arguments import Arguments
from ..zigbee.NTP import NTP
from ..zigbee.RF_Sensor_Physical import RF_Sensor_Physical
from settings import SettingsTestCase

class TestZigBeeRFSensorPhysical(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", ["--rf-sensor-id", "1"])
        self.settings = self.arguments.get_settings("rf_sensor_physical")

        self.thread_manager = Thread_Manager()
        self.usb_manager = USB_Manager()
        self.location_callback = MagicMock(return_value=((0, 0), 0))
        self.receive_callback = MagicMock()
        self.valid_callback = MagicMock(return_value=True)

        type_mock = PropertyMock(return_value="rf_sensor_physical")
        with patch.object(RF_Sensor_Physical, "type", new_callable=type_mock):
            self.rf_sensor = RF_Sensor_Physical(self.arguments, self.thread_manager,
                                                self.location_callback,
                                                self.receive_callback,
                                                self.valid_callback,
                                                usb_manager=self.usb_manager)

    def test_initialization(self):
        # Providing an incorrect USB Manager raises an exception.
        type_mock = PropertyMock(return_value="rf_sensor_physical")
        with patch.object(RF_Sensor_Physical, "type", new_callable=type_mock):
            with self.assertRaises(TypeError):
                RF_Sensor_Physical(self.arguments, self.thread_manager,
                                   self.location_callback, self.receive_callback,
                                   self.valid_callback, usb_manager=None)

        self.assertEqual(self.rf_sensor._usb_manager, self.usb_manager)

        self.assertEqual(self.rf_sensor._synchronized, False)
        self.assertEqual(self.rf_sensor._discovery_callback, None)

        self.assertIsInstance(self.rf_sensor._ntp, NTP)
        self.assertEqual(self.rf_sensor._ntp_delay, self.settings.get("ntp_delay"))

    def test_discover(self):
        # The discovery callback must be registered.
        self.rf_sensor.discover(MagicMock())

        self.assertNotEqual(self.rf_sensor._discovery_callback, None)
        self.assertTrue(hasattr(self.rf_sensor._discovery_callback, "__call__"))
