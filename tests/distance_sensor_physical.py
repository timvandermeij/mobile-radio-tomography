from mock import call
from environment import EnvironmentTestCase

class TestDistanceSensorPhysical(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([], simulated=False, distance_sensors=[0.0],
                                use_infrared_sensor=False)

        super(TestDistanceSensorPhysical, self).setUp()

        self.settings = self.arguments.get_settings("distance_sensor_physical")
        self.distance_sensor = self.environment.get_distance_sensors()[0]

    def test_initialization(self):
        # Warnings must be disabled.
        self.distance_sensor.gpio.setwarnings.assert_called_once_with(False)

        # Board numbering has to be used.
        self.distance_sensor.gpio.setmode.assert_called_once_with(
            self.distance_sensor.gpio.BOARD)

        # The input and output pins have to be set.
        self.distance_sensor.gpio.setup.assert_has_calls([
            call(self.settings.get("echo_pin"), self.distance_sensor.gpio.IN),
            call(self.settings.get("trigger_pin"), self.distance_sensor.gpio.OUT)
        ])

        # The trigger signal must be set to false.
        self.distance_sensor.gpio.output.assert_called_once_with(
            self.settings.get("trigger_pin"), False)

    def test_elapsed_time_triggers(self):
        self.distance_sensor.get_distance()

        # The starting trigger has to be created.
        self.distance_sensor.gpio.output.assert_has_calls([
            call(self.settings.get("trigger_pin"), True),
            call(self.settings.get("trigger_pin"), False)
        ])

        # The echo pin must be checked at least once.
        self.distance_sensor.gpio.input.assert_called_with(
            self.settings.get("echo_pin"))

    def test_elapsed_time_to_distance_conversion(self):
        elapsed_time = 5.153064012527466
        distance_meters = (elapsed_time * self.settings.get("speed_of_sound")) / 2
        
        correct = distance_meters / 100
        calculated = self.distance_sensor._convert_elapsed_time_to_distance(elapsed_time)

        self.assertEqual(calculated, correct)
