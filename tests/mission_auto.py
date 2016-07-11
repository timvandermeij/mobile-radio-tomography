# Core imports
import time
from mock import patch

# Library imports
from dronekit import LocationLocal, LocationGlobalRelative

# Package imports
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..environment.Environment import Environment
from ..mission.Mission import Mission
from ..mission.Mission_Auto import Mission_Auto
from ..vehicle.Mock_Vehicle import Mock_Vehicle
from environment import EnvironmentTestCase

class TestMissionAuto(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle", "--geometry-class", "Geometry",
            "--rf-sensor-synchronization", "--measurement-delay", "0",
            "--closeness", "1"
        ], use_infrared_sensor=False)

        super(TestMissionAuto, self).setUp()

        self.settings = self.arguments.get_settings("mission")
        self.mission = Mission_Auto(self.environment, self.settings)
        self.vehicle = self.mission.vehicle

        with patch("sys.stdout"):
            self.mission.setup()

    def test_setup(self):
        self.assertIsNone(self.mission._waypoints)
        self.assertEqual(self.mission._first_waypoint, 1)
        self.assertEqual(self.mission._required_waypoint_sensors, [])

    @patch.object(Mission_Auto, "get_points")
    def test_arm_and_takeoff(self, get_points_mock):
        with patch("sys.stdout"):
            self.mission.arm_and_takeoff()
            get_points_mock.assert_called_once_with()
            self.assertTrue(self.vehicle.armed)

    @patch.object(Mission_Auto, "add_commands", side_effect=RuntimeError)
    def test_arm_and_takeoff_raises(self, add_commands_mock):
        with patch("sys.stdout"):
            self.mission.arm_and_takeoff()
            add_commands_mock.assert_called_once_with()
            self.assertTrue(self.vehicle.armed)

    @patch.object(Mission_Auto, "get_points")
    def test_get_waypoints(self, get_points_mock):
        waypoints = self.mission.get_waypoints()
        self.assertEqual(waypoints, get_points_mock.return_value)

        # Calling the method again returns a cached list of waypoints.
        self.assertEqual(self.mission._waypoints, waypoints)
        self.assertEqual(self.mission.get_waypoints(), waypoints)
        get_points_mock.assert_called_once_with()

    def test_get_points(self):
        # Verify that the interface requires subclasses to implement
        # the `get_points()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.get_points()

    @patch.object(Mock_Vehicle, "add_takeoff")
    def test_add_takeoff(self, add_takeoff_mock):
        add_takeoff_mock.configure_mock(return_value=True)
        self.mission.add_takeoff()
        add_takeoff_mock.assert_called_once_with(self.settings.get("altitude"))

        add_takeoff_mock.reset_mock()
        add_takeoff_mock.configure_mock(return_value=False)
        self.mission.add_takeoff()
        add_takeoff_mock.assert_called_once_with(self.settings.get("altitude"))
        self.assertEqual(self.mission.altitude, 0.0)
        self.assertEqual(self.mission._first_waypoint, 0)

    def test_convert_waypoint(self):
        loc = LocationLocal(1.2, 3.4, 0.0)
        adjusted_loc = LocationLocal(1.2, 3.4, -self.settings.get("altitude"))
        self.assertEqual(self.mission._convert_waypoint(loc), adjusted_loc)

        loc = LocationGlobalRelative(5.6, 7.8, 9.0)
        local_loc = LocationLocal(5.6, 7.8, -9.0)
        self.assertEqual(self.mission._convert_waypoint(loc), local_loc)

        loc = LocationGlobalRelative(4.3, 2.1, 0.0)
        new_loc = LocationGlobalRelative(4.3, 2.1, self.settings.get("altitude"))
        with patch.object(self.mission, "geometry", new=Geometry_Spherical()):
            self.assertEqual(self.mission._convert_waypoint(loc), new_loc)

    @patch.object(Mock_Vehicle, "add_waypoint")
    @patch.object(Mock_Vehicle, "add_wait")
    def test_add_waypoint(self, add_wait_mock, add_waypoint_mock):
        loc = LocationLocal(1.2, 3.4, 5.6)
        self.mission.add_waypoint(loc)

        self.assertEqual(add_waypoint_mock.call_count, 1)
        args = add_waypoint_mock.call_args[0]
        self.assertEqual(args[0], loc)
        add_wait_mock.assert_called_once_with()

        self.assertEqual(self.mission._required_waypoint_sensors, [None])

        self.mission.add_waypoint(loc, required_sensors=[2, 3])
        self.assertEqual(self.mission._required_waypoint_sensors, [None, [2, 3]])

    @patch.object(Mission_Auto, "get_waypoints")
    @patch.object(Mission_Auto, "add_waypoint")
    def test_add_commands(self, add_waypoint_mock, get_waypoints_mock):
        waypoints = [
            LocationLocal(1.0, 2.0, 3.0), LocationLocal(4.0, 5.0, 6.0),
            LocationLocal(7.0, 8.0, 9.0), LocationLocal(0.0, 1.0, -2.0)
        ]
        get_waypoints_mock.configure_mock(return_value=waypoints)

        with patch("sys.stdout"):
            self.mission.add_commands()

        get_waypoints_mock.assert_called_once_with()
        self.assertEqual(add_waypoint_mock.call_count, len(waypoints))
        for actual, expected in zip(add_waypoint_mock.call_args_list, waypoints):
            self.assertEqual(actual[0][0], expected)

    def test_display(self):
        with patch.object(time, "sleep") as sleep_mock:
            with patch.object(Mission, "check_mission") as check_mission_mock:
                self.mission.display()

                # The method must wait for a period of time before checking the
                # mission's commands to ensure that output is displayed cleanly.
                sleep_mock.assert_any_call(self.settings.get("mission_delay"))
                check_mission_mock.assert_called_once_with()

    def test_start(self):
        self.mission.start()
        self.assertEqual(self.vehicle.mode.name, "AUTO")

    def test_step(self):
        # The `step` method does not do anything, not even raising exceptions.
        self.mission.step()

    @patch.object(Environment, "is_measurement_valid")
    @patch.object(Environment, "invalidate_measurement")
    def test_check_wait(self, invalidate_measurement_mock, measurement_valid_mock):
        self.assertFalse(self.mission.check_wait())

        self.vehicle.add_wait()
        measurement_valid_mock.configure_mock(return_value=False)
        self.assertTrue(self.mission.check_wait())
        measurement_valid_mock.assert_called_once_with()
        invalidate_measurement_mock.assert_not_called()

        measurement_valid_mock.configure_mock(return_value=True)
        with patch("sys.stdout"):
            self.assertFalse(self.mission.check_wait())
            self.assertEqual(self.vehicle.commands.next, 1)

            invalidate_measurement_mock.assert_called_once_with(None)

    def test_check_waypoint(self):
        with patch("sys.stdout"):
            self.mission._first_waypoint = 0
            self.assertTrue(self.mission.check_waypoint())

            self.mission.add_waypoint(LocationLocal(1.0, 2.0, 0.0))
            self.assertTrue(self.mission.check_waypoint())
            self.assertEqual(self.vehicle.commands.next, 0)

            self.vehicle.set_location(0.5, 2.0, self.settings.get("altitude"))
            self.assertTrue(self.mission.check_waypoint())
            self.assertEqual(self.vehicle.commands.next, 1)
