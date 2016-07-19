import math
from dronekit import LocationLocal, LocationGlobal
from mock import patch, MagicMock, PropertyMock
from ..bench.Method_Coverage import covers
from ..core.Import_Manager import Import_Manager
from ..core.Thread_Manager import Thread_Manager
from ..core.USB_Manager import USB_Manager
from ..distance.Distance_Sensor_Simulator import Distance_Sensor_Simulator
from ..environment.Environment import Environment
from ..environment.Environment_Simulator import Environment_Simulator
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..settings import Arguments
from ..trajectory.Servo import Servo
from ..vehicle.Mock_Vehicle import Mock_Vehicle, MockAttitude
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import RF_Sensor
from geometry import LocationTestCase
from settings import SettingsTestCase
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from core_wiringpi import WiringPiTestCase

class EnvironmentTestCase(LocationTestCase, SettingsTestCase,
                          ThreadableTestCase, USBManagerTestCase,
                          WiringPiTestCase):
    """
    Test case class for tests that make use of the `Environment` class,
    including mission and distance sensor tests.

    This class handles initializing the settings in a generic manner and
    providing various means of simulating sensors and other modules.
    """

    def __init__(self, *a, **kw):
        super(EnvironmentTestCase, self).__init__(*a, **kw)

        self._argv = []
        self._modules = {}
        self._simulated = True

    def register_arguments(self, argv, simulated=True, distance_sensors=None,
                           use_infrared_sensor=True):
        self._argv = argv
        self._argv.extend([
            "--rf-sensor-class", "RF_Sensor_Simulator", "--rf-sensor-id", "1"
        ])

        self._simulated = simulated
        # WiringPiTestCase provides a patcher for RPi.GPIO, which is necessary 
        # when not in simulation mode to be able to run those tests on PC. 
        # Additionally, it always handles the WiringPi setup singleton.
        self.set_rpi_patch(rpi_patch=not simulated)

        self._modules = {}

        if use_infrared_sensor:
            # We need to mock the Infrared_Sensor module as it is only 
            # available when LIRC is installed which is not a requirement for 
            # running tests.
            package = __package__.split('.')[0]
            self._modules[package + '.control.Infrared_Sensor'] = MagicMock()

            self._argv.append("--infrared-sensor")
        else:
            self._argv.append("--no-infrared-sensor")

        if distance_sensors is not None:
            self._argv.append("--distance-sensors")
            self._argv.extend([str(sensor) for sensor in distance_sensors])

    def setUp(self):
        super(EnvironmentTestCase, self).setUp()

        self.arguments = Arguments("settings.json", self._argv)

        if self._modules:
            self._module_patcher = patch.dict('sys.modules', self._modules)
            self._module_patcher.start()

        self.environment = Environment.setup(self.arguments,
                                             usb_manager=self.usb_manager,
                                             simulated=self._simulated)

        # Make the environment thread manager available to the tearDown method 
        # of the ThreadableTestCase.
        self.thread_manager = self.environment.thread_manager

    def tearDown(self):
        super(EnvironmentTestCase, self).tearDown()
        if self._modules:
            self._module_patcher.stop()

class TestEnvironment(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--geometry-class", "Geometry_Spherical",
            "--vehicle-class", "Mock_Vehicle", "--number-of-sensors", "3"
        ], distance_sensors=[0, 90], use_infrared_sensor=True)

        super(TestEnvironment, self).setUp()

        self.servos = []
        for pin, value in [(6, 45), (7, 90)]:
            methods = {
                "get_pin.return_value": pin,
                "get_value.return_value": value
            }
            self.servos.append(MagicMock(spec=Servo, **methods))

        self.environment._servos = self.servos

    def test_setup(self):
        settings = self.arguments.get_settings("environment")
        settings.set("rf_sensor_class", "")
        environment = Environment.setup(self.arguments,
                                        simulated=self._simulated)
        self.assertIsInstance(environment.usb_manager, USB_Manager)

        geometry = Geometry_Spherical()
        import_manager = Import_Manager()
        thread_manager = Thread_Manager()
        usb_manager = USB_Manager()
        vehicle = Mock_Vehicle(self.arguments, geometry, import_manager,
                               thread_manager, usb_manager)
        environment = Environment.setup(self.arguments,
                                        geometry_class="Geometry_Spherical",
                                        vehicle=vehicle,
                                        thread_manager=thread_manager,
                                        usb_manager=usb_manager)
        self.assertIsInstance(environment, Environment_Simulator)
        self.assertIsInstance(environment.geometry, Geometry_Spherical)
        self.assertEqual(environment.vehicle, vehicle)
        self.assertEqual(environment.thread_manager, thread_manager)
        self.assertEqual(environment.usb_manager, usb_manager)
        self.assertIsNone(environment.get_rf_sensor())
        self.assertEqual(environment._required_sensors, set())
        for servo in environment.get_servos():
            self.assertIsInstance(servo, Servo)

        with self.assertRaises(ValueError):
            environment = Environment.setup(self.arguments, vehicle=vehicle)

        simulation_mock = PropertyMock(return_value=False)
        with patch.object(Mock_Vehicle, 'use_simulation', new_callable=simulation_mock):
            vehicle = Mock_Vehicle(self.arguments, geometry, import_manager,
                                   thread_manager, usb_manager)
            with self.assertRaises(ValueError):
                environment = Environment.setup(self.arguments, vehicle=vehicle,
                                                thread_manager=thread_manager,
                                                usb_manager=usb_manager,
                                                simulated=True)

    @covers(["get_objects", "get_distance_sensors"])
    def test_base_interface(self):
        geometry = Geometry_Spherical()
        import_manager = Import_Manager()
        thread_manager = Thread_Manager()
        usb_manager = USB_Manager()
        vehicle = Mock_Vehicle(self.arguments, geometry, import_manager,
                               thread_manager, usb_manager)
        environment = Environment(vehicle, geometry, self.arguments,
                                  import_manager, thread_manager, usb_manager)
        # Base class does not provide simulated objects or distance sensors.
        self.assertEqual(environment.get_objects(), [])
        with self.assertRaises(NotImplementedError):
            environment.get_distance_sensors()

    def test_initialization(self):
        self.assertIsInstance(self.environment, Environment)
        self.assertIsInstance(self.environment.vehicle, Mock_Vehicle)
        self.assertIsInstance(self.environment.geometry, Geometry_Spherical)
        self.assertIsInstance(self.environment.import_manager, Import_Manager)
        self.assertIsInstance(self.environment.thread_manager, Thread_Manager)
        self.assertEqual(self.environment.usb_manager, self.usb_manager)
        self.assertEqual(self.environment.arguments, self.arguments)
        self.assertTrue(self.environment.settings.get("infrared_sensor"))

    @covers([
        "get_vehicle", "get_geometry", "get_arguments", "get_import_manager",
        "get_thread_manager", "get_usb_manager", "get_distance_sensors",
        "get_rf_sensor", "get_infrared_sensor", "get_servos"
    ])
    def test_interface(self):
        self.assertEqual(self.environment.get_vehicle(),
                         self.environment.vehicle)
        self.assertEqual(self.environment.get_geometry(),
                         self.environment.geometry)
        self.assertEqual(self.environment.get_arguments(),
                         self.environment.arguments)

        self.assertEqual(self.environment.get_import_manager(),
                         self.environment.import_manager)
        self.assertEqual(self.environment.get_thread_manager(),
                         self.environment.thread_manager)
        self.assertEqual(self.environment.get_usb_manager(),
                         self.environment.usb_manager)

        distance_sensors = self.environment.get_distance_sensors()
        expected_angles = [0, 90]
        self.assertEqual(len(distance_sensors), len(expected_angles))
        for i, expected_angle in enumerate(expected_angles):
            self.assertIsInstance(distance_sensors[i], Distance_Sensor_Simulator)
            self.assertEqual(distance_sensors[i].id, i)
            self.assertEqual(distance_sensors[i].angle, expected_angle)

        self.assertIsInstance(self.environment.get_rf_sensor(), RF_Sensor)
        self.assertIsNotNone(self.environment.get_infrared_sensor())
        self.assertEqual(self.environment.get_servos(), self.servos)

    def test_on_servos(self):
        pwms = {
            6: 500,
            7: 1000,
            9: 1234,
            "abc": 42
        }
        self.environment.on_servos(self.environment.vehicle, "servos", pwms)
        self.servos[0].set_current_pwm.assert_called_once_with(500)
        self.servos[1].set_current_pwm.assert_called_once_with(1000)

    def test_on_home_location(self):
        loc = LocationGlobal(1.0, 2.0, 3.0)
        self.environment.on_home_location(self.environment.vehicle,
                                          "home_location", loc)
        self.assertEqual(self.environment.geometry.home_location, loc)

    @covers(["add_packet_action", "receive_packet"])
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
        packet = Packet()
        packet.set("specification", "waypoint_add")
        packet.set("latitude", 12.345)
        packet.set("longitude", 32.109)
        packet.set("to_id", 1)

        self.environment.receive_packet(packet)
        mock_callback.assert_called_once_with(packet)

        # Callback is not called for another specification.
        mock_callback.reset_mock()
        packet = Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", 1)

        self.environment.receive_packet(packet)
        mock_callback.assert_not_called()

    @covers(["get_location", "get_raw_location"])
    def test_location(self):
        vehicle = self.environment.vehicle
        self.assertEqual(self.environment.location, vehicle.location)

        location = self.environment.vehicle.location.global_relative_frame
        self.assertEqual(location, self.environment.get_location())

        # Raw location provides the correct return value corresponding to the 
        # real location.
        raw_location, waypoint_index = self.environment.get_raw_location()
        self.assertEqual(raw_location, (location.lat, location.lon))
        self.assertEqual(waypoint_index, 0)

        loc = LocationLocal(1.2, 3.4, -5.6)
        with patch.object(vehicle, "_locations", new=loc):
            raw_location, waypoint_index = self.environment.get_raw_location()
            self.assertEqual(raw_location, (loc.north, loc.east))
            self.assertEqual(waypoint_index, 0)

    @covers([
        "location_valid", "is_measurement_valid", "invalidate_measurement"
    ])
    def test_valid(self):
        rf_sensor = self.environment.get_rf_sensor()
        other_id = rf_sensor.id + 1

        self.assertEqual(self.environment._valid_measurements, {})
        self.assertEqual(self.environment._required_sensors,
                         set(range(1, rf_sensor.number_of_sensors + 1)))

        self.assertTrue(self.environment.location_valid())
        self.assertFalse(self.environment.is_measurement_valid())
        self.assertEqual(self.environment._valid_measurements,
                         {rf_sensor.id: 0})

        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=0))
        self.assertFalse(self.environment.is_measurement_valid())
        self.assertEqual(self.environment._valid_measurements,
                         {rf_sensor.id: 0, other_id: 0})

        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id + 1,
                                                        other_index=0))
        self.assertTrue(self.environment.is_measurement_valid())

        # Requiring a specific set of sensors
        self.environment.invalidate_measurement(required_sensors=[other_id])
        self.assertTrue(self.environment.location_valid())
        self.assertFalse(self.environment.is_measurement_valid())

        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=0))
        self.assertTrue(self.environment.is_measurement_valid())

        # Check that receiving valid measurements in other orders works as 
        # expected, i.e., it waits a full sweep.
        self.environment.invalidate_measurement()
        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=0))
        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id + 1,
                                                        other_index=0))

        self.assertFalse(self.environment.is_measurement_valid())

        self.assertTrue(self.environment.location_valid())
        self.assertFalse(self.environment.is_measurement_valid())

        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=0))
        self.assertTrue(self.environment.is_measurement_valid())

    def test_get_distance(self):
        loc = LocationLocal(12.0, 5.0, 0.0)
        # 12**2 + 5**2 = 144 + 25 which is 13 squared.
        self.assertEqual(self.environment.get_distance(loc), 13.0)

    def test_get_yaw(self):
        vehicle = self.environment.vehicle
        vehicle.attitude = MockAttitude(0.0, 0.25*math.pi, 0.0, vehicle)
        self.assertEqual(self.environment.get_yaw(), 0.25*math.pi)

    def test_get_sensor_yaw(self):
        vehicle = self.environment.vehicle
        vehicle.attitude = MockAttitude(0.0, 0.5*math.pi, 0.0, vehicle)
        self.assertEqual(self.environment.get_sensor_yaw(), 0.75*math.pi)
        self.assertEqual(self.environment.get_sensor_yaw(id=1), math.pi)
        # A sensor ID outside the scope of the number of servos means that we 
        # receive the vehicle's yaw.
        self.assertEqual(self.environment.get_sensor_yaw(id=6), 0.5*math.pi)

    def test_get_angle(self):
        vehicle = self.environment.vehicle
        vehicle.attitude = MockAttitude(0.0, 0.5*math.pi, 0.0, vehicle)
        self.assertEqual(self.environment.get_angle(), 0.0)

    def test_get_pitch(self):
        vehicle = self.environment.vehicle
        vehicle.attitude = MockAttitude(0.75*math.pi, 0.0, 0.0, vehicle)
        self.assertEqual(self.environment.get_pitch(), 0.75*math.pi)
