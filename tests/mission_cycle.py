import itertools
from mock import patch
from dronekit import LocationLocal
from ..environment.Environment import Environment
from ..trajectory.Mission import Mission_Cycle
from ..vehicle.Robot_Vehicle import Robot_State
from ..settings import Arguments
from core_thread_manager import ThreadableTestCase
from core_usb_manager import USBManagerTestCase
from geometry import LocationTestCase
from settings import SettingsTestCase

class TestMissionCycle(ThreadableTestCase, USBManagerTestCase, LocationTestCase, SettingsTestCase):
    def setUp(self):
        super(TestMissionCycle, self).setUp()

        self.arguments = Arguments("settings.json", [
            "--vehicle-class", "Robot_Vehicle_Arduino", "--space-size", "3",
            "--serial-flow-control", "--no-infrared-sensor"
        ])
        self.environment = Environment.setup(self.arguments, geometry_class="Geometry",
                                             usb_manager=self.usb_manager, simulated=True)
        self.vehicle = self.environment.get_vehicle()

        settings = self.arguments.get_settings("mission")
        self.mission = Mission_Cycle(self.environment, settings)

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
        # The mission waits for the other XBee to send a valid location packet.
        self.assertEqual(self.mission.current_waypoint, (1,0))
        self.assertTrue(self.environment.location_valid(other_valid=True))
        self.mission.step()
        self.assertEqual(self.mission.current_waypoint, (2,0))
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._waypoints, [(2,0)])
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(2,0,0))
