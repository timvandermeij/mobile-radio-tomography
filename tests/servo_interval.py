import unittest
from ..trajectory.Servo import Interval

class TestServo(unittest.TestCase):
    def test_init(self):
        # Both minimum and maximum must be provided.
        with self.assertRaises(ValueError):
            interval = Interval(1)
        with self.assertRaises(ValueError):
            interval = Interval((1,))

        # Cannot provide both a sequence and a maximum.
        with self.assertRaises(ValueError):
            interval = Interval([1, 2], 3)

        interval = Interval(1, 2)
        self.assertEqual(interval.min, 1)
        self.assertEqual(interval.max, 2)

        interval = Interval([1, 2])
        self.assertEqual(interval.min, 1)
        self.assertEqual(interval.max, 2)

    def test_diff(self):
        interval = Interval((123, 456))
        self.assertEqual(interval.diff, 333)
