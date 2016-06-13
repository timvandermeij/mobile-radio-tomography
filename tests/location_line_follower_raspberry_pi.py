import sys
import time
from mock import patch, call, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..settings import Arguments
from core_thread_manager import ThreadableTestCase
from core_wiringpi import WiringPiTestCase
from settings import SettingsTestCase

class TestLocationLineFollowerRaspberryPi(ThreadableTestCase, SettingsTestCase,
                                          WiringPiTestCase):
    def setUp(self):
        self.set_rpi_patch(rpi_patch=True)

        super(TestLocationLineFollowerRaspberryPi, self).setUp()

        from ..location.Line_Follower import Line_Follower_Direction

        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP

        self.arguments = Arguments("settings.json", [
            "--readable-leds", "0", "2", "3", "5"
        ])
        self.settings = self.arguments.get_settings("line_follower_raspberry_pi")

        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        self.mock_callback = MagicMock()
        self.thread_manager = Thread_Manager()
        self.line_follower = Line_Follower_Raspberry_Pi(
            self.location, self.direction, self.mock_callback, self.settings,
            self.thread_manager, delay=0
        )

    def test_initialization(self):
        from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

        # The settings argument must be `Arguments` or `Settings`
        with self.assertRaises(TypeError):
            Line_Follower_Raspberry_Pi(
                self.location, self.direction, self.mock_callback,
                None, self.thread_manager, delay=0
            )

        # `Arguments` is accepted (like `Settings` in `setUp`).
        self.rpi_gpio_mock.GPIO.setwarnings.reset_mock()
        self.rpi_gpio_mock.GPIO.setmode.reset_mock()
        line_follower = Line_Follower_Raspberry_Pi(
            self.location, self.direction, self.mock_callback, self.arguments,
            self.thread_manager, delay=0
        )

        # Verify that the correct sensors are set.
        self.assertEqual(line_follower._sensors, self.settings.get("led_pins"))

        # Warnings must be disabled.
        line_follower.gpio.setwarnings.assert_called_once_with(False)

        # Board numbering has to be used.
        line_follower.gpio.setmode.assert_called_once_with(line_follower.gpio.BOARD)

        # The "led_pins" must have the correct length.
        self.settings.set("led_pins", [1, 2, 3])
        with self.assertRaises(ValueError):
            Line_Follower_Raspberry_Pi(
                self.location, self.direction, self.mock_callback,
                self.settings, self.thread_manager, delay=0
            )

    def test_enable(self):
        emitter_pin = self.settings.get("emitter_pin")

        self.line_follower.enable()
        self.assertEqual(self.line_follower.gpio.setup.call_count, 1)
        self.line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, self.line_follower.gpio.OUT)
        ])
        self.assertEqual(self.line_follower.gpio.output.call_count, 1)
        self.line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, True)
        ])

    def test_disable(self):
        emitter_pin = self.settings.get("emitter_pin")

        self.line_follower.disable()
        self.assertEqual(self.line_follower.gpio.setup.call_count, 1)
        self.line_follower.gpio.setup.assert_has_calls([
            call(emitter_pin, self.line_follower.gpio.OUT)
        ])
        self.assertEqual(self.line_follower.gpio.output.call_count, 1)
        self.line_follower.gpio.output.assert_has_calls([
            call(emitter_pin, False)
        ])

    def test_read(self):
        led_pins = self.settings.get("led_pins")
        readable_leds = self.settings.get("readable_leds")
        led_count = len(readable_leds)

        inputs = [1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0]
        self.line_follower.gpio.input.configure_mock(side_effect=inputs)
        t = time.time()
        times = [t]*2 + [t + 1e-6]*2 + [t + 2e-6]*2 + [sys.float_info.max]*2
        loop_count = 3
        with patch.object(time, "time", side_effect=times) as time_mock:
            sensor_values = self.line_follower.read()

            # Ensure the setup method is called the correct number of times.
            self.assertEqual(self.line_follower.gpio.setup.call_count, led_count*3)
            args_list = self.line_follower.gpio.setup.call_args_list
            for call_index, led_pin in enumerate(readable_leds):
                out_call = call(led_pins[led_pin], self.line_follower.gpio.OUT)
                self.assertEqual(args_list[call_index], out_call)

                pull_call = call(led_pins[led_pin], self.line_follower.gpio.IN,
                                 pull_up_down=self.line_follower.gpio.PUD_DOWN)
                self.assertEqual(args_list[led_count+2*call_index], pull_call)

                in_call = call(led_pins[led_pin], self.line_follower.gpio.IN)
                self.assertEqual(args_list[led_count+2*call_index+1], in_call)

            # Ensure the output method calls are correct.
            self.assertEqual(self.line_follower.gpio.output.call_args_list, [
                call(led_pins[led_pin], True) for led_pin in readable_leds
            ])

            # Ensure the input method calls are correct.
            self.assertEqual(self.line_follower.gpio.input.call_args_list, [
                call(led_pins[led_pin]) for led_pin in readable_leds
            ]*loop_count)

            # Ensure the `time.time` function is called enough times: once for 
            # the start time, then twice per full loop and once for detecting 
            # that the maximum time has elapsed.
            self.assertEqual(time_mock.call_count, 1 + 2*loop_count + 1)

            self.assertEqual(sensor_values, [0, 0, 1, 1])
