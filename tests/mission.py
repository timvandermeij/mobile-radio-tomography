# Core imports
from mock import patch

# Library imports
from dronekit import VehicleMode

# Package imports
from ..mission.Mission import Mission
from ..mission.Mission_Calibrate import Mission_Calibrate
from ..trajectory.Memory_Map import Memory_Map
from ..vehicle.Mock_Vehicle import Mock_Vehicle
from environment import EnvironmentTestCase

class TestMission(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([], use_infrared_sensor=False)

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

    def test_display(self):
        # Verify that the interface requires subclasses to implement
        # the `display()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.display()

    def test_get_waypoints(self):
        # The waypoints list must be empty by default.
        self.assertEqual(self.mission.get_waypoints(), [])

    def test_get_home_location(self):
        # The home location of the vehicle must be returned.
        self.assertEqual(self.mission.get_home_location(), self.vehicle.home_location)

    def test_arm_and_takeoff(self):
        with patch("sys.stdout"):
            with patch.object(Mock_Vehicle, "check_arming", return_value=False):
                # The method must raise an exception when the vehicle is not armed.
                with self.assertRaises(RuntimeError):
                    self.mission.arm_and_takeoff()

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

    def test_check_waypoint(self):
        # The method must return `True` by default.
        self.assertTrue(self.mission.check_waypoint())

    def test_get_space_size(self):
        # The space size of the network must be returned.
        self.assertEqual(self.mission.get_space_size(), self.settings.get("space_size"))

    def test_get_memory_map(self):
        # The return value must be a `Memory_Map` object.
        self.assertIsInstance(self.mission.get_memory_map(), Memory_Map)

    def test_send_global_velocity(self):
        # The vehicle's velocity must be set as a list.
        self.mission.send_global_velocity(1, 2, 3)
        self.assertEqual(self.vehicle.velocity, [1, 2, 3])

    def test_return_to_launch(self):
        # The vehicle mode must be set to RTL (return to launch).
        with patch("sys.stdout"):
            self.mission.return_to_launch()

        self.assertEqual(self.vehicle.mode, VehicleMode("RTL"))
