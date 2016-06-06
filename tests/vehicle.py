from mock import MagicMock
from dronekit import LocationLocal, LocationGlobal, LocationGlobalRelative, VehicleMode
from ..core.Import_Manager import Import_Manager
from ..core.Thread_Manager import Thread_Manager
from ..geometry.Geometry import Geometry
from ..settings import Arguments
from ..vehicle.Vehicle import Vehicle
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from geometry import LocationTestCase
from settings import SettingsTestCase

class VehicleTestCase(LocationTestCase, SettingsTestCase,
                      ThreadableTestCase, USBManagerTestCase):
    """
    Test case class for testing a specific vehicle.

    This class only provides basic object setup; extending test case classes
    must prepare the arguments beforehand.
    """

    def __init__(self, *a, **kw):
        super(VehicleTestCase, self).__init__(*a, **kw)

        self._argv = []
        self._vehicle_class = "Vehicle"

    def set_arguments(self, argv=None, vehicle_class=None):
        if argv is not None:
            self._argv = argv
        if vehicle_class is not None:
            self._vehicle_class = vehicle_class

    def setUp(self):
        super(VehicleTestCase, self).setUp()

        self.arguments = Arguments("settings.json", self._argv)
        self.settings = self.arguments.get_settings("vehicle")
        self.settings.set("vehicle_class", self._vehicle_class)
        self.geometry = Geometry()
        self.import_manager = Import_Manager()
        self.thread_manager = Thread_Manager()
        self.usb_manager.index()
        self.vehicle = Vehicle.create(self.arguments, self.geometry,
                                      self.import_manager, self.thread_manager,
                                      self.usb_manager)

class TestVehicle(VehicleTestCase):
    def setUp(self):
        self.set_arguments(vehicle_class="Vehicle")
        super(TestVehicle, self).setUp()

    def test_create(self):
        # Vehicle.create must return a Vehicle object.
        self.assertIsInstance(self.vehicle, Vehicle)
        # Protected member variables must be initialized
        self.assertEqual(self.vehicle._geometry, self.geometry)
        self.assertTrue(hasattr(self.vehicle, "_home_location"))
        self.assertTrue(hasattr(self.vehicle, "_mode"))
        self.assertFalse(self.vehicle._armed)
        self.assertTrue(hasattr(self.vehicle, "_servos"))
        self.assertTrue(hasattr(self.vehicle, "_attribute_listeners"))

    def test_interface(self):
        dummy = None
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.use_simulation

        self.vehicle.setup()
        self.assertIsNone(self.vehicle.home_location)
        self.vehicle.update_mission()

        self.assertFalse(self.vehicle.add_takeoff(42))
        with self.assertRaises(NotImplementedError):
            self.vehicle.add_waypoint(LocationGlobal(1.0, 2.0, 3.0))
        with self.assertRaises(NotImplementedError):
            self.vehicle.clear_waypoints()
        with self.assertRaises(NotImplementedError):
            self.vehicle.add_wait()
        with self.assertRaises(NotImplementedError):
            self.vehicle.is_wait()
        with self.assertRaises(NotImplementedError):
            self.vehicle.get_waypoint()
        with self.assertRaises(NotImplementedError):
            self.vehicle.get_next_waypoint()
        with self.assertRaises(NotImplementedError):
            self.vehicle.set_next_waypoint()
        with self.assertRaises(NotImplementedError):
            self.vehicle.count_waypoints()

        self.assertTrue(self.vehicle.check_arming())
        self.assertFalse(self.vehicle.simple_takeoff(100))

        with self.assertRaises(NotImplementedError):
            self.vehicle.simple_goto(LocationGlobal(4.0, 5.0, 6.0))
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.location

        self.vehicle.speed = 3.0
        self.vehicle.velocity = [1.2, 3.4, 5.6]
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.speed
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.velocity
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.attitude

        self.vehicle.set_yaw(0, relative=True, direction=-1)
        with self.assertRaises(NotImplementedError):
            self.vehicle.set_servo(7, 1000)

    def test_home_location(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("home_location", mock_callback)
        self.assertEqual(self.vehicle._attribute_listeners["home_location"],
                         [mock_callback])
        new_location = LocationGlobal(1.0, 2.0, 3.0)
        self.vehicle.home_location = new_location
        self.assertEqual(self.vehicle._home_location, new_location)

        # Test if the listener is called with the correct arguments
        self.assertEqual(mock_callback.call_count, 1)
        call_args = mock_callback.call_args[0]
        self.assertEqual(call_args[0], self.vehicle)
        self.assertEqual(call_args[1], "home_location")
        self.assertEqual(call_args[2], new_location)

        with self.assertRaises(ValueError):
            self.vehicle.remove_attribute_listener("home_location", lambda: 99)
        self.vehicle.remove_attribute_listener("home_location", mock_callback)
        self.assertNotIn("home_location", self.vehicle._attribute_listeners)
        with self.assertRaises(KeyError):
            self.vehicle.remove_attribute_listener("xyz", mock_callback)

    def test_mode(self):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.assertEqual(self.vehicle.mode, self.vehicle._mode)

    def test_armed(self):
        self.vehicle.armed = True
        self.assertTrue(self.vehicle.armed)
        self.vehicle.armed = False
        self.assertFalse(self.vehicle.armed)
        self.assertEqual(self.vehicle.armed, self.vehicle._armed)

    def test_location_valid(self):
        self.assertTrue(self.vehicle.is_location_valid(LocationGlobal(1.0, 2.3, 4.2)))
        self.assertFalse(self.vehicle.is_location_valid(LocationGlobal(None, 2.3, 4.2)))
        self.assertFalse(self.vehicle.is_location_valid(LocationGlobal(1.0, 2.3, None)))
        self.assertTrue(self.vehicle.is_location_valid(LocationLocal(5.0, 4.0, 3.0)))
        self.assertFalse(self.vehicle.is_location_valid(LocationLocal(None, 4.0, 3.0)))
        with self.assertRaises(TypeError):
            self.vehicle.is_location_valid((1, 2, 3))

    def test_set_servos(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("servos", mock_callback)

        servos = {1: 255, 2: 100}
        self.vehicle._set_servos(servos)
        self.assertEqual(self.vehicle._servos, servos)
        mock_callback.assert_called_once_with(self.vehicle, "servos", servos)

        mock_callback.reset_mock()
        new_servos = {1: 42, 3: 1024}
        result_servos = {1: 42, 2: 100, 3: 1024}
        self.vehicle._set_servos(new_servos)
        self.assertEqual(self.vehicle._servos, result_servos)
        mock_callback.assert_called_once_with(self.vehicle, "servos", result_servos)

    def test_make_global_location(self):
        global_location = LocationGlobal(1.0, 2.0, 3.0)
        relative_location = LocationGlobalRelative(6.0, 7.0, 8.0)
        local_location = LocationLocal(4.0, 3.0, -2.0)
        self.assertEqual(self.vehicle._make_global_location(global_location), global_location)
        self.assertEqual(self.vehicle._make_global_location(relative_location), LocationGlobal(6.0, 7.0, 8.0))
        self.assertEqual(self.vehicle._make_global_location(local_location), LocationGlobal(4.0, 3.0, 2.0))

        self.vehicle.home_location = global_location

        self.assertEqual(self.vehicle._make_global_location(global_location), global_location)
        self.assertEqual(self.vehicle._make_global_location(relative_location), LocationGlobal(6.0, 7.0, 11.0))
        self.assertEqual(self.vehicle._make_global_location(local_location), LocationGlobal(5.0, 5.0, 5.0))
