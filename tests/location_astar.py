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
        path, dist = self.astar.assign(start, end, 1.0)
        self.assertNotEqual(path, [])
        self.assertTrue(0 < dist < np.inf)

    def test_assign_closeness(self):
        res = self.size * self.resolution
        for i in xrange(1, res):
            for j in xrange(1, res):
                self.memory_map.set((i, j), 1)

        start = self.environment.get_location(0, 0, self.altitude)
        end = self.environment.get_location(4, 4, self.altitude)
        path, dist = self.astar.assign(start, end, 1/float(self.resolution))
        self.assertEqual(path, [])
        self.assertEqual(dist, np.inf)

    def test_assign_out_of_bounds(self):
        self.memory_map.set((0, 20), 1)
        self.memory_map.set((20, 0), 1)

        start = self.environment.get_location(0, 0, self.altitude)
        end = self.environment.get_location(5, 5, self.altitude)
        path, dist = self.astar.assign(start, end, 1.0)
        self.assertEqual(path, [])
        self.assertEqual(dist, np.inf)

    def test_assign_impossible(self):
        for i in range(self.size * self.resolution):
            self.memory_map.set((i, 20), 1)

        start = self.environment.get_location(-4, -4, self.altitude)
        end = self.environment.get_location(4, 4, self.altitude)
        path, dist = self.astar.assign(start, end, 1.0)
        self.assertEqual(path, [])
        self.assertEqual(dist, np.inf)

    def test_assign_leave_area(self):
        # Add an unsafe area at the starting location as well as some walls.
        start = self.environment.get_location(-4.6, -4.6, self.altitude)
        end = self.environment.get_location(4.6, 4.6, self.altitude)

        self.memory_map.set_location_value(start, 1)
        for i in range(self.resolution * 3, (self.size - 3) * self.resolution):
            self.memory_map.set((self.resolution * 3, i), 1)
            self.memory_map.set((i, self.resolution * 3), 1)

        path, dist = self.astar.assign(start, end, 1.0)
        self.assertNotEqual(path, [])
        self.assertTrue(0 < dist < np.inf)

    def test_assign_equal(self):
        start = self.environment.get_location(4, 4, self.altitude)
        path, dist = self.astar.assign(start, start, 1.0)
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0], start)
        self.assertEqual(dist, 0.0)

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
        self.astar = AStar(self.environment.get_geometry(), self.memory_map,
                           allow_at_bounds=True, trend_strides=False,
                           use_indices=True)

    def test_assign_grid(self):
        # Deny access to the entire center of the grid, excepting the boundary.
        n = self.size - 1
        closeness = 1/float(self.resolution)
        for i in xrange(1, n):
            for j in xrange(1, n):
                self.memory_map.set((i, j), 1)

        # Also enforce going into a certain direction.
        self.memory_map.set((n, 0), 1)

        path, dist = self.astar.assign((0, 0), (n, n), closeness)

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
        self.assertEqual(dist, n*2)
