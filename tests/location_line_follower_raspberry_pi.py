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
        self.settings = arguments.get_settings("line_follower_raspberry_pi")

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

    def test_activate(self):
        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        mock_callback = MagicMock()
        line_follower = Line_Follower_Raspberry_Pi(self.location, self.direction,
                                                   mock_callback, self.settings)
        emitter_pin = self.settings.get("emitter_pin")

        line_follower.activate()
        line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, line_follower.gpio.OUT)
        ])
        line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, True)
        ])

    def test_deactivate(self):
        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        mock_callback = MagicMock()
        line_follower = Line_Follower_Raspberry_Pi(self.location, self.direction,
                                                   mock_callback, self.settings)
        emitter_pin = self.settings.get("emitter_pin")

        line_follower.deactivate()
        line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, line_follower.gpio.OUT)
        ])
        line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, False)
        ])
