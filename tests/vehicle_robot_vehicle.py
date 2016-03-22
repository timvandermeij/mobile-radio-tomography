from dronekit import LocationLocal, VehicleMode
from mock import patch, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..geometry.Geometry import Geometry
from ..location.Line_Follower import Line_Follower_Direction
from ..settings import Arguments
from ..vehicle.Robot_Vehicle import Robot_State, Robot_Vehicle
from ..vehicle.Vehicle import Vehicle
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from geometry import LocationTestCase
from settings import SettingsTestCase

class TestVehicleRobotVehicle(LocationTestCase, SettingsTestCase, ThreadableTestCase, USBManagerTestCase):
    def setUp(self):
        super(TestVehicleRobotVehicle, self).setUp()
        self.arguments = Arguments("settings.json", [
            "--vehicle-class", "Robot_Vehicle", "--home-location", "0", "0",
            "--home-direction", "0", "--diverged-speed", "0.5"
        ])

        Robot_Vehicle._setup_line_follower = MagicMock()

        self.geometry = Geometry()
        self.thread_manager = Thread_Manager()
        self.vehicle = Vehicle.create(self.arguments, self.geometry,
                                      self.thread_manager, self.usb_manager)
    
    def test_init(self):
        self.assertEqual(self.vehicle.arguments, self.arguments)
        self.assertEqual(self.vehicle._home_location, (0,0))
        self.assertEqual(self.vehicle._direction, Line_Follower_Direction.UP)
        self.assertIsInstance(self.vehicle._state, Robot_State)
        self.assertEqual(self.vehicle._state.name, "intersection")
        Robot_Vehicle._setup_line_follower.assert_called_once_with(self.thread_manager, self.usb_manager)

    @patch.object(Robot_Vehicle, 'set_speeds')
    def test_check_state(self, set_speeds_mock):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.speed = 0.3

        # Test default state: No changes
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, -1)
        self.assertEqual(self.vehicle._waypoints, [])

        # Test adding a waypoint and moving to it.
        waypoint = LocationLocal(1.0, 0.0, 0.0)
        self.vehicle.add_waypoint(waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(1, 0)])
        self.assertEqual(self.vehicle.get_waypoint(), waypoint)
        self.assertEqual(self.vehicle._state.name, "move")
        set_speeds_mock.assert_called_once_with(0.3, 0.3)

        # Test diverged state
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("diverged", "left")
        self.assertIsNotNone(self.vehicle._last_diverged_time)
        set_speeds_mock.assert_called_once_with(0.5 * 0.3, 0.3 + 0.5 * 0.3)

        # Done diverging
        set_speeds_mock.reset_mock()
        self.vehicle._last_diverged_time = 0
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0.3, 0.3)

        # Reached the waypoint intersection
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("intersection", (0,1))
        self.assertEqual(self.vehicle._state.name, "intersection")
        self.assertEqual(self.vehicle.location, waypoint)
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0, 0)
