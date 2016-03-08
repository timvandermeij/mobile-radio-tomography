import unittest
from mock import patch, call, MagicMock
from ..settings import Arguments

class TestDistanceSensorPhysical(unittest.TestCase):
    def setUp(self):
        # We need to mock the RPi.GPIO module as it is only available
        # on Raspberry Pi devices and these tests run on a PC.
        self.rpi_gpio_mock = MagicMock()
        modules = {
            'RPi': self.rpi_gpio_mock,
            'RPi.GPIO': self.rpi_gpio_mock.GPIO
        }

        self.patcher = patch.dict('sys.modules', modules)
        self.patcher.start()
        from ..environment import Environment
        from ..distance.Distance_Sensor_Physical import Distance_Sensor_Physical
        arguments = Arguments("settings.json", [
            "--sensors", "0", "--no-infrared-sensor"
        ])
        self.settings = arguments.get_settings("distance_sensor_physical")
        environment = Environment.setup(arguments, simulated=False)
        self.distance_sensor = environment.get_distance_sensors()[0]

    def tearDown(self):
        self.patcher.stop()

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
