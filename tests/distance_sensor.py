import math
from environment import EnvironmentTestCase

class TestDistanceSensor(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([], simulated=False, distance_sensors=[45.0],
                                use_infrared_sensor=False)

        super(TestDistanceSensor, self).setUp()

        self.environment._sensor_class = "Distance_Sensor"
        self.distance_sensor = self.environment.get_distance_sensors()[0]

    def test_initialization(self):
        self.assertEqual(self.distance_sensor.environment, self.environment)
        self.assertEqual(self.distance_sensor.id, 0)
        self.assertEqual(self.distance_sensor.angle, 45.0)

        with self.assertRaises(NotImplementedError):
            self.distance_sensor.get_distance()

    def test_get_angle(self):
        self.assertEqual(self.distance_sensor.get_angle(math.pi), 1.75*math.pi)
        self.assertEqual(self.distance_sensor.get_angle(), 0.75*math.pi)

    def test_get_pitch(self):
        self.assertEqual(self.distance_sensor.get_pitch(1.5*math.pi), 0.5*math.pi)
        self.assertEqual(self.distance_sensor.get_pitch(), 0.0)
