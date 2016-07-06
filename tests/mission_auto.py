# Core imports
import time
from mock import patch

# Library imports
from dronekit import LocationLocal, LocationGlobalRelative

# Package imports
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..mission.Mission import Mission
from ..mission.Mission_Auto import Mission_Auto
from environment import EnvironmentTestCase

class TestMissionAuto(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle", "--geometry-class", "Geometry"
        ], use_infrared_sensor=False)

        super(TestMissionAuto, self).setUp()

        self.settings = self.arguments.get_settings("mission")
        self.mission = Mission_Auto(self.environment, self.settings)

        with patch("sys.stdout"):
            self.mission.setup()

    def test_get_points(self):
        # Verify that the interface requires subclasses to implement
        # the `get_points()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.get_points()

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

    def test_display(self):
        with patch.object(time, "sleep") as sleep_mock:
            with patch.object(Mission, "check_mission") as check_mission_mock:
                self.mission.display()

                # The method must wait for a period of time before checking the
                # mission's commands to ensure that output is displayed cleanly.
                sleep_mock.assert_any_call(self.settings.get("mission_delay"))
                check_mission_mock.assert_called_once_with()

    def test_step(self):
        # The `step` method does not do anything, not even raising exceptions.
        self.mission.step()
