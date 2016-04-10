from mock import patch
from dronekit import LocationLocal
from ..trajectory.Mission import Mission_XBee
from ..vehicle.Robot_Vehicle import Robot_State
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator
from ..zigbee.XBee_Packet import XBee_Packet
from environment import EnvironmentTestCase

class TestMissionXBee(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Robot_Vehicle_Arduino",
            "--geometry-class", "Geometry",
            "--space-size", "10", "--closeness", "0",
            "--xbee-synchronization", "--number-of-sensors", "2"
        ], use_infrared_sensor=False)

        super(TestMissionXBee, self).setUp()

        self.vehicle = self.environment.get_vehicle()

        settings = self.arguments.get_settings("mission")
        self.mission = Mission_XBee(self.environment, settings)
        self.xbee = self.environment.get_xbee_sensor()

    def test_setup(self):
        with patch('sys.stdout'):
            self.mission.setup()

        packet_actions = self.environment._packet_callbacks.keys()
        self.assertIn("waypoint_clear", packet_actions)
        self.assertIn("waypoint_add", packet_actions)
        self.assertIn("waypoint_done", packet_actions)
        self.assertFalse(self.mission._waypoints_complete)
        self.assertEqual(self.mission._next_index, 0)

    def _send_waypoint_add(self, index, latitude, longitude):
        packet = XBee_Packet()
        packet.set("specification", "waypoint_add")
        packet.set("index", index)
        packet.set("latitude", latitude)
        packet.set("longitude", longitude)
        packet.set("altitude", 0.0)
        packet.set("wait_id", 0)
        packet.set("to_id", self.xbee.id)

        with patch('sys.stdout'):
            self.environment.receive_packet(packet)

    @patch.object(XBee_Sensor_Simulator, "enqueue")
    def test_clear(self, enqueue_mock):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 4.0, 2.0)
        enqueue_mock.reset_mock()

        packet = XBee_Packet()
        packet.set("specification", "waypoint_clear")
        packet.set("to_id", self.xbee.id)

        with patch('sys.stdout'):
            self.environment.receive_packet(packet)

        self.assertEqual(enqueue_mock.call_count, 1)
        args, kwargs = enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], XBee_Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 0,
            "sensor_id": self.xbee.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.vehicle._waypoints, [])

    @patch.object(XBee_Sensor_Simulator, "enqueue")
    def test_add(self, enqueue_mock):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 1.0, 4.0)

        self.assertEqual(enqueue_mock.call_count, 1)
        args, kwargs = enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], XBee_Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 1,
            "sensor_id": self.xbee.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.vehicle._waypoints, [(1, 4), None])

    @patch.object(XBee_Sensor_Simulator, "enqueue")
    def test_add_wrong_index(self, enqueue_mock):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(42, 3.0, 2.0)

        self.assertEqual(enqueue_mock.call_count, 1)
        args, kwargs = enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], XBee_Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 0,
            "sensor_id": self.xbee.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.vehicle._waypoints, [])

    @patch.object(XBee_Sensor_Simulator, "enqueue")
    def test_done(self, enqueue_mock):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 1.0, 0.0)
        self._send_waypoint_add(1, 2.0, 0.0)
        self._send_waypoint_add(2, 3.0, 0.0)
        self._send_waypoint_add(3, 4.0, 0.0)

        packet = XBee_Packet()
        packet.set("specification", "waypoint_done")
        packet.set("to_id", self.xbee.id)

        with patch('sys.stdout'):
            self.environment.receive_packet(packet)

        self.assertTrue(self.mission._waypoints_complete)
        self.assertEqual(self.vehicle._waypoints, [
            (1, 0), None, (2, 0), None, (3, 0), None, (4, 0), None
        ])

        with patch('sys.stdout'):
            self.mission.arm_and_takeoff()
            self.mission.start()

        self.assertEqual(self.vehicle.mode.name, "AUTO")
        self.assertTrue(self.vehicle.armed)

        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(1, 0, 0))
        self.assertFalse(self.vehicle.is_wait())
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())

        self.vehicle._location = (1, 0)
        self.vehicle._state = Robot_State("intersection")
        self.vehicle._check_state()
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())

        self.assertEqual(self.vehicle._current_waypoint, 1)
        self.assertEqual(self.vehicle.get_waypoint(), None)
        self.assertTrue(self.vehicle.is_wait())

        # The mission waits for the other XBee to send a valid location packet.
        self.assertTrue(self.environment.location_valid(other_valid=True, other_id=self.xbee.id + 1))
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())

        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(2, 0, 0))
        self.assertFalse(self.vehicle.is_wait())
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 2)
        self.assertEqual(self.vehicle._state.name, "move")
