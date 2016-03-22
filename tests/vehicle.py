from mock import MagicMock
from dronekit import LocationLocal, LocationGlobal, LocationGlobalRelative, VehicleMode
from ..core.Thread_Manager import Thread_Manager
from ..geometry.Geometry import Geometry
from ..settings import Arguments
from ..vehicle.Vehicle import Vehicle
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from geometry import LocationTestCase

class TestVehicle(LocationTestCase, ThreadableTestCase, USBManagerTestCase):
    def setUp(self):
        super(TestVehicle, self).setUp()
        self.arguments = Arguments("settings.json", [
            "--vehicle-class", "Vehicle"
        ])
        self.geometry = Geometry()
        self.thread_manager = Thread_Manager()
        self.vehicle = Vehicle.create(self.arguments, self.geometry,
                                      self.thread_manager, self.usb_manager)

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

    def test_home_location(self):
        mock_callback = MagicMock()
        self.vehicle.add_attribute_listener("home_location", mock_callback)
        new_location = LocationGlobal(1.0, 2.0, 3.0)
        self.vehicle.home_location = new_location
        self.assertEqual(self.vehicle._home_location, new_location)

        # Test if the listener is called with the correct arguments
        self.assertEqual(mock_callback.call_count, 1)
        call_args = mock_callback.call_args[0]
        self.assertEqual(call_args[0], self.vehicle)
        self.assertEqual(call_args[1], "home_location")
        self.assertEqual(call_args[2], new_location)

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
