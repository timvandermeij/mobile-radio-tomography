import unittest
from mock import patch, call, MagicMock
from ..settings import Arguments

class TestLocationLineFollower(unittest.TestCase):
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
        from ..location.Line_Follower import Line_Follower, Line_Follower_State

        mock_callback = MagicMock()

        # Location must be a tuple.
        with self.assertRaises(ValueError):
            line_follower = Line_Follower([0, 0], self.direction, mock_callback, self.settings)

        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            line_follower = Line_Follower(self.location, "up", mock_callback, self.settings)

        # Correct intialization should set the attributes.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._callback, mock_callback)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)

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
        from ..location.Line_Follower import Line_Follower, Line_Follower_Direction

        mock_callback = MagicMock()
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        sensors = self.settings.get("led_pins")
        sensor_values = line_follower.read()
        
        self.assertIs(type(sensor_values), list)
        line_follower.gpio.input.assert_has_calls([
            call(sensor) for sensor in [sensors[0], sensors[2], sensors[3], sensors[5]]
        ])

    def test_update(self):
        from ..location.Line_Follower import Line_Follower, Line_Follower_Direction, Line_Follower_State

        mock_callback = MagicMock()
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)

        # Invalid sensor values should cause an error.
        with self.assertRaises(ValueError):
            line_follower.update(0b0110)

        # It should detect being on a single line.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([0, 1, 1, 0])
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(mock_callback.called)
        mock_callback.reset_mock()

        # It should detect being on an intersection (both left and right lines).
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([1, 1, 1, 1])
        new_location = (self.location[0], self.location[1] + 1)
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        # It should detect being on an intersection (only left line).
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([1, 1, 1, 0])
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        # It should detect being on an intersection (only right line).
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([0, 1, 1, 1])
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        # It should do nothing when the vehicle is on an intersection and we
        # detect an intersection again.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([1, 1, 1, 1])
        line_follower.update([1, 1, 1, 1])
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.assertEqual(mock_callback.call_count, 1)
        mock_callback.reset_mock()

        # It should handle changing directions.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.set_direction(Line_Follower_Direction.DOWN)
        line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0], self.location[1] - 1)
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.DOWN)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.set_direction(Line_Follower_Direction.LEFT)
        line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0] - 1, self.location[1])
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.LEFT)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.set_direction(Line_Follower_Direction.RIGHT)
        line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0] + 1, self.location[1])
        self.assertEqual(line_follower._location, new_location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.RIGHT)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_INTERSECTION)
        mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])
        mock_callback.reset_mock()

        # It should do nothing when the vehicle is not on a line and no other
        # lines are detected.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([0, 0, 0, 0])
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(mock_callback.called)
        mock_callback.reset_mock()

        # It should do nothing when the vehicle is not on a line and both other
        # lines are detected.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([1, 0, 0, 1])
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(mock_callback.called)
        mock_callback.reset_mock()

        # It should let the controller know when the vehicle diverged from the grid.
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([1, 0, 0, 0])
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        mock_callback.assert_has_calls([
            call("diverged", "left")
        ])
        mock_callback.reset_mock()

        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)
        line_follower.update([0, 0, 0, 1])
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        mock_callback.assert_has_calls([
            call("diverged", "right")
        ])
        mock_callback.reset_mock()

    def test_set_location(self):
        from ..location.Line_Follower import Line_Follower, Line_Follower_Direction

        mock_callback = MagicMock()
        line_follower = Line_Follower(self.location, self.direction, mock_callback, self.settings)

        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            line_follower.set_direction("up")

        # A valid direction must be set.
        line_follower.set_direction(Line_Follower_Direction.LEFT)
        self.assertEqual(line_follower._direction, Line_Follower_Direction.LEFT)
