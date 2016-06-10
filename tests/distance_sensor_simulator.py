import math
from dronekit import LocationGlobalRelative
from mock import call, MagicMock, Mock
from environment import EnvironmentTestCase

class TestDistanceSensorSimulator(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--altitude-margin", "2.0", "--angle-margin", "2.5",
            "--maximum-distance", "2000"
        ], simulated=True, distance_sensors=[0.0], use_infrared_sensor=False)

        super(TestDistanceSensorSimulator, self).setUp()

        self.settings = self.arguments.get_settings("distance_sensor_simulator")
        self.distance_sensor = self.environment.get_distance_sensors()[0]

    def test_initialization(self):
        self.assertEqual(self.distance_sensor.settings, self.settings)
        self.assertEqual(self.distance_sensor.altitude_margin, 2.0)
        self.assertEqual(self.distance_sensor.angle_margin, 2.5 * math.pi/180)
        self.assertEqual(self.distance_sensor.maximum_distance, 2000)
        self.assertIsNone(self.distance_sensor.current_edge)
        self.assertEqual(self.distance_sensor.current_object, -1)
        self.assertEqual(self.distance_sensor.current_face, -1)

    def check_draw_current_edge_calls(self, *args):
        """
        Check that `draw_current_edge` uses specific parts of the current edge
        to retrieve a memory map index and annotate the edge in matplotlib.

        This is a helper function for other test cases, not a test itself.
        """

        plt_mock = MagicMock()
        number_of_index_calls = max(1, len(args))
        index_mocks = [Mock()] * number_of_index_calls
        methods = {
            "get_xy_index.side_effect": index_mocks
        }
        memory_map_mock = MagicMock(**methods)
        self.distance_sensor.draw_current_edge(plt_mock, memory_map_mock)

        if args:
            index_calls = [
                call(self.distance_sensor.current_edge[idx]) for idx in args
            ]
        else:
            index_calls = [call(self.distance_sensor.current_edge)]

        self.assertEqual(memory_map_mock.get_xy_index.call_count,
                         number_of_index_calls)
        memory_map_mock.get_xy_index.assert_has_calls(index_calls)

        self.assertEqual(plt_mock.annotate.call_count, 1)
        args = plt_mock.annotate.call_args[0]
        self.assertEqual(args[0], "D")
        self.assertEqual(args[1], index_mocks[0])
        self.assertEqual(args[2], index_mocks[-1])

    def test_get_distance(self):
        self.environment._load_objects()

        # No arguments
        self.assertEqual(self.distance_sensor.get_distance(), 60.0)
        self.assertIsInstance(self.distance_sensor.current_edge, tuple)
        self.assertEqual(self.distance_sensor.get_current_edge(),
                         self.distance_sensor.current_edge)

        # Other direction
        self.assertEqual(self.distance_sensor.get_distance(yaw=math.pi), 60.0)
        self.assertIsInstance(self.distance_sensor.current_edge, tuple)
        self.check_draw_current_edge_calls(0, 1)

        # Non-straight angle
        self.assertTrue(self.distance_sensor.get_distance(yaw=0.33*math.pi) < 2000)
        self.assertIsInstance(self.distance_sensor.current_edge, tuple)

        # Inside an object
        loc = self.environment.get_location(100, 0, 5)
        self.assertEqual(self.distance_sensor.get_distance(location=loc), 0.0)

    def test_get_distance_circle(self):
        self.environment._load_objects()

        loc = self.environment.get_location(0, -10, 0)
        self.assertEqual(self.distance_sensor.get_distance(location=loc), 37.5)
        self.assertIsInstance(self.distance_sensor.current_edge,
                              LocationGlobalRelative)
        self.check_draw_current_edge_calls()

    def test_get_distance_scenefile(self):
        self.environment._load_objects(scenefile="tests/vrml/castle.wrl")
        self.distance_sensor.get_distance()
        self.check_draw_current_edge_calls(-1)

    def test_get_distance_other(self):
        self.environment.objects = [None]
        with self.assertRaises(ValueError):
            self.distance_sensor.get_distance()
