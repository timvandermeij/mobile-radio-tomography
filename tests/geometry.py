import unittest
import math
from droneapi.lib import Location
from ..geometry.Geometry import Geometry, Geometry_Spherical

class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(Location, self.assertLocationEqual)
        self.geometry = Geometry()

    def assertLocationEqual(self, loc1, loc2, msg=None):
        if loc1.lat != loc2.lat or loc1.lon != loc2.lon or loc1.alt != loc2.alt:
            if msg is None:
                msg = ""
            msg += "Location({}, {}, {}) != Location({}, {}, {})".format(loc1.lat, loc1.lon, loc1.alt, loc2.lat, loc2.lon, loc2.alt)
            raise self.failureException(msg)

    def test_bearing_to_angle(self):
        bearing = -45.0 * math.pi/180
        self.assertEqual(self.geometry.bearing_to_angle(bearing), 135.0 * math.pi/180)

    def test_angle_to_bearing(self):
        angle = 180.0 * math.pi/180
        self.assertEqual(self.geometry.angle_to_bearing(angle), 270.0 * math.pi/180)

    def test_location_meters(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        loc2 = Location(5.4, 3.2, 11.0, is_relative=True)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 0), loc)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 10), loc2)

    def test_distance_meters(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0)
        # Up to 2 cm accuracy. Geometry is precise, but Geometry_Spherical has 
        # some rounding due to coordinate precision.
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2), 5.0, delta=0.02)

    def test_diff_location(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0, 5.0)
        dlat, dlon, dalt = self.geometry.diff_location_meters(loc, loc2)
        self.assertAlmostEqual(dlat, 3.0)
        self.assertAlmostEqual(dlon, 4.0)
        self.assertAlmostEqual(dalt, 5.0)

    def test_get_angle(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        loc2 = self.geometry.get_location_meters(loc, 10.0, 10.0, 0.0)
        # Up to 0.15 degrees accuracy. Geometry is precise, but 
        # Geometry_Spherical has some rounding due to get_angle not taking 
        # curvature into account.
        self.assertAlmostEqual(self.geometry.get_angle(loc, loc2), 45.0 * math.pi/180, delta=0.15 * math.pi/180)

    def test_diff_angle(self):
        self.assertEqual(self.geometry.diff_angle(math.pi, 3*math.pi), 0.0)
        self.assertEqual(abs(self.geometry.diff_angle(-math.pi/2, math.pi/2)), math.pi)

    def test_get_direction(self):
        self.assertEqual(self.geometry.get_direction(0.0, math.pi/2), -1)
        self.assertEqual(self.geometry.get_direction(-math.pi/2, math.pi), 1)

class TestGeometry_Spherical(TestGeometry):
    def setUp(self):
        super(TestGeometry_Spherical, self).setUp()
        self.geometry = Geometry_Spherical()
