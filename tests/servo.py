import unittest
from ..trajectory.Servo import Servo

class TestServo(unittest.TestCase):
    def test_init(self):
        # Must be given a correct interval tuple.
        with self.assertRaises(ValueError):
            servo = Servo(7, (1, 2, 3))

        servo = Servo(7, (45, 180), (1200, 1800))
        self.assertEqual(servo.get_pin(), 7)
        self.assertEqual(servo.get_pwm(), 1200)
        self.assertEqual(servo.get_value(), 45)
        self.assertTrue(servo.check_value(90))
        self.assertFalse(servo.check_value(0))

        servo = Servo(8, (0, 100))
        self.assertEqual(servo.get_pin(), 8)
        self.assertEqual(servo.get_pwm(), 1000)
        self.assertEqual(servo.get_value(), 0)
        self.assertEqual(servo.pwm.max, 2000)

    def test_get_pwm_value(self):
        servo = Servo(7, (45, 135), (1250, 1750))
        self.assertEqual(servo.get_pwm(90), 1500)
        self.assertEqual(servo.get_value(1500), 90)

    def test_current_pwm(self):
        servo = Servo(7, (90, 180), (1000, 2000))
        servo.set_current_pwm(1500)
        self.assertEqual(servo.get_pwm(), 1500)
        self.assertEqual(servo.get_value(), 135)
