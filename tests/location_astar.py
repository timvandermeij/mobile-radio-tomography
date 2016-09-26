import math
import numpy as np
from ..bench.Method_Coverage import covers
from ..location.AStar import AStar
from ..trajectory.Memory_Map import Memory_Map
from environment import EnvironmentTestCase

class TestLocationAStar(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle",
            "--geometry-class", "Geometry_Spherical"
        ], use_infrared_sensor=False)

        super(TestLocationAStar, self).setUp()

        self.size = 10
        self.resolution = 5
        self.altitude = 4.0
        self.geometry = self.environment.geometry
        self.memory_map = Memory_Map(self.environment, self.size,
                                     self.resolution, self.altitude)
        self.astar = AStar(self.geometry, self.memory_map)

    def test_initialization(self):
        self.assertEqual(self.astar._geometry, self.geometry)
        self.assertEqual(self.astar._memory_map, self.memory_map)
        self.assertEqual(self.astar._resolution, self.resolution)
        self.assertEqual(self.astar._size, self.size * self.resolution)

    def test_assign(self):
        # Add some walls to the memory map
        for i in range(self.resolution * 2, (self.size - 2) * self.resolution):
            self.memory_map.set((self.resolution * 2, i), 1)
            self.memory_map.set((i, self.resolution * 2), 1)

        start = self.environment.get_location(-4.6, -4.6, self.altitude)
        end = self.environment.get_location(4.6, 4.6, self.altitude)
        path, trend, distance, direction = self.astar.assign(start, end, 1.0)
        self.assertNotEqual(path, [])
        self.assertNotEqual(trend, [])
        self.assertTrue(len(trend) < len(path))
        self.assertTrue(0 < distance < np.inf)
        self.assertTrue(0 <= direction <= 2*math.pi)

    def test_assign_closeness(self):
        res = self.size * self.resolution
        for i in xrange(1, res):
            for j in xrange(1, res):
                self.memory_map.set((i, j), 1)

        start = self.environment.get_location(0, 0, self.altitude)
        end = self.environment.get_location(4, 4, self.altitude)
        closeness = 1/float(self.resolution)
        path, trend, distance, direction = self.astar.assign(start, end,
                                                             closeness)
        self.assertEqual(path, [])
        self.assertEqual(trend, [])
        self.assertEqual(distance, np.inf)
        self.assertIsNone(direction)

    def test_assign_out_of_bounds(self):
        self.memory_map.set((0, 20), 1)
        self.memory_map.set((20, 0), 1)

        start = self.environment.get_location(0, 0, self.altitude)
        end = self.environment.get_location(5, 5, self.altitude)
        east = math.pi/2
        path, trend, distance, direction = self.astar.assign(start, end, 1.0,
                                                             direction=east)
        self.assertEqual(path, [])
        self.assertEqual(trend, [])
        self.assertEqual(distance, np.inf)
        self.assertEqual(direction, east)

    def test_assign_impossible(self):
        for i in range(self.size * self.resolution):
            self.memory_map.set((i, 20), 1)

        start = self.environment.get_location(-4, -4, self.altitude)
        end = self.environment.get_location(4, 4, self.altitude)
        path, trend, distance, direction = self.astar.assign(start, end, 1.0)
        self.assertEqual(path, [])
        self.assertEqual(trend, [])
        self.assertEqual(distance, np.inf)
        self.assertIsNone(direction)

    def test_assign_leave_area(self):
        # Add an unsafe area at the starting location as well as some walls.
        start = self.environment.get_location(-4.6, -4.6, self.altitude)
        end = self.environment.get_location(4.6, 4.6, self.altitude)

        self.memory_map.set_location_value(start, 1)
        for i in range(self.resolution * 3, (self.size - 3) * self.resolution):
            self.memory_map.set((self.resolution * 3, i), 1)
            self.memory_map.set((i, self.resolution * 3), 1)

        path, trend, distance, direction = \
            self.astar.assign(start, end, 1.0, direction=math.pi/2,
                              turning_cost=2/math.pi)

        self.assertNotEqual(path, [])
        self.assertNotEqual(trend, [])
        self.assertTrue(len(trend) < len(path))
        self.assertTrue(0 < distance < np.inf)
        self.assertTrue(0 <= direction <= 2*math.pi)

    def test_assign_equal(self):
        start = self.environment.get_location(4, 4, self.altitude)
        path, trend, distance, direction = self.astar.assign(start, start, 1.0,
                                                             direction=math.pi)
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0], start)
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0], start)
        self.assertEqual(distance, 0.0)
        self.assertEqual(direction, math.pi)

@covers(AStar)
class TestLocationAStarGrid(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle",
            "--geometry-class", "Geometry_Grid"
        ], use_infrared_sensor=False)

        super(TestLocationAStarGrid, self).setUp()

        self.size = 10
        self.resolution = 1
        self.altitude = 4.0
        self.memory_map = Memory_Map(self.environment, self.size,
                                     self.resolution, self.altitude)
        self.astar = AStar(self.environment.geometry, self.memory_map,
                           allow_at_bounds=True, use_indices=True)

    def test_assign_grid(self):
        # Deny access to the entire center of the grid, excepting the boundary.
        n = self.size - 1
        closeness = 1/float(self.resolution)
        for i in xrange(1, n):
            for j in xrange(1, n):
                self.memory_map.set((i, j), 1)

        # Also enforce going into a certain direction by disallowing the top 
        # left corner, which leaves only one safe path along the bottom and 
        # right sides.
        self.memory_map.set((n, 0), 1)

        path, trend, distance, direction = \
            self.astar.assign((0, 0), (n, n), closeness, direction=1.5*math.pi,
                              turning_cost=2/math.pi)

        # We receive an assignment. The path length is the correct length, 
        # containing even those waypoints that only differ in the same trend as 
        # the ones before them. It does not contain the starting point, and 
        # only has the midway corner point once.
        expected_path = []
        for i in range(1, self.size):
            expected_path.append((0, i))
        for i in range(1, self.size):
            expected_path.append((i, n))

        self.assertEqual(path, expected_path)
        self.assertEqual(len(path), self.size*2 - 2)
        self.assertEqual(trend, [(0, n), (n, n)])
        # The distance is the length of the path along the bottom and right 
        # side as well as the turning cost (two at the beginning and one in the 
        # bottom right corner).
        self.assertEqual(distance, n*2 + 3)
        # The vehicle ends up facing northward, which is a yaw angle of 0.
        self.assertEqual(direction, 0.0)
