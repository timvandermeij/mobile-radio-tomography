# Core imports
import math
import sys

# Library imports
import numpy as np

# Unit test imports
from mock import MagicMock, PropertyMock

# Package imports
from ..environment.Location_Proxy import Location_Proxy
from ..geometry.Geometry import Geometry
from ..trajectory.Memory_Map import Memory_Map
from environment import EnvironmentTestCase

class TestTrajectoryMemoryMap(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle", "--geometry-class", "Geometry"
        ], use_infrared_sensor=False)

        super(TestTrajectoryMemoryMap, self).setUp()

        self.coord_delta = sys.float_info.epsilon * 10

        self.size = 100
        self.resolution = 5
        self.alt = 4.0

        self.res = self.size * self.resolution
        self.in_bounds = (self.res - 1, 0)
        self.out_bounds = (self.res, -1)

        self.memory_map = Memory_Map(self.environment, self.size,
                                     self.resolution, self.alt)
        self.memory_map.set(self.in_bounds, 1)
        self.environment.get_vehicle().set_location(0.0, 0.0, self.alt)

    def test_initialization(self):
        memory_map = Memory_Map(self.environment, self.size,
                                self.resolution, self.alt)
        half = self.size/2
        self.assertIsInstance(memory_map.geometry, Geometry)
        self.assertEqual(memory_map.resolution, self.resolution)
        self.assertEqual(memory_map.bl,
                         self.environment.get_location(-half, -half, self.alt))
        self.assertEqual(memory_map.tr,
                         self.environment.get_location(half, half, self.alt))

        # The first argument must be a `Location_Proxy`, such as `Environment`.
        geometry_config = {
            "spec_set": Geometry,
            "diff_location_meters.return_value": (1, 2, 3)
        }
        geometry_mock = MagicMock(**geometry_config)
        proxy_config = {
            "spec_set": Location_Proxy,
            "geometry": geometry_mock
        }
        proxy_mock = MagicMock(**proxy_config)
        Memory_Map(proxy_mock, self.size, self.resolution, self.alt)

        with self.assertRaises(TypeError):
            Memory_Map(None, self.size, self.resolution, self.alt)

    def test_get_resolution(self):
        self.assertEqual(self.memory_map.get_resolution(), self.resolution)

    def test_get_size(self):
        self.assertEqual(self.memory_map.get_size(), self.res)

    def test_get_map(self):
        memory_map = Memory_Map(self.environment, self.size,
                                self.resolution, self.alt)
        self.assertIsInstance(memory_map.get_map(), np.ndarray)
        self.assertTrue(np.array_equal(memory_map.get_map(),
                                       np.zeros((self.res, self.res))))

    def test_get_index(self):
        current_loc = self.environment.get_location()
        self.assertEqual(self.memory_map.get_index(current_loc), (250, 250))

    def test_get_xy_index(self):
        loc = self.environment.get_location(self.size/2, self.size/10)
        self.assertEqual(self.memory_map.get_xy_index(loc), (300, 500))

    def test_index_in_bounds(self):
        self.assertTrue(self.memory_map.index_in_bounds(*self.in_bounds))
        self.assertFalse(self.memory_map.index_in_bounds(*self.out_bounds))

    def test_location_in_bounds(self):
        current_loc = self.environment.get_location()
        self.assertTrue(self.memory_map.location_in_bounds(current_loc))

        out_of_bounds = self.environment.get_location(self.size, self.size)
        self.assertFalse(self.memory_map.location_in_bounds(out_of_bounds))

    def test_set(self):
        with self.assertRaises(KeyError):
            self.memory_map.set(self.out_bounds, 1)

        # Setting back to zero works.
        self.memory_map.set(self.in_bounds, 0)
        self.assertEqual(self.memory_map.get(self.in_bounds), 0)

    def test_get(self):
        with self.assertRaises(KeyError):
            self.memory_map.get(self.out_bounds)

        self.assertEqual(self.memory_map.get(self.in_bounds), 1)

    def test_get_nonzero(self):
        self.assertEqual(len(self.memory_map.get_nonzero()), 1)
        self.assertIn(self.in_bounds, self.memory_map.get_nonzero())

    def test_get_nonzero_array(self):
        self.assertTrue(np.array_equal(self.memory_map.get_nonzero_array(),
                                       np.array([self.in_bounds])))

    def test_get_location(self):
        loc = self.memory_map.get_location(250, 250)
        current_loc = self.environment.get_location()
        self.assertEqual(loc, current_loc)

        self.assertEqual(self.memory_map.get_location(0, 0), self.memory_map.bl)
        self.assertEqual(self.memory_map.get_location(250, 250),
                         self.environment.get_location())

    def test_get_nonzero_locations(self):
        self.assertEqual(self.memory_map.get_location(*self.in_bounds),
                         self.memory_map.get_nonzero_locations()[0])

    def test_clear(self):
        self.memory_map.clear()
        # Clearing the memory map works.
        self.assertEqual(self.memory_map.get(self.in_bounds), 0)
        self.assertTrue(np.array_equal(self.memory_map.get_map(),
                                       np.zeros((self.res, self.res))))

    def test_handle_sensor(self):
        size = 100
        resolution = 5
        altitude = 4.0

        idx = (250, 245)

        memory_map = Memory_Map(self.environment, size, resolution, altitude)
        self.environment.get_vehicle().set_location(0.0, 0.0, altitude)

        location = memory_map.handle_sensor(1.0, math.pi)
        self.assertEqual(memory_map.get_index(location), idx)
        self.assertEqual(len(memory_map.get_nonzero()), 1)
        self.assertIn(idx, memory_map.get_nonzero())
        self.assertTrue(np.array_equal(memory_map.get_nonzero_array(), [idx]))
        loc = memory_map.get_location(*idx)
        self.assertEqual(memory_map.get_nonzero_locations()[0], loc)
        self.assertAlmostEqual(loc.north, location.north,
                               delta=self.coord_delta)
        self.assertAlmostEqual(loc.east, location.east, delta=self.coord_delta)
        self.assertEqual(loc.down, location.down)

        # Test that a location that is outside the map does not raise an error.
        outside_location = memory_map.handle_sensor(1000, math.pi)
        self.assertFalse(memory_map.location_in_bounds(outside_location))
