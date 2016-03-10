import os
import pty
import itertools
from mock import patch
from dronekit import LocationLocal
from ..environment.Environment import Environment
from ..trajectory.Mission import Mission_Cycle
from ..vehicle.Robot_Vehicle import Robot_State
from ..settings import Arguments
from geometry import LocationTestCase
from settings import SettingsTestCase

class TestMissionCycle(LocationTestCase, SettingsTestCase):
    def setUp(self):
        super(TestMissionCycle, self).setUp()

        # Create a virtual serial port.
        master, slave = pty.openpty()
        self.master = os.fdopen(master)
        self.port = os.ttyname(slave)

        self.arguments = Arguments("settings.json", [
            "--vehicle-class", "Robot_Vehicle_Arduino", "--space-size", "3",
            "--serial-device", self.port, "--serial-flow-control",
            "--no-infrared-sensor"
        ])
        self.environment = Environment.setup(self.arguments, geometry_class="Geometry", simulated=True)
        self.vehicle = self.environment.get_vehicle()

        settings = self.arguments.get_settings("mission")
        self.mission = Mission_Cycle(self.environment, settings)

    def tearDown(self):
        super(TestMissionCycle, self).tearDown()
        self.vehicle.deactivate()

    def test_setup(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self.assertEqual(self.vehicle.location, LocationLocal(0, 0, 0))
        self.assertEqual(self.mission.id, 0)
        self.assertEqual(self.mission.size, 3)
        self.assertFalse(self.mission.done)
        self.assertIsNone(self.mission.current_waypoint)
        self.assertIsInstance(self.mission.waypoints, itertools.chain)
        waypoints = list(self.mission.waypoints)
        self.assertEqual(waypoints, [
            (1,0), (2,0),
            (1,0), (0,0), (0,1), (0,2),
            (0,1), (0,0),
            (0,1), (0,2), (1,2), (2,2),
            (1,2), (0,2),
            (1,2), (2,2), (2,1), (2,0),
            (2,1), (2,2),
            (2,1), (2,0), (1,0), (0,0)
        ])

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

    def test_step(self):
        with patch('sys.stdout'):
            self.mission.setup()
            self.mission.arm_and_takeoff()
            self.mission.start()

        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.assertTrue(self.vehicle.armed)
        self.assertEqual(self.vehicle._waypoints, [])
        self.assertEqual(self.vehicle.get_waypoint(), None)

        self.mission.step()
        self.assertEqual(self.mission.current_waypoint, (1,0))
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(1,0)])
        self.assertEqual(self.vehicle._state.name, "move")
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(1,0,0))
        self.assertNotEqual(self.master.readline(), "")

        self.vehicle._location = (1,0)
        self.vehicle._state = Robot_State("intersection")
        self.mission.step()
        self.assertEqual(self.mission.current_waypoint, (2,0))
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._waypoints, [(2,0)])
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(2,0,0))
