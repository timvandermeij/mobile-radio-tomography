import itertools
from mock import patch
from dronekit import LocationLocal
from ..location.Line_Follower import Line_Follower
from ..trajectory.Mission import Mission_Cycle
from ..vehicle.Robot_Vehicle import Robot_State
from environment import EnvironmentTestCase

class TestMissionCycle(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Robot_Vehicle_Arduino",
            "--geometry-class", "Geometry", "--space-size", "3",
            "--number-of-sensors", "2", "--closeness", "0",
            "--xbee-synchronization"
        ], use_infrared_sensor=False)

        super(TestMissionCycle, self).setUp()

        self.vehicle = self.environment.get_vehicle()

        settings = self.arguments.get_settings("mission")
        self.mission = Mission_Cycle(self.environment, settings)
        self.xbee = self.environment.get_xbee_sensor()
        self.first_waypoints = [
            (1,0), (2,0),
            (1,0), (0,0), (0,1), (0,2),
            (0,1), (0,0),
            (0,1), (0,2), (1,2), (2,2),
            (1,2), (0,2),
            (1,2), (2,2), (2,1), (2,0),
            (2,1), (2,2),
            (2,1), (2,0), (1,0), (0,0)
        ]

    def test_setup(self):
        with patch('sys.stdout'):
            self.mission.setup()

        # Check first vehicle's state.
        self.assertEqual(self.vehicle.location, LocationLocal(0, 0, 0))
        self.assertEqual(self.mission.id, 0)
        self.assertEqual(self.mission.size, 3)
        self.assertIsInstance(self.mission.waypoints, itertools.chain)
        waypoints = list(self.mission.waypoints)
        self.assertEqual(waypoints, self.first_waypoints)

        # Check second vehicle's state.
        self.vehicle._location = (0,2)
        with patch('sys.stdout'):
            self.mission.setup()

        waypoints = list(self.mission.waypoints)
        self.assertEqual(waypoints, [
            (1,2), (2,2),
            (2,2), (2,2), (2,2), (2,2),
            (2,1), (2,0),
            (2,0), (2,0), (2,0), (2,0),
            (1,0), (0,0),
            (0,0), (0,0), (0,0), (0,0),
            (0,1), (0,2),
            (0,2), (0,2), (0,2), (0,2)
        ])

    @patch.object(Line_Follower, "_loop")
    def test_mission(self, line_follower_arduino_read_mock):
        with patch('sys.stdout'):
            self.mission.setup()
            self.mission.arm_and_takeoff()
            self.mission.start()

        self.assertEqual(self.vehicle.mode.name, "AUTO")
        self.assertTrue(self.vehicle.armed)
        self.assertEqual(self.vehicle._waypoints, list(itertools.chain(*[[waypoint, None] for waypoint in self.first_waypoints])))
        self.assertEqual(self.vehicle.get_waypoint(), None)

        with patch('sys.stdout'):
            self.mission.check_waypoint()

        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._state.name, "move")
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(1,0,0))
        self.assertNotEqual(self._ttl_device.readline(), "")

        self.vehicle._location = (1,0)
        self.vehicle._state = Robot_State("intersection")
        with patch('sys.stdout'):
            self.mission.check_waypoint()

        # The mission waits for the other XBee to send a valid location packet.
        self.vehicle._check_state()
        self.assertEqual(self.vehicle.get_waypoint(), None)
        self.assertTrue(self.environment.location_valid(other_valid=True, other_id=self.xbee.id + 1, other_index=1))

        with patch('sys.stdout'):
            self.mission.check_waypoint()

        self.vehicle._check_state()
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(2,0,0))
