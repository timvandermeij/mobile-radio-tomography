import math
import unittest
from mock import call, patch, MagicMock
from ..bench.Method_Coverage import covers
from ..core.Threadable import Threadable
from ..core.Thread_Manager import Thread_Manager
from ..location.Line_Follower import Line_Follower, Line_Follower_State, Line_Follower_Direction
from core_thread_manager import ThreadableTestCase

class TestLocationLineFollower(ThreadableTestCase):
    def setUp(self):
        super(TestLocationLineFollower, self).setUp()

        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP
        # Set up a line follower for the other tests.
        self.mock_callback = MagicMock()
        self.thread_manager = Thread_Manager()
        self.line_follower = Line_Follower(self.location, self.direction,
                                           self.mock_callback,
                                           self.thread_manager)

    def test_initialization(self):
        # Test initialization of line follower with a local variable rather 
        # than the one already created at setUp.
        mock_callback = MagicMock()
        thread_manager = Thread_Manager()

        # Location must be a tuple.
        with self.assertRaises(ValueError):
            line_follower = Line_Follower([0, 0], self.direction,
                                          mock_callback, thread_manager)

        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            line_follower = Line_Follower(self.location, "up",
                                          mock_callback, thread_manager)

        # Correct intialization should set the attributes.
        line_follower = Line_Follower(self.location, self.direction,
                                      mock_callback, thread_manager)
        self.assertEqual(line_follower._location, self.location)
        self.assertEqual(line_follower._direction, self.direction)
        self.assertEqual(line_follower._callback, mock_callback)
        self.assertEqual(line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(line_follower._running)

    @patch('thread.start_new_thread')
    @covers(["activate", "deactivate"])
    def test_thread(self, thread_mock):
        self.line_follower.activate()
        thread_mock.assert_called_once_with(self.line_follower._loop, ())

        self.assertTrue(self.line_follower._running)
        self.line_follower.deactivate()
        self.assertFalse(self.line_follower._running)

    @covers(["enable", "disable", "read"])
    def test_interface(self):
        with self.assertRaises(NotImplementedError):
            self.line_follower.enable()
        with self.assertRaises(NotImplementedError):
            self.line_follower.disable()
        with self.assertRaises(NotImplementedError):
            self.line_follower.read()

    @patch.object(Line_Follower, "enable")
    @patch.object(Line_Follower, "disable")
    @patch.object(Line_Follower, "read")
    @patch.object(Line_Follower, "update")
    def test_loop(self, update_mock, read_mock, disable_mock, enable_mock):
        self.line_follower._running = True
        with patch.object(Threadable, "interrupt") as interrupt_mock:
            enable_mock.configure_mock(side_effect=RuntimeError)
            self.line_follower._loop()
            enable_mock.assert_called_once_with()
            read_mock.assert_not_called()
            interrupt_mock.assert_called_once_with()

        enable_mock.reset_mock()
        enable_mock.configure_mock(side_effect=None)
        read_mock.configure_mock(side_effect=self.line_follower.deactivate)

        self.line_follower._loop()
        enable_mock.assert_called_once_with()
        read_mock.assert_called_once_with()
        update_mock.assert_not_called()
        self.assertFalse(self.line_follower._running)

        self.line_follower._running = True
        enable_mock.reset_mock()
        read_mock.reset_mock()
        read_mock.configure_mock(side_effect=None)
        disable_mock.configure_mock(side_effect=self.line_follower.deactivate)

        self.line_follower._loop()
        self.assertFalse(self.line_follower._running)

    def test_update_line(self):
        # Invalid sensor values should cause an error.
        with self.assertRaises(ValueError):
            self.line_follower.update(0b0110)

        # It should detect being on a single line.
        self.line_follower.update([0, 1, 1, 0])
        self.assertEqual(self.line_follower._location, self.location)
        self.assertEqual(self.line_follower._direction, self.direction)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(self.mock_callback.called)

    def test_update_intersection_both(self):
        # It should detect being on an intersection (both sides).
        self.line_follower.update([1, 1, 1, 1])
        new_location = (self.location[0], self.location[1] + 1)
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, self.direction)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_intersection_left(self):
        # It should detect being on an intersection (only left line).
        self.line_follower.update([1, 1, 1, 0])
        new_location = (self.location[0], self.location[1] + 1)
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, self.direction)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_intersection_right(self):
        # It should detect being on an intersection (only right line).
        self.line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0], self.location[1] + 1)
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, self.direction)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_intersection_multi(self):
        # It should do nothing when the vehicle is on an intersection and we
        # detect an intersection again.
        self.line_follower.update([1, 1, 1, 1])
        self.line_follower.update([1, 1, 1, 1])
        new_location = (self.location[0], self.location[1] + 1)
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, self.direction)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.assertEqual(self.mock_callback.call_count, 1)

    def test_update_direction_down(self):
        # It should handle changing directions.
        self.line_follower.set_direction(Line_Follower_Direction.DOWN)
        self.line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0], self.location[1] - 1)
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.DOWN)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_direction_left(self):
        self.line_follower.set_direction(Line_Follower_Direction.LEFT)
        self.line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0] - 1, self.location[1])
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.LEFT)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_direction_right(self):
        self.line_follower.set_direction(Line_Follower_Direction.RIGHT)
        self.line_follower.update([0, 1, 1, 1])
        new_location = (self.location[0] + 1, self.location[1])
        self.assertEqual(self.line_follower._location, new_location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.RIGHT)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_INTERSECTION)
        self.mock_callback.assert_has_calls([
            call("intersection", new_location)
        ])

    def test_update_nothing(self):
        # It should do nothing when the vehicle is not on a line and no other
        # lines are detected.
        self.line_follower.update([0, 0, 0, 0])
        self.assertEqual(self.line_follower._location, self.location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(self.mock_callback.called)

    def test_update_sides(self):
        # It should do nothing when the vehicle is not on a line and both other
        # lines are detected.
        self.line_follower.update([1, 0, 0, 1])
        self.assertEqual(self.line_follower._location, self.location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)
        self.assertFalse(self.mock_callback.called)

    def test_update_diverged_left(self):
        # It should let the controller know when the vehicle diverged from the 
        # grid.
        self.line_follower.update([1, 0, 0, 0])
        self.assertEqual(self.line_follower._location, self.location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)
        self.mock_callback.assert_has_calls([
            call("diverged", "left")
        ])

    def test_update_diverged_right(self):
        self.line_follower.update([0, 0, 0, 1])
        self.assertEqual(self.line_follower._location, self.location)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.UP)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)
        self.mock_callback.assert_has_calls([
            call("diverged", "right")
        ])

    def test_set_state(self):
        # State must be one of the defined types.
        with self.assertRaises(ValueError):
            self.line_follower.set_state("intersection")

        # A valid state must be set.
        self.line_follower.set_state(Line_Follower_State.AT_LINE)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)

    def test_set_direction(self):
        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            self.line_follower.set_direction("up")

        # A valid direction must be set.
        self.line_follower.set_direction(Line_Follower_Direction.LEFT)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.LEFT)

@covers(Line_Follower_Direction)
class TestLocationLineFollowerDirection(unittest.TestCase):
    def setUp(self):
        super(TestLocationLineFollowerDirection, self).setUp()
        self.yaw_cases = [
            (0.0, Line_Follower_Direction.UP),
            (math.pi/2, Line_Follower_Direction.RIGHT),
            (math.pi, Line_Follower_Direction.DOWN),
            (3*math.pi/2, Line_Follower_Direction.LEFT),
        ]

    def test_from_yaw(self):
        for yaw, direction in self.yaw_cases:
            self.assertEqual(Line_Follower_Direction.from_yaw(yaw), direction)

        self.assertEqual(Line_Follower_Direction.from_yaw(math.pi/3),
                         Line_Follower_Direction.RIGHT)

    def test_yaw(self):
        for yaw, direction in self.yaw_cases:
            self.assertEqual(direction.yaw, yaw)

    def test_axis(self):
        cases = [
            (Line_Follower_Direction.UP, 0),
            (Line_Follower_Direction.RIGHT, 1),
            (Line_Follower_Direction.DOWN, 0),
            (Line_Follower_Direction.LEFT, 1)
        ]
        for direction, axis in cases:
            self.assertEqual(direction.axis, axis)

    def test_sign(self):
        cases = [
            (Line_Follower_Direction.UP, 1),
            (Line_Follower_Direction.RIGHT, 1),
            (Line_Follower_Direction.DOWN, -1),
            (Line_Follower_Direction.LEFT, -1)
        ]
        for direction, sign in cases:
            self.assertEqual(direction.sign, sign)

    def test_invert(self):
        cases = [
            (Line_Follower_Direction.UP, Line_Follower_Direction.DOWN),
            (Line_Follower_Direction.RIGHT, Line_Follower_Direction.LEFT),
            (Line_Follower_Direction.DOWN, Line_Follower_Direction.UP),
            (Line_Follower_Direction.LEFT, Line_Follower_Direction.RIGHT)
        ]
        for direction, inverted_direction in cases:
            self.assertEqual(direction.invert(), inverted_direction)

    def test_add(self):
        cases = [
            # Adding a direction to "up" results in the same direction.
            [Line_Follower_Direction.UP] + [Line_Follower_Direction.UP]*2,
            [Line_Follower_Direction.UP] + [Line_Follower_Direction.RIGHT]*2,
            [Line_Follower_Direction.UP] + [Line_Follower_Direction.DOWN]*2,
            [Line_Follower_Direction.UP] + [Line_Follower_Direction.LEFT]*2,
            [
                Line_Follower_Direction.RIGHT, Line_Follower_Direction.RIGHT,
                Line_Follower_Direction.DOWN
            ],
            [
                Line_Follower_Direction.RIGHT, Line_Follower_Direction.DOWN,
                Line_Follower_Direction.LEFT
            ],
            [
                Line_Follower_Direction.RIGHT, Line_Follower_Direction.LEFT,
                Line_Follower_Direction.UP
            ],
            [
                Line_Follower_Direction.DOWN, Line_Follower_Direction.LEFT,
                Line_Follower_Direction.RIGHT
            ]
        ]
        for direction, add_direction, new_direction in cases:
            self.assertEqual(direction.add(add_direction), new_direction)

    def test_get_rotate_direction(self):
        cases = [
            (Line_Follower_Direction.UP, Line_Follower_Direction.LEFT, -1),
            (Line_Follower_Direction.UP, Line_Follower_Direction.RIGHT, 1),
            (Line_Follower_Direction.RIGHT, Line_Follower_Direction.UP, -1),
            (Line_Follower_Direction.RIGHT, Line_Follower_Direction.DOWN, 1),
            (Line_Follower_Direction.DOWN, Line_Follower_Direction.LEFT, 1),
            (Line_Follower_Direction.LEFT, Line_Follower_Direction.UP, 1)
        ]
        for direction, target_direction, rotate_direction in cases:
            self.assertEqual(direction.get_rotate_direction(target_direction),
                             rotate_direction)
