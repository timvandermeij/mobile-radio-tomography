import unittest
from mock import call, MagicMock
from ..core.Thread_Manager import Thread_Manager
from ..location.Line_Follower import Line_Follower, Line_Follower_State, Line_Follower_Direction

class TestLocationLineFollower(unittest.TestCase):
    def setUp(self):
        self.location = (0, 0)
        self.direction = Line_Follower_Direction.UP
        # Set up a line follower for the other tests.
        self.mock_callback = MagicMock()
        thread_manager = Thread_Manager()
        self.line_follower = Line_Follower(self.location, self.direction,
                                           self.mock_callback, thread_manager)

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
        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            self.line_follower.set_state("intersection")

        # A valid direction must be set.
        self.line_follower.set_direction(Line_Follower_State.AT_LINE)
        self.assertEqual(self.line_follower._state, Line_Follower_State.AT_LINE)

    def test_set_direction(self):
        # Direction must be one of the defined types.
        with self.assertRaises(ValueError):
            self.line_follower.set_direction("up")

        # A valid direction must be set.
        self.line_follower.set_direction(Line_Follower_Direction.LEFT)
        self.assertEqual(self.line_follower._direction, Line_Follower_Direction.LEFT)
