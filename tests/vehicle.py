from mock import patch, MagicMock, PropertyMock
from dronekit import LocationLocal, LocationGlobal, LocationGlobalRelative, VehicleMode
from ..bench.Method_Coverage import covers
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

        self._location_valid_cases = [
            (LocationGlobal(1.0, 2.3, 4.2), True),
            (LocationGlobal(None, 2.3, 4.2), False),
            (LocationGlobal(1.0, 2.3, None), False),
            (LocationLocal(5.0, 4.0, 3.0), True),
            (LocationLocal(None, 4.0, 3.0), False)
        ]

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

    @covers([
        "setup", "pause", "update_mission", "add_takeoff", "add_waypoint",
        "clear_waypoints", "add_wait", "is_wait", "get_waypoint",
        "get_next_waypoint", "set_next_waypoint", "count_waypoints",
        "check_arming", "simple_takeoff", "simple_goto", "set_yaw", "set_servo"
    ])
    def test_interface(self):
        dummy = None
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.use_simulation
        with self.assertRaises(NotImplementedError):
            dummy = self.vehicle.home_location

        self.vehicle.setup()

        with self.assertRaises(NotImplementedError):
            self.vehicle.pause()

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
        new_location = LocationGlobal(1.0, 2.0, 3.0)
        self.vehicle.home_location = new_location
        self.assertEqual(self.vehicle._home_location, new_location)

    def test_add_attribute_listener(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("home_location", mock_callback)
        self.assertEqual(self.vehicle._attribute_listeners["home_location"],
                         [mock_callback])
        new_location = LocationGlobal(1.0, 2.0, 3.0)
        self.vehicle.home_location = new_location
        self.assertEqual(self.vehicle._home_location, new_location)

        # Test if the listener is called with the correct arguments.
        self.assertEqual(mock_callback.call_count, 1)
        call_args = mock_callback.call_args[0]
        self.assertEqual(call_args[0], self.vehicle)
        self.assertEqual(call_args[1], "home_location")
        self.assertEqual(call_args[2], new_location)

    def test_remove_attribute_listener(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("home_location", mock_callback)

        # The listener must already have been registered.
        with self.assertRaises(ValueError):
            self.vehicle.remove_attribute_listener("home_location", lambda: 99)

        # Removing an existing listener works.
        self.vehicle.remove_attribute_listener("home_location", mock_callback)
        self.assertNotIn("home_location", self.vehicle._attribute_listeners)

        self.vehicle.home_location = LocationGlobal(5.0, 6.0, 7.0)
        mock_callback.assert_not_called()

        # The attribute must already have registered listeners.
        with self.assertRaises(KeyError):
            self.vehicle.remove_attribute_listener("xyz", mock_callback)

    def test_notify_attribute_listeners(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("foo", mock_callback)

        self.vehicle.notify_attribute_listeners("foo", "Hello!")
        mock_callback.assert_called_once_with(self.vehicle, "foo", "Hello!")

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

    def test_is_location_valid(self):
        for location, expected in self._location_valid_cases:
            neg = "" if expected else " not"
            self.assertEqual(self.vehicle.is_location_valid(location), expected,
                             msg="{} must{} be valid".format(location, neg))

        with self.assertRaises(TypeError):
            self.vehicle.is_location_valid((1, 2, 3))

    @patch.object(Vehicle, "location", new_callable=PropertyMock)
    def test_is_current_location_valid(self, location_mock):
        for location, expected in self._location_valid_cases: 
            neg = "" if expected else " not"
            location_mock.configure_mock(return_value=location)
            self.assertEqual(self.vehicle.is_current_location_valid(), expected,
                             msg="{} must{} be valid".format(location, neg))

    def test_set_servos(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("servos", mock_callback)

        servos = {1: 255, 2: 100}
        self.vehicle._set_servos(servos)
        self.assertEqual(self.vehicle._servos, servos)
        mock_callback.assert_called_once_with(self.vehicle, "servos", servos)

        mock_callback.reset_mock()
        new_servos = {1: 42, 3: 1024}
        expected = {1: 42, 2: 100, 3: 1024}
        self.vehicle._set_servos(new_servos)
        self.assertEqual(self.vehicle._servos, expected)
        mock_callback.assert_called_once_with(self.vehicle, "servos", expected)

    def test_make_global_location(self):
        global_location = LocationGlobal(1.0, 2.0, 3.0)
        relative_location = LocationGlobalRelative(6.0, 7.0, 8.0)
        local_location = LocationLocal(4.0, 3.0, -2.0)
        self.assertEqual(self.vehicle._make_global_location(global_location),
                         global_location)
        self.assertEqual(self.vehicle._make_global_location(relative_location),
                         LocationGlobal(6.0, 7.0, 8.0))
        self.assertEqual(self.vehicle._make_global_location(local_location),
                         LocationGlobal(4.0, 3.0, 2.0))

        self.vehicle.home_location = global_location

        self.assertEqual(self.vehicle._make_global_location(global_location),
                         global_location)
        self.assertEqual(self.vehicle._make_global_location(relative_location),
                         LocationGlobal(6.0, 7.0, 11.0))
        self.assertEqual(self.vehicle._make_global_location(local_location),
                         LocationGlobal(5.0, 5.0, 5.0))
