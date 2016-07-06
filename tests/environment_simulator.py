from dronekit import LocationLocal
from mock import patch
from ..geometry.Geometry_Spherical import Geometry_Spherical
from environment import EnvironmentTestCase

class TestEnvironmentSimulator(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--geometry-class", "Geometry_Spherical",
            "--vehicle-class", "Mock_Vehicle",
            "--translation", "1", "2", "3",
            "--scenefile", "tests/vrml/castle.wrl",
            "--location-check"
        ], distance_sensors=[0, 90], use_infrared_sensor=False)

        super(TestEnvironmentSimulator, self).setUp()

    def test_initialization(self):
        self.assertTrue(self.environment.has_location_check)
        self.assertIsNone(self.environment.old_location)
        home = self.environment.vehicle.home_location
        translation = self.environment.get_location(1, 2, 3)
        actual, expected = self.environment.geometry.equalize(home, translation)
        self.assertEqual(actual, expected)

    def test_get_objects(self):
        self.assertNotEqual(self.environment.get_objects(), [])

    def test_set_location_check(self):
        self.environment.remove_location_check()
        self.environment.set_location_check()
        self.assertTrue(self.environment.has_location_check)

    def test_remove_location_check(self):
        self.environment.remove_location_check()
        self.assertFalse(self.environment.has_location_check)

    def test_check_location(self):
        with patch.object(Geometry_Spherical, "get_plane_intersection",
                          side_effect=[(2,), (0.5,)]) as plane_intersection_mock:
            self.environment.vehicle.set_location(1.2, 2.1, 3.4)
            self.assertEqual(self.environment.old_location,
                             LocationLocal(1.2, 2.1, -3.4))

            with self.assertRaises(RuntimeError):
                self.environment.vehicle.set_location(2.3, 3.2, 4.5)

            # Up to 2 cm accuracy. Geometry is precise, but Geometry_Spherical 
            # has some rounding due to coordinate precision.
            coord_delta = 0.02 / Geometry_Spherical.EARTH_RADIUS

            self.assertEqual(plane_intersection_mock.call_count, 2)
            args = plane_intersection_mock.call_args[0]
            self.assertAlmostEqual(args[2].north, 3.5, delta=coord_delta)
            self.assertAlmostEqual(args[2].east, 5.3, delta=coord_delta)
            self.assertAlmostEqual(args[2].down, -7.9, delta=coord_delta)
