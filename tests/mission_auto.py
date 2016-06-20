# Core imports
import time
from mock import patch

# Package imports
from ..mission.Mission import Mission
from ..mission.Mission_Auto import Mission_Auto
from environment import EnvironmentTestCase

class TestMissionAuto(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([], use_infrared_sensor=False)

        super(TestMissionAuto, self).setUp()

        self.settings = self.arguments.get_settings("mission")
        self.mission = Mission_Auto(self.environment, self.settings)

    def test_get_points(self):
        # Verify that the interface requires subclasses to implement
        # the `get_points()` method.
        with self.assertRaises(NotImplementedError):
            self.mission.get_points()

    def test_display(self):
        with patch.object(time, "sleep") as sleep_mock:
            with patch.object(Mission, "check_mission") as check_mission_mock:
                self.mission.display()

                # The method must wait for a period of time before checking the
                # mission's commands to ensure that output is displayed cleanly.
                sleep_mock.assert_called_once_with(self.settings.get("mission_delay"))
                check_mission_mock.assert_called_once_with()
