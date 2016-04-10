from mock import patch, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..distance.Distance_Sensor_Simulator import Distance_Sensor_Simulator
from ..environment.Environment import Environment
from ..geometry.Geometry import Geometry_Spherical
from ..settings import Arguments
from ..trajectory.Servo import Servo
from ..vehicle.Mock_Vehicle import Mock_Vehicle
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from ..zigbee.XBee_Packet import XBee_Packet
from geometry import LocationTestCase
from settings import SettingsTestCase
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase

class EnvironmentTestCase(LocationTestCase, SettingsTestCase, ThreadableTestCase, USBManagerTestCase):
    def register_arguments(self, argv, use_infrared_sensor=True):
        self._argv = argv
        self._argv.extend(["--xbee-type", "simulator", "--xbee-id", "1"])

        self._use_infrared_sensor = use_infrared_sensor
        if self._use_infrared_sensor:
            self._argv.append("--infrared-sensor")
        else:
            self._argv.append("--no-infrared-sensor")

    def setUp(self):
        super(EnvironmentTestCase, self).setUp()

        self.arguments = Arguments("settings.json", self._argv)

        if self._use_infrared_sensor:
            # We need to mock the Infrared_Sensor module as it is only 
            # available when LIRC is installed which is not a requirement for 
            # running tests.
            package = __package__.split('.')[0]
            self.infrared_sensor_mock = MagicMock()
            modules = {
                package + '.control.Infrared_Sensor': self.infrared_sensor_mock,
            }

            self._infrared_sensor_patcher = patch.dict('sys.modules', modules)
            self._infrared_sensor_patcher.start()

        self.environment = Environment.setup(self.arguments,
                                             usb_manager=self.usb_manager,
                                             simulated=True)

    def tearDown(self):
        super(EnvironmentTestCase, self).tearDown()
        if self._use_infrared_sensor:
            self._infrared_sensor_patcher.stop()

class TestEnvironment(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--geometry-class", "Geometry_Spherical",
            "--vehicle-class", "Mock_Vehicle", "--distance-sensors", "0", "90",
            "--number-of-sensors", "3"
        ], use_infrared_sensor=True)

        super(TestEnvironment, self).setUp()

    def test_setup(self):
        self.assertIsInstance(self.environment, Environment)
        self.assertIsInstance(self.environment.vehicle, Mock_Vehicle)
        self.assertIsInstance(self.environment.geometry, Geometry_Spherical)
        self.assertIsInstance(self.environment.thread_manager, Thread_Manager)
        self.assertEqual(self.environment.usb_manager, self.usb_manager)
        self.assertEqual(self.environment.arguments, self.arguments)
        self.assertTrue(self.environment.settings.get("infrared_sensor"))

        self.assertEqual(self.environment.get_vehicle(), self.environment.vehicle)
        self.assertEqual(self.environment.get_geometry(), self.environment.geometry)
        self.assertEqual(self.environment.get_arguments(), self.environment.arguments)

        distance_sensors = self.environment.get_distance_sensors()
        expected_angles = [0, 90]
        self.assertEqual(len(distance_sensors), len(expected_angles))
        for i in range(len(expected_angles)):
            self.assertIsInstance(distance_sensors[i], Distance_Sensor_Simulator)
            self.assertEqual(distance_sensors[i].id, i)
            self.assertEqual(distance_sensors[i].angle, expected_angles[i])

        for servo in self.environment.get_servos():
            self.assertIsInstance(servo, Servo)

        self.assertIsInstance(self.environment.get_xbee_sensor(), XBee_Sensor_Simulator)
        self.assertIsNotNone(self.environment.get_infrared_sensor())

    def test_packet_action(self):
        # Callback must be callable
        with self.assertRaises(TypeError):
            self.environment.add_packet_action("waypoint_add", "no_function")

        mock_callback = MagicMock()
        self.environment.add_packet_action("waypoint_add", mock_callback)
        # Not allowed to add more than one callback for a packet specification.
        with self.assertRaises(KeyError):
            self.environment.add_packet_action("waypoint_add", MagicMock())

        # Callback is called for correct specification.
        packet = XBee_Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", 12.345)
        packet.set("longitude", 32.109)
        packet.set("to_id", 1)

        self.environment.receive_packet(packet)
        mock_callback.assert_called_once_with(packet)

        # Callback is not called for another specification.
        mock_callback.reset_mock()
        other_packet = XBee_Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 1)

        self.environment.receive_packet(packet)
        mock_callback.assert_not_called()

    def test_location(self):
        location = self.environment.vehicle.location.global_relative_frame
        self.assertEqual(location, self.environment.get_location())
        self.assertEqual((location.lat, location.lon), self.environment.get_raw_location())

    def test_location_valid(self):
        xbee = self.environment.get_xbee_sensor()

        self.assertEqual(self.environment._valid_measurements, {})
        self.assertEqual(self.environment._required_sensors, set(range(1, xbee.number_of_sensors + 1)))

        self.assertTrue(self.environment.location_valid())
        self.assertFalse(self.environment.is_measurement_valid())
        self.assertEqual(self.environment._valid_measurements, {xbee.id: True})

        self.assertTrue(self.environment.location_valid(other_valid=True, other_id=xbee.id + 1))
        self.assertFalse(self.environment.is_measurement_valid())
        self.assertEqual(self.environment._valid_measurements, {xbee.id: True, xbee.id + 1: True})

        self.assertTrue(self.environment.location_valid(other_valid=True, other_id=xbee.id + 2))
        self.assertTrue(self.environment.is_measurement_valid())

        # Requiring a specific set of sensors
        self.environment.invalidate_measurement(required_sensors=[xbee.id + 1])
        self.assertFalse(self.environment.is_measurement_valid())

        self.assertTrue(self.environment.location_valid(other_valid=True, other_id=xbee.id + 1))
        self.assertTrue(self.environment.is_measurement_valid())
