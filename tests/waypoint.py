import unittest
from ..waypoint.Waypoint import Waypoint

class TestWaypoint(unittest.TestCase):
    def setUp(self):
        self.waypoint = Waypoint(1)

    def test_interface(self):
        with self.assertRaises(NotImplementedError):
            dummy = self.waypoint.name

        self.assertEqual(self.waypoint.vehicle_id, 1)

    def test_get_points(self):
        with self.assertRaises(NotImplementedError):
            self.waypoint.get_points()
