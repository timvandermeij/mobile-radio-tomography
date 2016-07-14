from mock import patch
from dronekit import LocationLocal
from ..environment.Environment import Environment
from ..mission.Mission_RF_Sensor import Mission_RF_Sensor
from ..vehicle.Robot_Vehicle import Robot_State
from ..waypoint.Waypoint import Waypoint_Type
from ..zigbee.Packet import Packet
from ..zigbee.RF_Sensor import RF_Sensor
from environment import EnvironmentTestCase

class TestMissionRFSensor(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Robot_Vehicle_Arduino",
            "--geometry-class", "Geometry",
            "--space-size", "10", "--closeness", "0",
            "--rf-sensor-synchronization", "--number-of-sensors", "2"
        ], use_infrared_sensor=False)

        super(TestMissionRFSensor, self).setUp()

        self.vehicle = self.environment.get_vehicle()

        settings = self.arguments.get_settings("mission")
        self.mission = Mission_RF_Sensor(self.environment, settings)
        self.rf_sensor = self.environment.get_rf_sensor()

        # Mock the enqueue method of the RF sensor so that we can see which 
        # acknowledgement packets the mission attempts to send.
        self.enqueue_patcher = patch.object(RF_Sensor, "enqueue")
        self.enqueue_mock = self.enqueue_patcher.start()

    def tearDown(self):
        super(TestMissionRFSensor, self).tearDown()
        self.enqueue_patcher.stop()

    def test_setup(self):
        with patch('sys.stdout'):
            self.mission.setup()

        packet_actions = self.environment._packet_callbacks.keys()
        self.assertIn("waypoint_clear", packet_actions)
        self.assertIn("waypoint_add", packet_actions)
        self.assertIn("waypoint_done", packet_actions)
        self.assertFalse(self.mission.waypoints_complete)
        self.assertEqual(self.mission.next_index, 0)

    @patch.object(Environment, "get_rf_sensor", return_value=None)
    def test_setup_no_rf_sensor(self, get_rf_sensor_mock):
        with self.assertRaises(ValueError):
            with patch('sys.stdout'):
                self.mission.setup()

        get_rf_sensor_mock.assert_called_once_with()

    def test_get_points(self):
        # An RF sensor mission has no predetermined AUTO points.
        self.assertEqual(self.mission.get_points(), [])

    def test_add_commands(self):
        with self.assertRaises(RuntimeError):
            self.mission.add_commands()

    def test_arm_and_takeoff(self):
        with patch('sys.stdout'):
            self.mission.setup()

            # Starting arming checks will wait until waypoints are complete.
            with patch('time.sleep', side_effect=RuntimeError('sleep')):
                with self.assertRaises(RuntimeError):
                    self.mission.arm_and_takeoff()

    def _send_waypoint_add(self, index, latitude, longitude, **kwargs):
        # The default values of the fields.
        fields = {
            "altitude": 0.0,
            "type": Waypoint_Type.WAIT,
            "wait_id": 0,
            "wait_count": 1,
            "id_offset": 0
        }
        fields.update(kwargs)

        packet = Packet()
        packet.set("specification", "waypoint_add")
        packet.set("index", index)
        packet.set("latitude", latitude)
        packet.set("longitude", longitude)
        packet.set("altitude", fields["altitude"])
        packet.set("type", int(fields["type"]))
        packet.set("wait_id", fields["wait_id"])
        packet.set("wait_count", fields["wait_count"])
        packet.set("to_id", self.rf_sensor.id + fields["id_offset"])

        with patch('sys.stdout'):
            self.environment.receive_packet(packet)

    def _send_packet(self, specification, id_offset=0):
        packet = Packet()
        packet.set("specification", specification)
        packet.set("to_id", self.rf_sensor.id + id_offset)

        with patch('sys.stdout'):
            self.environment.receive_packet(packet)

    def test_clear_waypoints(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 4.0, 2.0)

        # Packets not meant for the current RF sensor are ignored.
        self._send_packet("waypoint_clear", id_offset=42)

        self.assertEqual(self.mission.next_index, 1)

        self.enqueue_mock.reset_mock()

        self._send_packet("waypoint_clear")

        self.assertEqual(self.enqueue_mock.call_count, 1)
        args, kwargs = self.enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 0,
            "sensor_id": self.rf_sensor.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.mission.next_index, 0)
        self.assertEqual(self.vehicle._waypoints, [])
        self.assertIsNone(self.mission._point)
        self.assertFalse(self.mission._waypoints_complete)

    def test_add_waypoint(self):
        with patch('sys.stdout'):
            self.mission.setup()

        # Packets not meant for the current RF sensor are ignored.
        self._send_waypoint_add(0, 6.0, 5.0, id_offset=42)
        self.assertEqual(self.mission.next_index, 0)

        self.enqueue_mock.reset_mock()
        self._send_waypoint_add(0, 1.0, 4.0)

        self.assertEqual(self.enqueue_mock.call_count, 1)
        args, kwargs = self.enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 1,
            "sensor_id": self.rf_sensor.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.mission.next_index, 1)
        self.assertEqual(self.vehicle._waypoints, [(1, 4), None])

    def test_add_waypoint_wait_count(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 0.0, 4.0, wait_count=4)

        self.assertEqual(self.enqueue_mock.call_count, 1)
        args, kwargs = self.enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 1,
            "sensor_id": self.rf_sensor.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.mission.next_index, 1)
        self.assertEqual(self.vehicle._waypoints, [
            (0, 1), None, (0, 2), None, (0, 3), None, (0, 4), None
        ])

    def test_add_waypoint_wrong_index(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(42, 3.0, 2.0)

        self.assertEqual(self.enqueue_mock.call_count, 1)
        args, kwargs = self.enqueue_mock.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], Packet)
        self.assertEqual(args[0].get_all(), {
            "specification": "waypoint_ack",
            "next_index": 0,
            "sensor_id": self.rf_sensor.id
        })
        self.assertEqual(kwargs, {"to": 0})

        self.assertEqual(self.mission.next_index, 0)
        self.assertEqual(self.vehicle._waypoints, [])

    def test_complete_waypoints(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 1.0, 0.0)
        self._send_waypoint_add(1, 2.0, 0.0, type=Waypoint_Type.PASS)
        self._send_waypoint_add(2, 3.0, 0.0)
        self._send_waypoint_add(3, 4.0, 0.0)

        # Packets not meant for us are ignored.
        self._send_packet("waypoint_done", id_offset=42)

        self.assertFalse(self.mission.waypoints_complete)

        self.enqueue_mock.reset_mock()
        self._send_packet("waypoint_done")

        # We do not send an acknowledgment (and request for next ID) when the 
        # waypoints are done.
        self.assertEqual(self.enqueue_mock.call_count, 0)

        self.assertTrue(self.mission.waypoints_complete)
        self.assertEqual(self.vehicle._waypoints, [
            (1, 0), None, (2, 0), (3, 0), None, (4, 0), None
        ])

    def test_interface_mission(self):
        with patch('sys.stdout'):
            self.mission.setup()

        self._send_waypoint_add(0, 1.0, 0.0)
        self._send_waypoint_add(1, 2.0, 0.0)

        self._send_packet("waypoint_done")

        with patch('sys.stdout'):
            self.mission.arm_and_takeoff()
            self.mission.start()

        self.assertTrue(self.mission.waypoints_complete)
        self.assertEqual(self.vehicle._waypoints, [(1, 0), None, (2, 0), None])

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

        # The mission waits at the waypoint, until the other RF sensor sends 
        # a valid location packet.
        self.assertEqual(self.vehicle._current_waypoint, 1)
        self.assertIsNone(self.vehicle.get_waypoint())
        self.assertTrue(self.vehicle.is_wait())

        other_id = self.rf_sensor.id + 1
        self.assertTrue(self.environment.location_valid())
        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=1))
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())

        self.assertEqual(self.vehicle.get_waypoint(), LocationLocal(2, 0, 0))
        self.assertFalse(self.vehicle.is_wait())
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 2)
        self.assertEqual(self.vehicle._state.name, "move")

        self.vehicle._location = (2, 0)
        self.vehicle._state = Robot_State("intersection")
        self.vehicle._check_state()
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())

        # The mission waits at the waypoint, until the other RF sensor sends 
        # a valid location packet.
        self.assertEqual(self.vehicle._current_waypoint, 3)
        self.assertIsNone(self.vehicle.get_waypoint())
        self.assertTrue(self.vehicle.is_wait())

        other_id = self.rf_sensor.id + 1
        self.assertTrue(self.environment.location_valid(other_valid=True,
                                                        other_id=other_id,
                                                        other_index=3))
        with patch('sys.stdout'):
            self.assertTrue(self.mission.check_waypoint())
