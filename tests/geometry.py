import math
import numpy as np
import sys
import unittest
from dronekit import LocationGlobal, LocationGlobalRelative, LocationLocal
from ..geometry.Geometry import Geometry, Geometry_Grid, Geometry_Spherical

class LocationTestCase(unittest.TestCase):
    def setUp(self):
        super(LocationTestCase, self).setUp()
        self.addTypeEqualityFunc(LocationLocal, self.assertLocationLocalEqual)
        self.addTypeEqualityFunc(LocationGlobal, self.assertLocationGlobalEqual)
        self.addTypeEqualityFunc(LocationGlobalRelative, self.assertLocationGlobalEqual)

    def assertLocationLocalEqual(self, loc1, loc2, msg=None):
        if loc1.north != loc2.north or loc1.east != loc2.east or loc1.down != loc2.down:
            if msg is None:
                msg = ""
            msg += "{} != {}".format(loc1, loc2)
            raise self.failureException(msg)

    def assertLocationGlobalEqual(self, loc1, loc2, msg=None):
        if loc1.lat != loc2.lat or loc1.lon != loc2.lon or loc1.alt != loc2.alt:
            if msg is None:
                msg = ""
            msg += "{} != {}".format(loc1, loc2)
            raise self.failureException(msg)

class TestGeometry(LocationTestCase):
    def setUp(self):
        super(TestGeometry, self).setUp()
        self.geometry = Geometry()
        # Handle float inaccuracies
        self.dist_delta = sys.float_info.epsilon * 10
        self.coord_delta = self.dist_delta
        self.angle_delta = sys.float_info.epsilon * 10

    def _make_global_location(self, x, y, z):
        return LocationLocal(x, y, z)

    def _make_relative_location(self, x, y, z):
        return LocationLocal(x, y, z)

    def test_home_location_type(self):
        with self.assertRaises(TypeError):
            self.geometry.set_home_location(LocationGlobalRelative(3.0, 2.0, 1.0))

        with self.assertRaises(TypeError):
            self.geometry.set_home_location(LocationGlobal(3.0, 2.0, 1.0))

    def test_home_location(self):
        self.assertEqual(self.geometry.home_location, self._make_global_location(0.0, 0.0, 0.0))
        self.geometry.set_home_location(self._make_global_location(1.0, 2.0, 3.0))
        self.assertEqual(self.geometry.home_location, self._make_global_location(1.0, 2.0, 3.0))

    def test_equalize(self):
        loc1 = LocationLocal(1.0, 2.0, -3.0)
        loc2 = LocationGlobalRelative(5.4, 6.7, 8.0)
        loc3 = LocationGlobal(54.7, 10.2, 1000.8)
        with self.assertRaises(TypeError):
            self.geometry.equalize(loc1, loc2)
        with self.assertRaises(TypeError):
            self.geometry.equalize(loc2, loc3)
        with self.assertRaises(TypeError):
            self.geometry.equalize(loc3, loc1)

    def test_bearing_to_angle(self):
        bearing = -45.0 * math.pi/180
        self.assertEqual(self.geometry.bearing_to_angle(bearing), 135.0 * math.pi/180)

    def test_angle_to_bearing(self):
        angle = 180.0 * math.pi/180
        self.assertEqual(self.geometry.angle_to_bearing(angle), 270.0 * math.pi/180)

    def test_location_meters(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        loc2 = LocationLocal(5.4, 3.2, -11.0)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 0), loc)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 10), loc2)

    def test_distance_meters(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0)
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2), 5.0, delta=self.dist_delta)

    def test_diff_location(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0, 5.0)
        dlat, dlon, dalt = self.geometry.diff_location_meters(loc, loc2)
        self.assertAlmostEqual(dlat, 3.0, delta=self.dist_delta)
        self.assertAlmostEqual(dlon, 4.0, delta=self.dist_delta)
        self.assertAlmostEqual(dalt, 5.0, delta=self.dist_delta)

    def test_location_angle(self):
        loc = LocationLocal(5.0, 3.0, -1.0)
        loc2 = self.geometry.get_location_meters(loc, 10, math.sqrt(200), math.sqrt(200))
        cl = self.geometry.get_location_angle(loc, 20, 45.0 * math.pi/180, 45.0 * math.pi/180)
        self.assertAlmostEqual(cl.north, loc2.north, delta=self.coord_delta)
        self.assertAlmostEqual(cl.east, loc2.east, delta=self.coord_delta)
        self.assertAlmostEqual(cl.down, loc2.down, delta=self.coord_delta)
        self.assertAlmostEqual(self.geometry.get_angle(loc, self.geometry.get_location_angle(loc, 10.0, math.pi/4)), math.pi/4, delta=self.angle_delta)

    def test_get_angle(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
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

    def test_get_point_edges(self):
        self.assertEqual(self.geometry.get_point_edges([]), [])
        locations = [self._make_relative_location(*p) for p in [(1, 2, 3), (20.0, 4.3, 2.5), (3.14, 4.443, 1.2)]]
        edges = self.geometry.get_point_edges(locations)
        self.assertEqual(edges[0], (locations[0], locations[1]))
        self.assertEqual(edges[1], (locations[1], locations[2]))
        self.assertEqual(edges[2], (locations[2], locations[0]))

    def test_get_neighbor_offsets(self):
        offsets = self.geometry.get_neighbor_offsets()
        self.assertEqual(offsets.shape, (8, 2))
        self.assertTrue(np.array_equal(offsets, [(-1, -1), (-1, 0), (-1, 1),
                                                  (0, -1),           (0, 1),
                                                  (1, -1),  (1, 0),  (1, 1)]))

class TestGeometry_Grid(TestGeometry):
    def setUp(self):
        super(TestGeometry_Grid, self).setUp()
        self.geometry = Geometry_Grid()

    def test_distance_meters(self):
        loc = LocationLocal(5.0, 2.0, -1.0)
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0)
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2), 7.0, delta=self.dist_delta)

    def test_get_neighbor_offsets(self):
        offsets = self.geometry.get_neighbor_offsets()
        self.assertEqual(offsets.shape, (4, 2))
        self.assertTrue(np.array_equal(offsets, [          (-1, 0),
                                                  (0, -1),           (0, 1),
                                                            (1, 0)         ]))

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

    def _make_global_location(self, x, y, z):
        return LocationGlobal(x, y, z)

    def _make_relative_location(self, x, y, z):
        return LocationGlobalRelative(x, y, z)

    def test_home_location_type(self):
        with self.assertRaises(TypeError):
            self.geometry.set_home_location(LocationGlobalRelative(3.0, 2.0, 1.0))

        with self.assertRaises(TypeError):
            self.geometry.set_home_location(LocationLocal(3.0, 2.0, 1.0))

    def test_equalize(self):
        home_loc = self._make_global_location(5.0, 3.14, 10.0)
        self.geometry.set_home_location(home_loc)
        loc1 = self.geometry.get_location_meters(home_loc, 0.4, 0.06, 1.0)
        loc2 = LocationLocal(0.4, 0.06, -1.0)
        loc1, loc2 = self.geometry.equalize(loc1, loc2)
        self.assertEqual(loc1, loc2)
