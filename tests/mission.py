# Core imports
import math
import time
from mock import call, patch, MagicMock, PropertyMock

# Library imports
from dronekit import VehicleMode, LocationGlobal, LocationGlobalRelative

# Package imports
from ..environment.Environment import Environment
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..mission.Mission import Mission
from ..mission.Mission_Calibrate import Mission_Calibrate
from ..trajectory.Memory_Map import Memory_Map
from ..trajectory.Servo import Servo
from ..vehicle.Mock_Vehicle import Mock_Vehicle, MockAttitude
from environment import EnvironmentTestCase

class TestMission(EnvironmentTestCase):
    def setUp(self):
        # These tests can only be run with the Mock_Vehicle.
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle"
        ], use_infrared_sensor=False)

        super(TestMission, self).setUp()

        self.vehicle = self.environment.get_vehicle()

        self.settings = self.arguments.get_settings("mission")
        self.mission = Mission(self.environment, self.settings)

        with patch("sys.stdout"):
            self.mission.setup()

    def test_create(self):
        # The method must return an object of the type set in the
        # `mission_class` setting.
        self.settings.set("mission_class", "Mission_Calibrate")
        mission = Mission.create(self.environment, self.arguments)
        self.assertIsInstance(mission, Mission_Calibrate)

    def test_setup(self):
        self.assertEqual(self.mission.size, self.settings.get("space_size"))
        self.assertEqual(self.mission.resolution, self.settings.get("resolution"))
        self.assertEqual(self.mission.padding, self.settings.get("padding"))
        self.assertEqual(self.mission.altitude, self.settings.get("altitude"))
        self.assertEqual(self.mission.speed, self.settings.get("speed"))
        self.assertEqual(self.mission.closeness, self.settings.get("closeness"))
        self.assertEqual(self.mission.farness, self.settings.get("farness"))
        self.assertIsInstance(self.mission.memory_map, Memory_Map)

    def test_distance_to_current_waypoint(self):
        self.assertIsNone(self.mission.distance_to_current_waypoint())

    def test_distance_to_current_waypoint_spherical(self):
        with patch.object(self.environment, "_geometry", new=Geometry_Spherical()):
            # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
            home_loc = LocationGlobal(0.0, 0.0, 0.0)
            loc = self.mission.geometry.get_location_meters(home_loc, 3.0, 4.0)
            self.vehicle.add_waypoint(loc)
            self.assertAlmostEqual(self.mission.distance_to_current_waypoint(),
                                   5.0, delta=0.02)

    def test_display(self):
        # Verify that the interface requires subclasses to implement
        # the `display()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.display()

    def test_clear_mission(self):
        with patch.object(self.mission, "vehicle", spec=Mock_Vehicle) as vehicle_mock:
            with patch("sys.stdout"):
                self.mission.clear_mission()
                vehicle_mock.clear_waypoints.assert_called_once_with()
                vehicle_mock.update_mission.assert_called_once_with()

    def test_check_mission(self):
        config = {
            "spec": Geometry_Spherical,
            "set_home_location.side_effect": TypeError
        }
        with patch.object(self.mission, "geometry", **config) as geometry_mock:
            with patch("sys.stdout"):
                loc = LocationGlobal(0.1, 2.3, 4.5)
                self.vehicle.home_location = loc
                self.mission.check_mission()
                self.assertEqual(geometry_mock.set_home_location.call_count, 1)
                args = geometry_mock.set_home_location.call_args[0]
                self.assertEqual(args[0], loc)

    def test_get_waypoints(self):
        # The waypoints list must be empty by default.
        self.assertEqual(self.mission.get_waypoints(), [])

    def test_get_home_location(self):
        # The home location of the vehicle must be returned.
        self.assertEqual(self.mission.get_home_location(),
                         self.vehicle.home_location)

    def test_arm_and_takeoff(self):
        with patch("sys.stdout"):
            with patch.object(Mock_Vehicle, "check_arming", return_value=False):
                # The method must raise an exception when the vehicle is not 
                # ready to be armed.
                with self.assertRaises(RuntimeError):
                    self.mission.arm_and_takeoff()

            params = {
                "spec": Mock_Vehicle,
                "check_arming.return_value": True,
                "simple_takeoff.return_value": False
            }
            with patch.object(self.mission, "vehicle", **params) as vehicle_mock:
                armed_mock = PropertyMock(side_effect=[False, False, True])
                type(vehicle_mock).armed = armed_mock

                with patch.object(time, "sleep") as sleep_mock:
                    # A ground vehicle that does not take off should have the 
                    # appropriate calls.
                    self.mission.arm_and_takeoff()
                    armed_mock.assert_has_calls([call(True), call(), call()])
                    sleep_mock.assert_any_call(1)
                    self.assertEqual(vehicle_mock.speed, self.mission.speed)

            alt = self.settings.get("altitude")
            undershoot = self.settings.get("altitude_undershoot")
            loc_ground = LocationGlobalRelative(0.0, 0.0, 0.0)
            loc_under = LocationGlobalRelative(0.0, 0.0, undershoot * alt - 0.5)
            loc_takeoff = LocationGlobalRelative(0.0, 0.0, alt)
            locs = [loc_ground, loc_ground, loc_under, loc_under, loc_takeoff]

            global_relative_frame_mock = PropertyMock(side_effect=locs)
            location_mock = MagicMock()
            type(location_mock).global_relative_frame = global_relative_frame_mock
            params = {
                "spec": Mock_Vehicle,
                "check_arming.return_value": True,
                "simple_takeoff.return_value": True,
                "location": location_mock
            }
            with patch.object(self.mission, "vehicle", **params) as vehicle_mock:
                armed_mock = PropertyMock(side_effect=[False, True])
                type(vehicle_mock).armed = armed_mock

                with patch.object(time, "sleep") as sleep_mock:
                    # A flying vehicle that takes off has the correct calls.
                    self.mission.arm_and_takeoff()
                    self.assertEqual(global_relative_frame_mock.call_count, 5)
                    self.assertEqual(sleep_mock.call_count, 2)

    def test_start(self):
        # Verify that the interface requires subclasses to implement
        # the `start()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.start()

    def test_stop(self):
        # The vehicle must be disarmed.
        self.mission.stop()
        self.assertFalse(self.vehicle.armed)

    def test_step(self):
        # Verify that the interface requires subclasses to implement
        # the `step()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.step()

    def test_check_sensor_distance(self):
        # The method must exit the program if it detects that the vehicle is 
        # inside another object.
        with self.assertRaises(SystemExit):
            with patch("sys.stdout"):
                self.mission.check_sensor_distance(0.0, 0.0, 0.0)

        # The method must raise an exception if the vehicle is too close to an 
        # object, and stop the vehicle.
        self.vehicle.mode = VehicleMode("AUTO")
        self.vehicle.speed = 5.0
        with self.assertRaises(RuntimeError):
            self.mission.check_sensor_distance(self.settings.get("closeness"),
                                               0.0, 0.0)
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.assertEqual(self.vehicle.speed, 0.0)

        # If the sensor distance is within the farness, then the method must 
        # return `True`.
        farness = self.settings.get("farness")
        self.assertTrue(self.mission.check_sensor_distance(farness-1, 0.0, 0.0))

        # If the sensor distance is outside the farness, then the method must 
        # return `False`.
        self.assertFalse(self.mission.check_sensor_distance(farness+1, 0.0, 0.0))

    def test_check_waypoint(self):
        # The method must return `True` by default.
        self.assertTrue(self.mission.check_waypoint())

    def test_get_space_size(self):
        # The space size of the network must be returned.
        self.assertEqual(self.mission.get_space_size(),
                         self.settings.get("space_size"))

    def test_get_memory_map(self):
        # The return value must be a `Memory_Map` object.
        self.assertIsInstance(self.mission.get_memory_map(), Memory_Map)
        self.assertEqual(self.mission.get_memory_map(), self.mission.memory_map)

    def test_send_global_velocity(self):
        # The vehicle's velocity must be set as a list.
        self.mission.send_global_velocity(1, 2, 3)
        self.assertEqual(self.vehicle.velocity, [1, 2, 3])

    def test_get_new_yaw(self):
        self.assertEqual(self.mission._get_new_yaw(90, False), 0.5*math.pi)
        self.vehicle.attitude = MockAttitude(0.0, math.pi, 0.0, self.vehicle)
        self.assertEqual(self.mission._get_new_yaw(45, True), 1.25*math.pi)

    @patch.object(Mock_Vehicle, "set_yaw")
    def test_set_yaw(self, set_yaw_mock):
        self.mission.set_yaw(90, direction=1)
        set_yaw_mock.assert_called_once_with(90, False, 1)

        set_yaw_mock.reset_mock()
        self.vehicle.attitude = MockAttitude(0.0, 0.5*math.pi, 0.0, self.vehicle)
        self.mission.set_yaw(45, relative=True)
        set_yaw_mock.assert_called_once_with(45, True, 1)

        set_yaw_mock.reset_mock()
        self.mission.set_yaw(45)
        set_yaw_mock.assert_called_once_with(45, False, -1)

    @patch.object(Mock_Vehicle, "set_yaw")
    @patch.object(Mock_Vehicle, "set_servo")
    def test_set_sensor_yaw(self, set_servo_mock, set_yaw_mock):
        with patch.object(Environment, "get_servos", return_value=[]) as get_servos_mock:
            self.mission.set_sensor_yaw(45, relative=False, direction=1)
            get_servos_mock.assert_called_once_with()
            set_yaw_mock.assert_called_once_with(45, False, 1)
            set_servo_mock.assert_not_called()

        set_yaw_mock.reset_mock()
        servo = Servo(7, (0, 360), (0, 2000))
        self.vehicle.attitude = MockAttitude(0.0, math.pi, 0.0, self.vehicle)
        with patch.object(Environment, "get_servos", return_value=[servo]):
            self.mission.set_sensor_yaw(180, relative=False, direction=1)
            set_servo_mock.assert_called_once_with(servo, 500)
            set_yaw_mock.assert_not_called()

        set_servo_mock.reset_mock()
        set_yaw_mock.reset_mock()
        servo = Servo(7, (180, 360), (1000, 2000))
        with patch.object(Environment, "get_servos", return_value=[servo]):
            self.mission.set_sensor_yaw(180, relative=False, direction=1)
            set_yaw_mock.assert_called_once_with(180, False, 1)
            set_servo_mock.assert_not_called()

    def test_return_to_launch(self):
        # The vehicle mode must be set to RTL (return to launch).
        with patch("sys.stdout"):
            self.mission.return_to_launch()

        self.assertEqual(self.vehicle.mode, VehicleMode("RTL"))
