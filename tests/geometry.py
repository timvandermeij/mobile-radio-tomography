# Core imports
import math
import sys

# Unit test imports
import unittest
from mock import patch, Mock, PropertyMock

# Library imports
import numpy as np
from dronekit import LocationGlobal, LocationGlobalRelative, LocationLocal, Locations

# Package imports
from ..bench.Method_Coverage import covers
from ..geometry.Geometry import Geometry

class LocationTestCase(unittest.TestCase):
    """
    Test case base class that provides equality checking for `Location` objects.

    This makes it possible to use `assertEqual` and related unit test methods
    on location objects of the same type.
    """

    def setUp(self):
        super(LocationTestCase, self).setUp()
        self.addTypeEqualityFunc(LocationLocal, self.assertLocationLocalEqual)
        for loc_type in (LocationGlobal, LocationGlobalRelative):
            self.addTypeEqualityFunc(loc_type, self.assertLocationGlobalEqual)

    def assertLocationLocalEqual(self, first_loc, second_loc, msg=None):
        first_coords = (first_loc.north, first_loc.east, first_loc.down)
        second_coords = (second_loc.north, second_loc.east, second_loc.down)
        if first_coords != second_coords:
            if msg is None:
                msg = ""
            msg += "{} != {}".format(first_loc, second_loc)
            raise self.failureException(msg)

    def assertLocationGlobalEqual(self, first_loc, second_loc, msg=None):
        first_coords = (first_loc.lat, first_loc.lon, first_loc.alt)
        second_coords = (second_loc.lat, second_loc.lon, second_loc.alt)
        if first_coords != second_coords:
            if msg is None:
                msg = ""
            msg += "{} != {}".format(first_loc, second_loc)
            raise self.failureException(msg)

class TestGeometry(LocationTestCase):
    """
    Test case class for base Geometry tests.

    This class tests the `Geometry` interface. It can be subclassed in order
    to test the subclasses of `Geometry`. The test methods are then inherited,
    so some may need to be overridden to test different behavior.
    """

    def setUp(self):
        super(TestGeometry, self).setUp()

        # Geometry object to use in the tests.
        self.geometry = Geometry()

        # Delta values for approximate equality checks.
        # The default values handle float inaccuracies that may be caused by 
        # conversions in the geometry class.
        self.dist_delta = sys.float_info.epsilon * 10
        self.coord_delta = self.dist_delta
        self.angle_delta = sys.float_info.epsilon * 10

        # Create a mock version of a `Locations` object. The location frames 
        # have property mocks that can be configured to return a specific 
        # location value.
        self.locations_mock = Mock(spec_set=Locations)
        self.relative_mock = PropertyMock()
        self.global_mock = PropertyMock()
        self.local_mock = PropertyMock()

        type(self.locations_mock).global_relative_frame = self.relative_mock
        type(self.locations_mock).global_frame = self.global_mock
        type(self.locations_mock).local_frame = self.local_mock

        # Location objects that can be used by type checking tests, where the 
        # coordinate values do not matter at all.
        self.local_location = LocationLocal(1.0, 2.0, 3.0)
        self.global_location = LocationGlobal(4.0, 5.0, 6.0)
        self.relative_location = LocationGlobalRelative(7.0, 8.0, 9.0)

    def _make_global_location(self, x, y, z=0.0):
        """
        Create a `Location` object that is suitable as a global location.

        The returned type depends on the geometry being tested.
        """

        return LocationLocal(x, y, -z)

    def _make_relative_location(self, x, y, z=0.0):
        """
        Create a `Location` object that is suitable as a relative location.

        The returned type depends on the geometry being tested.
        """

        return LocationLocal(x, y, -z)

    def test_set_home_location(self):
        self.assertEqual(self.geometry.home_location,
                         self._make_global_location(0.0, 0.0, 0.0))

        home_loc = self._make_global_location(1.0, 2.0, 3.0)
        self.geometry.set_home_location(home_loc)
        self.assertEqual(self.geometry.home_location, home_loc)

    def test_set_home_location_type(self):
        # Base geometry does not support relative or global locations.
        with self.assertRaises(TypeError):
            self.geometry.set_home_location(self.relative_location)

        with self.assertRaises(TypeError):
            self.geometry.set_home_location(self.global_location)

    def test_equalize(self):
        # Local locations are kept intact.
        loc1 = LocationLocal(1.0, 2.0, 3.0)
        loc2 = LocationLocal(4.5, 6.7, -8.9)
        new_loc1, new_loc2 = self.geometry.equalize(loc1, loc2)
        self.assertEqual(loc1, new_loc1)
        self.assertEqual(loc2, new_loc2)

        # Base geometry does not support relative or global locations.
        with self.assertRaises(TypeError):
            self.geometry.equalize(self.local_location, self.relative_location)
        with self.assertRaises(TypeError):
            self.geometry.equalize(self.relative_location, self.global_location)
        with self.assertRaises(TypeError):
            self.geometry.equalize(self.global_location, self.local_location)

    def test_equals(self):
        loc = LocationLocal(1.0, 2.0, -3.0)
        self.assertTrue(self.geometry.equals(loc, loc))
        # Integer coordinates are still equal to floats.
        self.assertTrue(self.geometry.equals(loc, LocationLocal(1.0, 2, -3.0)))
        self.assertFalse(self.geometry.equals(loc, LocationLocal(1, 2, -3.14)))

    def test_make_location(self):
        # Base geometry creates local locations with inverted down component.
        loc = LocationLocal(1.0, 2.0, -3.0)
        self.assertEqual(self.geometry.make_location(1.0, 2.0, 3.0), loc)

    def test_get_coordinates(self):
        # Check that retrieving coordinates from `Location` objects works.
        # The supported location types of the geometry are tested.
        loc1 = LocationLocal(1.0, 2.0, -3.0)
        self.assertEqual(self.geometry.get_coordinates(loc1), (1.0, 2.0, 3.0))

        loc2 = self._make_relative_location(4.0, 5.0, 6.0)
        self.assertEqual(self.geometry.get_coordinates(loc2), (4.0, 5.0, 6.0))

        loc3 = self._make_global_location(7.0, 8.0, 9.0)
        self.assertEqual(self.geometry.get_coordinates(loc3), (7.0, 8.0, 9.0))

        # A `Location` object must be provided.
        with self.assertRaises(TypeError):
            self.geometry.get_coordinates(None)

    def test_bearing_to_angle(self):
        bearing = -45.0 * math.pi/180
        self.assertEqual(self.geometry.bearing_to_angle(bearing),
                         135.0 * math.pi/180)

    def test_angle_to_bearing(self):
        angle = 180.0 * math.pi/180
        self.assertEqual(self.geometry.angle_to_bearing(angle),
                         270.0 * math.pi/180)

    def test_get_location_local(self):
        local_location = LocationLocal(7.6, 5.4, -3.2)
        self.assertEqual(self.geometry.get_location_local(local_location),
                         local_location)

        self.local_mock.configure_mock(return_value=local_location)
        self.assertEqual(self.geometry.get_location_local(self.locations_mock),
                         local_location)
        self.local_mock.assert_called_once_with()

    def test_get_location_local_other(self):
        # Base geometry does not support relative or global locations.
        with self.assertRaises(TypeError):
            self.geometry.get_location_local(self.global_location)
        with self.assertRaises(TypeError):
            self.geometry.get_location_local(self.relative_location)

    def test_get_location_frame(self):
        local_location = LocationLocal(7.6, 5.4, -3.2)
        self.local_mock.configure_mock(return_value=local_location)
        self.assertEqual(self.geometry.get_location_frame(self.locations_mock),
                         local_location)
        self.local_mock.assert_called_once_with()

    def test_get_location_frame_other(self):
        # A `Locations` object must be given.
        with self.assertRaises(TypeError):
            self.geometry.get_location_frame(self.local_location)
        with self.assertRaises(TypeError):
            self.geometry.get_location_frame(self.global_location)
        with self.assertRaises(TypeError):
            self.geometry.get_location_frame(self.relative_location)

    def test_get_location_meters(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        loc2 = LocationLocal(5.4, 3.2, -11.0)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 0), loc)
        self.assertEqual(self.geometry.get_location_meters(loc, 0, 0, 10), loc2)

    def test_get_distance_meters(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0)
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2),
                               5.0, delta=self.dist_delta)

    def test_norm(self):
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        self.assertEqual(self.geometry.norm(3.0, 4.0), 5.0)
        # (-12)**2 + 5**2 = 144 + 25 which is 13 squared.
        self.assertEqual(self.geometry.norm(0.0, -12.0, 5.0), 13.0)

    def test_diff_location_meters(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0, 5.0)
        dlat, dlon, dalt = self.geometry.diff_location_meters(loc, loc2)
        self.assertAlmostEqual(dlat, 3.0, delta=self.dist_delta)
        self.assertAlmostEqual(dlon, 4.0, delta=self.dist_delta)
        self.assertAlmostEqual(dalt, 5.0, delta=self.dist_delta)

    def test_get_location_range(self):
        home = self._make_relative_location(0.0, 0.0, 0.0)
        cases = [
            {
                "start": (0.0, 0.0),
                "end": (4.0, 0.0),
                "count": 4,
                "range": [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0)]
            },
            {
                "start": (5.0, 1.0),
                "end": (5.0, 3.0),
                "count": 2,
                "range": [(5.0, 2.0), (5.0, 3.0)]
            },
            {
                "start": (6.0, 6.0, 0.0),
                "end": (3.0, 0.0, 9.0),
                "count": 3,
                "range": [(5.0, 4.0, 3.0), (4.0, 2.0, 6.0), (3.0, 0.0, 9.0)]
            },
            {
                "start": (3.0, 4.0),
                "end": (3.0, 4.0),
                "count": 5,
                "range": [(3.0, 4.0)]*5
            },
            {
                "start": (4.0, 5.0),
                "end": (6.0, 7.0),
                "count": 1,
                "range": [(6.0, 7.0)]
            }
        ]
        for case in cases:
            start = self.geometry.get_location_meters(home, *case["start"])
            end = self.geometry.get_location_meters(home, *case["end"])
            actual = self.geometry.get_location_range(start, end,
                                                      count=case["count"])
            self.assertEqual(len(actual), len(case["range"]))
            for actual_loc, p in zip(actual, case["range"]):
                expected_loc = self.geometry.get_location_meters(home, *p)
                self.assertEqual(actual_loc,
                                 self.geometry.get_location_local(expected_loc))

    def test_get_location_angle(self):
        loc = LocationLocal(5.0, 3.0, -1.0)
        loc2 = self.geometry.get_location_meters(loc, 10, math.sqrt(200),
                                                 math.sqrt(200))
        cl = self.geometry.get_location_angle(loc, 20, 45.0 * math.pi/180,
                                              45.0 * math.pi/180)
        self.assertAlmostEqual(cl.north, loc2.north, delta=self.coord_delta)
        self.assertAlmostEqual(cl.east, loc2.east, delta=self.coord_delta)
        self.assertAlmostEqual(cl.down, loc2.down, delta=self.coord_delta)

        other_loc = self.geometry.get_location_angle(loc, 10.0, math.pi/4)
        angle = self.geometry.get_angle(loc, other_loc)
        self.assertAlmostEqual(angle, math.pi/4, delta=self.angle_delta)

    def test_get_angle(self):
        loc = LocationLocal(5.4, 3.2, -1.0)
        loc2 = self.geometry.get_location_meters(loc, 10.0, 10.0, 0.0)
        self.assertAlmostEqual(self.geometry.get_angle(loc, loc2),
                               45.0 * math.pi/180, delta=self.angle_delta)

    def test_diff_angle(self):
        self.assertEqual(self.geometry.diff_angle(math.pi, 3*math.pi), 0.0)
        self.assertEqual(abs(self.geometry.diff_angle(-math.pi/2, math.pi/2)),
                         math.pi)

    def test_check_angle(self):
        right = math.pi/2
        self.assertTrue(self.geometry.check_angle(math.pi, 3*math.pi, 0.0))
        self.assertFalse(self.geometry.check_angle(-right, right, math.pi/4))
        self.assertTrue(self.geometry.check_angle(2.0 * math.pi/180,
                                                  -2.0 * math.pi/180,
                                                  5.0 * math.pi/180))

    def test_get_direction(self):
        self.assertEqual(self.geometry.get_direction(0.0, math.pi/2), -1)
        self.assertEqual(self.geometry.get_direction(-math.pi/2, math.pi), 1)

    def test_get_neighbor_offsets(self):
        offsets = self.geometry.get_neighbor_offsets()
        self.assertEqual(offsets.shape, (8, 2))

        # pylint: disable=bad-continuation,bad-whitespace
        self.assertTrue(np.array_equal(offsets, [(-1, -1), (-1, 0), (-1, 1),
                                                  (0, -1),           (0, 1),
                                                  (1, -1),  (1, 0),  (1, 1)]))

    def test_ray_intersects_segment(self):
        cases = [
            [(1, 0), (2, 1), (0, 1), True], # Vertical edge
            [(1, 1), (2, 1), (0, 1), True], # Precisely on vertical edge
            [(1, 1), (1, 4), (4, 1), True], # Non-straight edge
            [(2, 0), (3, 1), (5.5, 3.25), False], # Too far north
            [(3, 20), (3, 2), (5, 7.6), False], # Too far east
            [(2, 3.5), (1, 1), (4, 4), False], # Right from edge
            [(2, 4), (1, 1), (4, 4), False] # Right from edge
        ]
        for case in cases:
            P = self._make_relative_location(*case[0])
            start = self._make_relative_location(*case[1])
            end = self._make_relative_location(*case[2])
            expected = case[3]
            with patch('sys.stdout'):
                actual = self.geometry.ray_intersects_segment(P, start, end,
                                                              verbose=True)
                msg = "Ray from {0} must{neg} intersect start={1}, end={2}"
                msg = msg.format(*case, neg="" if expected else " not")
                self.assertEqual(actual, expected, msg=msg)

    def test_point_inside_polygon(self):
        # http://rosettacode.org/wiki/Ray-casting_algorithm#Python
        polys = {
            "square": [(0, 0), (10, 0), (10, 10), (0, 10)],
            "square_hole": [
                (0, 0), (10, 0), (10, 10), (0, 10), (0, 0),
                (2.5, 2.5), (7.5, 2.5), (7.5, 7.5), (2.5, 7.5)
            ],
            "exagon": [(3, 0), (7, 0), (10, 5), (7, 10), (3, 10), (0, 5)]
        }
        locs = [(5, 8), (-10, 5), (10, 10)]
        results = {
            "square": [True, False, False],
            "square_hole": [True, False, False],
            "exagon": [True, False, False]
        }

        for name, poly in polys.iteritems():
            points = [self._make_relative_location(*p) for p in poly]
            for loc, expected in zip(locs, results[name]):
                location = self._make_relative_location(*loc)
                actual = self.geometry.point_inside_polygon(location, points)
                msg = "Point {} must{} be inside polygon {}"
                msg = msg.format(loc, "" if expected else " not", name)
                self.assertEqual(actual, expected, msg=msg)

        poly = polys["square"]
        points = [self._make_relative_location(*p) for p in poly]
        location = self._make_relative_location(1, 2, 3)
        with patch('sys.stdout'):
            inside = self.geometry.point_inside_polygon(location, points,
                                                        alt=True, verbose=True)
            self.assertFalse(inside)

    def test_get_edge_distance(self):
        start_location = self._make_relative_location(0.0, 0.0, 0.0)
        cases = [
            [(1, 0), (2, 1), (0, 1), 1.0], # Vertical edge
            [(1, 0), (2, 0), (2, 2), sys.float_info.max], # Horizontal edge
            [(1, 1), (2, 1), (0, 1), 0.0], # Precisely on vertical edge
            [(1, 1), (1, 4), (4, 1), 3.0], # Non-straight edge
            [(1, 1), (4, 1), (1, 4), 3.0], # Non-straight edge (swapped)
            [(1, 1), (2, 4), (4, 2), sys.float_info.max] # Non-extended line
        ]
        for case in cases:
            loc = self.geometry.get_location_meters(start_location, *case[0])
            start = self.geometry.get_location_meters(start_location, *case[1])
            end = self.geometry.get_location_meters(start_location, *case[2])
            expected = case[3]

            actual = self.geometry.get_edge_distance((start, end), loc)
            self.assertAlmostEqual(actual, expected, delta=self.dist_delta)

        # Miss the edge
        loc = self.geometry.get_location_meters(start_location, 1, 0.66, 0)
        start = self.geometry.get_location_meters(start_location, 2, 1, 0)
        end = self.geometry.get_location_meters(start_location, 0, 1, 0)
        actual = self.geometry.get_edge_distance((start, end), loc,
                                                 pitch_angle=0.25*math.pi)
        self.assertEqual(actual, sys.float_info.max)

    def test_get_point_edges(self):
        self.assertEqual(self.geometry.get_point_edges([]), [])
        points = [(1, 2, 3), (20.0, 4.3, 2.5), (3.14, 4.443, 1.2)]
        locations = [self._make_relative_location(*p) for p in points]
        edges = self.geometry.get_point_edges(locations)
        self.assertEqual(edges[0], (locations[0], locations[1]))
        self.assertEqual(edges[1], (locations[1], locations[2]))
        self.assertEqual(edges[2], (locations[2], locations[0]))

    def test_get_projected_location(self):
        location = LocationLocal(1.0, 2.0, -3.0)
        self.assertEqual(self.geometry.get_projected_location(location, 0),
                         LocationLocal(2.0, 3.0, 0.0))
        self.assertEqual(self.geometry.get_projected_location(location, 1),
                         LocationLocal(1.0, 3.0, 0.0))
        self.assertEqual(self.geometry.get_projected_location(location, 2),
                         location)

    @covers([
        "get_plane_intersection", "get_plane_vector", "point_inside_plane"
    ])
    def test_get_plane_distance(self):
        home = self._make_relative_location(0.0, 0.0, 0.0)
        cases = [
            # Upward polygon
            {
                "points": [(1, 2, 3), (1, 4, 3), (1, 4, 9), (1, 2, 9)],
                "location1": (0, 3, 6),
                "location2": (0.1, 3, 6),
                "distance": 1.0,
                "loc_point": (1, 3, 6)
            },
            # Missing the polygon
            {
                "points": [(1, 2, 3), (1, 4, 3), (1, 4, 9), (1, 2, 9)],
                "location1": (0, 5, 6),
                "location2": (0.1, 5, 6),
                "distance": sys.float_info.max,
                "loc_point": None
            },
            # Line segment in the other direction
            {
                "points": [(1, 2, 3), (1, 4, 3), (1, 4, 9), (1, 2, 9)],
                "location1": (0, 3, 6),
                "location2": (-0.1, 3, 6),
                "distance": sys.float_info.max,
                "loc_point": None
            },
            # Not intersecting with plane
            {
                "points": [(1, 2, 3), (1, 4, 3), (1, 4, 9), (1, 2, 9)],
                "location1": (0, 3, 6),
                "location2": (0, 3.1, 6),
                "distance": sys.float_info.max,
                "loc_point": None
            },
            # Incomplete face
            {
                "points": [(1, 2, 3), (1, 4, 3)],
                "location1": (0, 3, 6),
                "location2": (0.1, 3, 6),
                "distance": sys.float_info.max,
                "loc_point": None
            }
        ]
        for case in cases:
            points = case["points"]
            face = [self.geometry.get_location_meters(home, *p) for p in points]
            loc1 = self.geometry.get_location_meters(home, *case["location1"])
            loc2 = self.geometry.get_location_meters(home, *case["location2"])
            with patch('sys.stdout'):
                dist, point = self.geometry.get_plane_distance(face,
                                                               loc1, loc2,
                                                               verbose=True)

            self.assertAlmostEqual(dist, case["distance"],
                                   delta=self.dist_delta)
            if case["loc_point"] is None:
                self.assertIsNone(point)
            else:
                actual = self.geometry.get_location_local(point)
                location = self.geometry.get_location_meters(home,
                                                             *case["loc_point"])
                expected = self.geometry.get_location_local(location)
                self.assertAlmostEqual(actual.north, expected.north,
                                       delta=self.coord_delta)
                self.assertAlmostEqual(actual.east, expected.east,
                                       delta=self.coord_delta)
                self.assertAlmostEqual(actual.down, expected.down,
                                       delta=self.coord_delta)
