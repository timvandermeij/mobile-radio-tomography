import unittest
from mock import patch, call, MagicMock
from ..settings import Arguments

class TestLocationLineFollowerRaspberryPi(unittest.TestCase):
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
        from ..location.Line_Follower import Line_Follower_Direction

        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP
        
        arguments = Arguments("settings.json", [])
        self.settings = arguments.get_settings("line_follower")

    def tearDown(self):
        self.patcher.stop()

    def test_initialization(self):
        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        mock_callback = MagicMock()
        line_follower = Line_Follower_Raspberry_Pi(self.location, self.direction,
                                                   mock_callback, self.settings)

        # Verify that the correct sensors are set.
        self.assertEqual(line_follower._sensors, self.settings.get("led_pins"))

        # Warnings must be disabled.
        line_follower.gpio.setwarnings.assert_called_once_with(False)

        # Board numbering has to be used.
        line_follower.gpio.setmode.assert_called_once_with(line_follower.gpio.BOARD)

        # The input pins have to be set.
        sensors = self.settings.get("led_pins")
        line_follower.gpio.setup.assert_has_calls([
            call(sensor, line_follower.gpio.IN) for sensor in sensors
        ])

    def test_read(self):
        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        mock_callback = MagicMock()
        line_follower = Line_Follower_Raspberry_Pi(self.location, self.direction,
                                                   mock_callback, self.settings)
        sensors = self.settings.get("led_pins")
        sensor_values = line_follower.read()

        self.assertIs(type(sensor_values), list)
        line_follower.gpio.input.assert_has_calls([
            call(sensor) for sensor in [sensors[0], sensors[2], sensors[3], sensors[5]]
        ])
