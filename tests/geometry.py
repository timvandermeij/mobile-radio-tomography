import unittest
import math
import sys
from droneapi.lib import Location
from ..geometry.Geometry import Geometry, Geometry_Spherical

class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(Location, self.assertLocationEqual)
        self.geometry = Geometry()
        # Handle float inaccuracies
        self.dist_delta = sys.float_info.epsilon * 10
        self.coord_delta = self.dist_delta
        self.angle_delta = sys.float_info.epsilon * 10

    def assertLocationEqual(self, loc1, loc2, msg=None):
        if loc1.lat != loc2.lat or loc1.lon != loc2.lon or loc1.alt != loc2.alt:
            if msg is None:
                msg = ""
            msg += "Location({}, {}, {}) != Location({}, {}, {})".format(loc1.lat, loc1.lon, loc1.alt, loc2.lat, loc2.lon, loc2.alt)
            raise self.failureException(msg)
        if loc1.is_relative != loc2.is_relative:
            raise self.failureException("Location relativeness differs")

    def test_home_location(self):
        self.assertEqual(self.geometry.home_location, Location(0.0, 0.0, 0.0, False))
        with self.assertRaises(ValueError):
            self.geometry.set_home_location(Location(3.0, 2.0, 1.0, True))
        self.geometry.set_home_location(Location(1.0, 2.0, 3.0, False))
        self.assertEqual(self.geometry.home_location, Location(1.0, 2.0, 3.0, False))

    def test_equalize(self):
        loc1 = Location(0.4, 0.06, 1.0, is_relative=True)
        loc2 = Location(5.4, 3.2, 11.0, is_relative=False)
        self.geometry.set_home_location(Location(5.0, 3.14, 10.0, False))
        loc1, loc2 = self.geometry.equalize(loc1, loc2)
        self.assertEqual(loc1, loc2)

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
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2), 5.0, delta=self.dist_delta)

    def test_diff_location(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0, 5.0)
        dlat, dlon, dalt = self.geometry.diff_location_meters(loc, loc2)
        self.assertAlmostEqual(dlat, 3.0, delta=self.dist_delta)
        self.assertAlmostEqual(dlon, 4.0, delta=self.dist_delta)
        self.assertAlmostEqual(dalt, 5.0, delta=self.dist_delta)

    def test_location_angle(self):
        loc = Location(5.0, 3.0, 1.0, is_relative=True)
        loc2 = self.geometry.get_location_meters(loc, 10, math.sqrt(200), math.sqrt(200))
        cl = self.geometry.get_location_angle(loc, 20, 45.0 * math.pi/180, 45.0 * math.pi/180)
        self.assertAlmostEqual(cl.lat, loc2.lat, delta=self.coord_delta)
        self.assertAlmostEqual(cl.lon, loc2.lon, delta=self.coord_delta)
        self.assertAlmostEqual(cl.alt, loc2.alt, delta=self.coord_delta)
        self.assertAlmostEqual(self.geometry.get_angle(loc, self.geometry.get_location_angle(loc, 10.0, math.pi/4)), math.pi/4, delta=self.angle_delta)

    def test_get_angle(self):
        loc = Location(5.4, 3.2, 1.0, is_relative=True)
        loc2 = self.geometry.get_location_meters(loc, 10.0, 10.0, 0.0)
        self.assertAlmostEqual(self.geometry.get_angle(loc, loc2), 45.0 * math.pi/180, delta=self.angle_delta)

    def test_diff_angle(self):
        self.assertEqual(self.geometry.diff_angle(math.pi, 3*math.pi), 0.0)
        self.assertEqual(abs(self.geometry.diff_angle(-math.pi/2, math.pi/2)), math.pi)

    def test_check_angle(self):
        self.assertEqual(self.geometry.check_angle(math.pi, 3*math.pi, 0.0), True)
        self.assertEqual(self.geometry.check_angle(-math.pi/2, math.pi/2, math.pi/4), False)
        self.assertEqual(self.geometry.check_angle(2.0 * math.pi/180, -2.0 * math.pi/180, 5.0 *math.pi/180), True)

    def test_get_direction(self):
        self.assertEqual(self.geometry.get_direction(0.0, math.pi/2), -1)
        self.assertEqual(self.geometry.get_direction(-math.pi/2, math.pi), 1)

class TestGeometry_Spherical(TestGeometry):
    def setUp(self):
        super(TestGeometry_Spherical, self).setUp()
        self.geometry = Geometry_Spherical()
        # Up to 2 cm accuracy. Geometry is precise, but Geometry_Spherical has 
        # some rounding due to coordinate precision.
        self.dist_delta = 0.02
        self.coord_delta = self.dist_delta / self.geometry.EARTH_RADIUS
        # Up to 0.15 degrees accuracy. Geometry is precise, but 
        # Geometry_Spherical has some rounding due to get_angle not taking 
        # curvature into account.
        self.angle_delta = 0.15 * math.pi/180
