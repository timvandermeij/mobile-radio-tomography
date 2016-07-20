import numpy as np
from dronekit import LocationLocal
from ..geometry.Geometry_Grid import Geometry_Grid
from ..location.AStar import AStar
from ..planning.Collision_Avoidance import Collision_Avoidance, Collision_Type
from ..settings import Arguments
from ..trajectory.Memory_Map import Memory_Map
from geometry import LocationTestCase
from settings import SettingsTestCase

class TestPlanningCollisionAvoidance(LocationTestCase, SettingsTestCase):
    def setUp(self):
        super(TestPlanningCollisionAvoidance, self).setUp()

        self.arguments = Arguments("settings.json", [
            "--network-size", "10", "10", "--network-padding", "1", "1"
        ])
        self.geometry = Geometry_Grid()
        self.collision_avoidance = Collision_Avoidance(self.arguments,
                                                       self.geometry)

        self.real_size = 10
        self.size = self.real_size + 1
        half = self.size/2.0
        self.center = LocationLocal(half, half, 0.0)

        self.real_padding = 1
        self.padding = self.real_padding + 1

        self.home_locations = [(0, 0), (0, 10), (10, 10)]
        self.assignment = {
            1: [[5, 1, 0]],
            2: [],
            3: []
        }

    def test_initialization(self):
        self.assertEqual(self.collision_avoidance._geometry, self.geometry)
        self.assertTrue(self.collision_avoidance._enabled)
        self.assertEqual(self.collision_avoidance._network_size,
                         (self.real_size, self.real_size))
        self.assertEqual(self.collision_avoidance._network_padding,
                         (self.real_padding, self.real_padding))

        self.assertEqual(self.collision_avoidance._center, self.center)
        self.assertIsInstance(self.collision_avoidance._memory_map, Memory_Map)
        self.assertEqual(self.collision_avoidance._memory_map.get_size(),
                         self.size)
        self.assertIsInstance(self.collision_avoidance._astar, AStar)

    def test_reset(self):
        # Fill the current map with data, to ensure that it is cleared.
        memory_map = self.collision_avoidance._memory_map
        for i in range(self.size):
            for j in range(self.size):
                memory_map.set((i, j), 1)

        end = self.size - self.padding
        expected_map = np.zeros((self.size, self.size))
        expected_map[self.padding, self.padding:end] = Collision_Type.NETWORK
        expected_map[end-1, self.padding:end] = Collision_Type.NETWORK
        expected_map[self.padding:end, self.padding] = Collision_Type.NETWORK
        expected_map[self.padding:end, end-1] = Collision_Type.NETWORK

        self.collision_avoidance.reset()
        self.assertTrue(np.array_equal(memory_map.get_map(), expected_map))

        self.assertEqual(self.collision_avoidance._vehicles, set())
        self.assertEqual(self.collision_avoidance._vehicle_syncs, {})
        self.assertEqual(self.collision_avoidance._vehicle_routes, {})
        self.assertTrue(np.array_equal(self.collision_avoidance._vehicle_distances, np.empty(0)))
        self.assertEqual(self.collision_avoidance._current_vehicle, 0)

    def test_location(self):
        # Initially, the location is the center of the memory map.
        self.assertEqual(self.collision_avoidance.location, self.center)

        # Once we have a current vehicle, then we track its location.
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        1, 2)
        self.assertEqual(self.collision_avoidance.location,
                         LocationLocal(5, 1, 0))

    def test_distance(self):
        # Initially, the distance is neutral.
        self.assertEqual(self.collision_avoidance.distance, 0.0)

        # Once we have a current vehicle, then we track its distance.
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        1, 2)
        self.assertEqual(self.collision_avoidance.distance, 6)

    def test_update(self):
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        1, 2)

        self.assignment[2].append([5, 9, 0])
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        2, 1)
        self.assertEqual(self.collision_avoidance.location,
                         LocationLocal(5, 9, 0))
        self.assertEqual(self.collision_avoidance.distance, 6)

        # Vehicles 1 and 2 are synchronized with each other, but vehicle 3 has 
        # not yet. Thus it can crooss either vehicle's paths, which can lead to 
        # a collision.
        self.assignment[3].append([0, 5, 0])
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        3, 1)
        self.assertEqual(self.collision_avoidance.location,
                         LocationLocal(0, 5, 0))
        self.assertEqual(self.collision_avoidance.distance, np.inf)

    def test_update_disabled(self):
        self.collision_avoidance._enabled = False
        self.collision_avoidance.update(self.home_locations, self.assignment,
                                        1, 2)

        # When the collision avoidance algorithm is disabled, then the location 
        # and distance do not update.
        self.assertEqual(self.collision_avoidance.location, self.center)
        self.assertEqual(self.collision_avoidance.distance, 0.0)
