import math
from dronekit import LocationGlobal, LocationGlobalRelative, LocationLocal
from ..geometry.Geometry_Spherical import Geometry_Spherical
import geometry

class TestGeometrySpherical(geometry.TestGeometry):
    """
    Grid geometry test case.

    This tests the `Geometry_Spherical` class. All test methods are inherited
    from `TestGeometry`, but some are overridden here and new test methods
    are added to cover the additional interface.
    """

    def setUp(self):
        super(TestGeometrySpherical, self).setUp()
        self.geometry = Geometry_Spherical()
        # Up to 2 cm accuracy. Geometry is precise, but Geometry_Spherical has 
        # some rounding due to coordinate precision.
        self.dist_delta = 0.02
        self.coord_delta = self.dist_delta / self.geometry.EARTH_RADIUS
        # Up to 0.15 degrees accuracy. Geometry is precise, but 
        # Geometry_Spherical has some rounding due to get_angle not taking 
        # curvature into account.
        self.angle_delta = 0.15 * math.pi/180

    def _make_global_location(self, x, y, z=0.0):
        return LocationGlobal(x, y, z)

    def _make_relative_location(self, x, y, z=0.0):
        return LocationGlobalRelative(x, y, z)

    def test_set_home_location_type(self):
        # Spherical geometry requires a global location as home location.
        with self.assertRaises(TypeError):
            self.geometry.set_home_location(self.relative_location)

        with self.assertRaises(TypeError):
            self.geometry.set_home_location(self.local_location)

        global_location = LocationGlobal(3.0, 2.0, 1.0)
        self.global_mock.configure_mock(return_value=global_location)
        self.geometry.set_home_location(self.locations_mock)
        self.global_mock.assert_called_once_with()
        self.assertEqual(self.geometry.home_location, global_location)

    def test_get_coordinates_other(self):
        relative_location = LocationGlobalRelative(3.0, 2.0, 1.0)
        self.relative_mock.configure_mock(return_value=relative_location)
        self.assertEqual(self.geometry.get_coordinates(self.locations_mock),
                         (3.0, 2.0, 1.0))
        self.relative_mock.assert_called_once_with()

    def test_get_location_local_other(self):
        home_loc = self._make_global_location(5.0, 3.14, 10.0)
        self.geometry.set_home_location(home_loc)

        rel_loc = self.geometry.get_location_meters(home_loc, 0.4, 0.06, 1.0)
        local_loc = LocationLocal(0.4, 0.06, -1.0)
        new_loc = self.geometry.get_location_local(rel_loc)
        self.assertAlmostEqual(new_loc.north, local_loc.north,
                               delta=self.coord_delta)
        self.assertAlmostEqual(new_loc.east, local_loc.east,
                               delta=self.coord_delta)
        self.assertAlmostEqual(new_loc.down, local_loc.down,
                               delta=self.coord_delta)

        global_loc = LocationGlobal(rel_loc.lat, rel_loc.lon, 11.0)
        new_loc = self.geometry.get_location_local(global_loc)
        self.assertAlmostEqual(new_loc.north, local_loc.north,
                               delta=self.coord_delta)
        self.assertAlmostEqual(new_loc.east, local_loc.east,
                               delta=self.coord_delta)
        self.assertAlmostEqual(new_loc.down, local_loc.down,
                               delta=self.coord_delta)

    def test_get_location_frame(self):
        with self.assertRaises(TypeError):
            self.geometry.get_location_frame(self.global_location)

        relative_location = LocationGlobalRelative(7.6, 5.4, 3.2)
        self.relative_mock.configure_mock(return_value=relative_location)
        self.assertEqual(self.geometry.get_location_frame(self.locations_mock),
                         relative_location)
        self.relative_mock.assert_called_once_with()

    def test_get_locations_frame(self):
        relative_loc = LocationGlobalRelative(6.0, 5.0, 4.0)
        global_loc = LocationGlobal(3.0, 2.0, 1.0)
        local_loc = LocationLocal(0.0, -1.0, -2.0)

        self.relative_mock.configure_mock(return_value=relative_loc)
        self.global_mock.configure_mock(return_value=global_loc)
        self.local_mock.configure_mock(return_value=local_loc)

        loc1 = LocationGlobalRelative(5.4, 3.2, 1.0)
        frame_loc = self.geometry.get_locations_frame(self.locations_mock, loc1)
        self.assertEqual(frame_loc, relative_loc)
        self.relative_mock.assert_called_once_with()

        loc2 = LocationGlobal(8.6, 4.2, 0.8)
        frame_loc = self.geometry.get_locations_frame(self.locations_mock, loc2)
        self.assertEqual(frame_loc, global_loc)
        self.global_mock.assert_called_once_with()

        loc3 = LocationLocal(-2.0, 4.5, -2.5)
        frame_loc = self.geometry.get_locations_frame(self.locations_mock, loc3)
        self.assertEqual(frame_loc, local_loc)
        self.local_mock.assert_called_once_with()

        # Correct location types must be provided.
        with self.assertRaisesRegexp(TypeError, "`Locations`"):
            self.geometry.get_locations_frame(None, loc3)
        with self.assertRaisesRegexp(TypeError, "`Location`"):
            self.geometry.get_locations_frame(self.locations_mock, None)

    def test_equalize(self):
        home_loc = self._make_global_location(5.0, 3.14, 10.0)
        self.geometry.set_home_location(home_loc)
        loc1 = self.geometry.get_location_meters(home_loc, 0.4, 0.06, 1.0)
        loc2 = LocationLocal(0.4, 0.06, -1.0)
        loc3 = LocationGlobalRelative(5.0, 3.14, 0.0)
        self.assertEqual(*self.geometry.equalize(loc1, loc2))
        self.assertEqual(*self.geometry.equalize(home_loc, loc3))

        self.local_mock.configure_mock(return_value=loc2)
        self.relative_mock.configure_mock(return_value=loc3)
        self.assertEqual(*self.geometry.equalize(self.locations_mock, loc2))
        self.local_mock.assert_called_once_with()

        self.local_mock.reset_mock()
        self.assertEqual(*self.geometry.equalize(loc2, self.locations_mock))
        self.local_mock.assert_called_once_with()

        self.assertEqual(*self.geometry.equalize(self.locations_mock,
                                                 self.locations_mock))
        self.assertEqual(self.relative_mock.call_count, 2)

        with self.assertRaisesRegexp(TypeError, "`location1`"):
            self.geometry.equalize(None, loc2)
        with self.assertRaisesRegexp(TypeError, "`location2`"):
            self.geometry.equalize(loc1, None)

    def test_make_location(self):
        loc = LocationGlobalRelative(1.0, 2.0, 3.0)
        self.assertEqual(self.geometry.make_location(1.0, 2.0, 3.0), loc)

    def test_norm(self):
        self.assertIsNone(self.geometry.norm)
