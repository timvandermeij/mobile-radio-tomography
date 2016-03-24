import math
from dronekit import LocationLocal, VehicleMode
from mock import patch, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..geometry.Geometry import Geometry
from ..location.Line_Follower import Line_Follower_Direction, Line_Follower_State
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
            "--home-location", "0", "0", "--home-direction", "0",
            "--diverged-speed", "0.5", "--rotate-speed", "0.2"
        ])
        self.settings = self.arguments.get_settings("vehicle")
        self.settings.set("vehicle_class", "Robot_Vehicle")

        Robot_Vehicle._setup_line_follower = MagicMock()

        self.geometry = Geometry()
        self.thread_manager = Thread_Manager()
        self.vehicle = Vehicle.create(self.arguments, self.geometry,
                                      self.thread_manager, self.usb_manager)
        self.vehicle._line_follower = MagicMock()
    
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
        self.assertFalse(self.vehicle.is_current_location_valid())
        self.assertEqual(self.vehicle.attitude.yaw, 0.0)

        # Test adding a waypoint and moving to it.
        waypoint = LocationLocal(1.0, 0.0, 0.0)
        self.vehicle.add_waypoint(waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(1, 0)])
        self.assertEqual(self.vehicle.get_waypoint(), waypoint)
        self.assertEqual(self.vehicle._state.name, "move")
        set_speeds_mock.assert_called_once_with(0.3, 0.3)
        self.assertFalse(self.vehicle.is_current_location_valid())

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
        self.assertTrue(self.vehicle._at_current_waypoint())
        self.assertEqual(self.vehicle._state.name, "intersection")
        self.assertEqual(self.vehicle.location, waypoint)
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0, 0)
        self.assertTrue(self.vehicle.is_current_location_valid())

        # Start turning at an intersection
        set_speeds_mock.reset_mock()
        new_waypoint = LocationLocal(1.0, 1.0, 0.0)
        self.vehicle.simple_goto(new_waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "rotate")
        self.assertEqual(self.vehicle._state.current_direction, Line_Follower_Direction.UP)
        self.assertEqual(self.vehicle._state.target_direction, Line_Follower_Direction.RIGHT)
        self.assertEqual(self.vehicle._state.rotate_direction, 1)
        set_speeds_mock.assert_called_once_with(0.2, 0.2, True, False)
        self.assertFalse(self.vehicle.is_current_location_valid())

        # Finish turning at an intersection
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("diverged", "right")
        self.vehicle._line_follower.set_state.assert_called_with(Line_Follower_State.AT_INTERSECTION)
        self.assertEqual(self.vehicle._state.current_direction, Line_Follower_Direction.RIGHT)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "intersection")
        set_speeds_mock.assert_called_once_with(0, 0)
        self.assertEqual(self.vehicle._direction, Line_Follower_Direction.RIGHT)
        self.vehicle._line_follower.set_direction.assert_called_once_with(Line_Follower_Direction.RIGHT)
        self.assertEqual(self.vehicle.attitude.yaw, 0.5 * math.pi)

        # Moving to next intersection
        set_speeds_mock.reset_mock()
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(1, 1)])
        self.assertEqual(self.vehicle.get_waypoint(), new_waypoint)
        self.assertEqual(self.vehicle._state.name, "move")
        set_speeds_mock.assert_called_once_with(0.3, 0.3)

    @patch('thread.start_new_thread')
    def test_armed_mode(self, thread_mock):
        self.assertFalse(self.vehicle.armed)

        self.vehicle.armed = True
        self.assertTrue(self.vehicle.armed)
        self.assertEqual(thread_mock.call_count, 1)

        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.vehicle.mode = VehicleMode("RTL")
        self.assertEqual(self.vehicle.mode.name, "RTL")
        self.assertEqual(self.vehicle._waypoints, [(0,0)])
        self.vehicle.mode = VehicleMode("HALT")
        self.assertFalse(self.vehicle.armed)
