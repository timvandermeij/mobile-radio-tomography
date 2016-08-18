# Core imports
import time

# Library imports
from mock import patch, MagicMock, PropertyMock

# Package imports
from ..core.USB_Manager import USB_Manager
from ..reconstruction.Buffer import Buffer
from ..zigbee.NTP import NTP
from ..zigbee.RF_Sensor_Physical import RF_Sensor_Physical
from zigbee_rf_sensor import ZigBeeRFSensorTestCase

class TestZigBeeRFSensorPhysical(ZigBeeRFSensorTestCase):
    def setUp(self):
        super(TestZigBeeRFSensorPhysical, self).setUp()

        self.settings = self.arguments.get_settings("rf_sensor_physical")
        self.usb_manager = USB_Manager()

        type_mock = PropertyMock(return_value="rf_sensor_physical")
        with patch.object(RF_Sensor_Physical, "type", new_callable=type_mock):
            self.rf_sensor = self._create_sensor(RF_Sensor_Physical,
                                                 usb_manager=self.usb_manager)

    def test_initialization(self):
        # Providing an incorrect USB Manager raises an exception.
        type_mock = PropertyMock(return_value="rf_sensor_physical")
        with patch.object(RF_Sensor_Physical, "type", new_callable=type_mock):
            with self.assertRaises(TypeError):
                self._create_sensor(RF_Sensor_Physical, usb_manager=None)

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

    @patch.object(NTP, "start")
    def test_synchronize(self, ntp_start_mock):
        # Enable synchronization mode and mock the NTP component.
        self.settings.set("synchronize", True)

        # Let `time.sleep` raise an exception to exit the loop.
        with patch.object(time, "sleep", side_effect=RuntimeError) as sleep_mock:
            with self.assertRaises(RuntimeError):
                self.rf_sensor._synchronize()

            # The NTP component must be called to start synchronization.
            ntp_start_mock.assert_called_once_with()

            # The NTP delay must be applied.
            sleep_mock.assert_any_call(self.settings.get("ntp_delay"))

    def test_process(self):
        # Private packets must be passed along to the receive callback.
        with patch.object(self.rf_sensor, "_receive_callback") as receive_callback_mock:
            self.packet.set("specification", "waypoint_clear")

            self.rf_sensor._process(self.packet)
            receive_callback_mock.assert_called_once_with(self.packet)

        with patch.object(NTP, "process") as ntp_process_mock:
            # NTP synchronization packets must be handled.
            self.packet.set("specification", "ntp")

            self.rf_sensor._process(self.packet)
            ntp_process_mock.assert_called_once_with(self.packet)

        # RSSI ground station packets must be handled on the ground station.
        buffer_mock = MagicMock(spec=Buffer)
        self.rf_sensor._id = 0
        self.rf_sensor.buffer = buffer_mock

        self.packet.set("specification", "rssi_ground_station")

        self.rf_sensor._process(self.packet)
        buffer_mock.put.assert_called_once_with(self.packet)

        # RSSI broadcast packets must raise an exception on the ground station.
        self.packet.set("specification", "rssi_broadcast")

        with self.assertRaises(ValueError):
            self.rf_sensor._process(self.packet)

        # RSSI ground station packets must raise an exception on other RF sensors.
        self.rf_sensor._id = 1

        self.packet.set("specification", "rssi_ground_station")

        with self.assertRaises(ValueError):
            self.rf_sensor._process(self.packet)

    def test_process_rssi_broadcast_packet(self):
        self.rf_sensor.start()

        timestamp = self.rf_sensor._scheduler.timestamp

        packet = self.rf_sensor._create_rssi_broadcast_packet()
        ground_station_packet = self.rf_sensor._process_rssi_broadcast_packet(packet)

        # The scheduler's timestamp must be updated.
        self.assertNotEqual(timestamp, self.rf_sensor._scheduler.timestamp)

        # A ground station packet must be returned.
        self.assertEqual(ground_station_packet.get("specification"),
                         "rssi_ground_station")
