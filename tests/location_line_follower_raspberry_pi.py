from mock import patch, call, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..settings import Arguments
from core_thread_manager import ThreadableTestCase
from settings import SettingsTestCase

class TestLocationLineFollowerRaspberryPi(ThreadableTestCase, SettingsTestCase):
    def setUp(self):
        super(TestLocationLineFollowerRaspberryPi, self).setUp()

        # We need to mock the RPi.GPIO module as it is only available
        # on Raspberry Pi devices and these tests run on a PC.
        self.rpi_gpio_mock = MagicMock()
        modules = {
            'RPi': self.rpi_gpio_mock,
            'RPi.GPIO': self.rpi_gpio_mock.GPIO
        }

        self._rpi_patcher = patch.dict('sys.modules', modules)
        self._rpi_patcher.start()
        from ..location.Line_Follower import Line_Follower_Direction

        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP

        arguments = Arguments("settings.json", [])
        self.settings = arguments.get_settings("line_follower_raspberry_pi")

        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        self.mock_callback = MagicMock()
        self.thread_manager = Thread_Manager()
        self.line_follower = Line_Follower_Raspberry_Pi(
            self.location, self.direction, self.mock_callback, self.settings,
            self.thread_manager, None
        )

    def tearDown(self):
        super(TestLocationLineFollowerRaspberryPi, self).tearDown()
        self._rpi_patcher.stop()

    def test_initialization(self):
        # Verify that the correct sensors are set.
        self.assertEqual(self.line_follower._sensors, self.settings.get("led_pins"))

        # Warnings must be disabled.
        self.line_follower.gpio.setwarnings.assert_called_once_with(False)

        # Board numbering has to be used.
        self.line_follower.gpio.setmode.assert_called_once_with(self.line_follower.gpio.BOARD)

    def test_enable(self):
        emitter_pin = self.settings.get("emitter_pin")

        self.line_follower.enable()
        self.line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, self.line_follower.gpio.OUT)
        ])
        self.line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, True)
        ])

    def test_disable(self):
        emitter_pin = self.settings.get("emitter_pin")

        self.line_follower.disable()
        self.line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, self.line_follower.gpio.OUT)
        ])
        self.line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, False)
        ])
