from dronekit import LocationLocal
from ..location.AStar import AStar
from ..trajectory.Memory_Map import Memory_Map
from environment import EnvironmentTestCase

class TestAStar(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle", "--geometry-class", "Geometry"
        ], use_infrared_sensor=False)

        super(TestAStar, self).setUp()

        self.size = 10
        self.resolution = 5
        self.altitude = 4.0
        self.memory_map = Memory_Map(self.environment, self.size,
                                     self.resolution, self.altitude)
        self.astar = AStar(self.environment.get_geometry(), self.memory_map)

    def test_init(self):
        self.assertEqual(self.astar._geometry, self.environment.get_geometry())
        self.assertEqual(self.astar._memory_map, self.memory_map)
        self.assertEqual(self.astar._resolution, self.resolution)
        self.assertEqual(self.astar._size, self.size * self.resolution)

    def test_assign(self):
        self.memory_map.set((0,20), 1)
        self.memory_map.set((20,0), 1)
        path = self.astar.assign(LocationLocal(0, 0, self.altitude),
                                 LocationLocal(4, 4, self.altitude),
                                 1.0)
        self.assertNotEqual(path, [])

    def test_assign_impossible(self):
        for i in xrange(0, 21):
            self.memory_map.set((i,20), 1)
            self.memory_map.set((20,i), 1)

        path = self.astar.assign(LocationLocal(0, 0, self.altitude),
                                 LocationLocal(5, 5, self.altitude),
                                 1/float(self.resolution))
        self.assertEqual(path, [])

class TestAStarGrid(EnvironmentTestCase):
    def setUp(self):
        self.register_arguments([
            "--vehicle-class", "Mock_Vehicle",
            "--geometry-class", "Geometry_Grid"
        ], use_infrared_sensor=False)

        super(TestAStarGrid, self).setUp()

        self.size = 10
        self.resolution = 1
        self.altitude = 4.0
        self.memory_map = Memory_Map(self.environment, self.size,
                                     self.resolution, self.altitude)
        self.astar = AStar(self.environment.get_geometry(), self.memory_map,
                           allow_at_bounds=True)

    def test_assign_grid(self):
        n = self.size
        for i in xrange(1, n-1):
            for j in xrange(1, n-1):
                self.memory_map.set((i,j), 1)

        path = self.astar.assign(LocationLocal(-n/2, -n/2, self.altitude),
                                 LocationLocal(n/2-1, n/2-1, self.altitude),
                                 1/float(self.resolution))
        self.assertNotEqual(path, [])
