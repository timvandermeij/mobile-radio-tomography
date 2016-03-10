import math
import numpy as np
import sys
from ..environment import Environment
from ..trajectory.Memory_Map import Memory_Map
from ..settings import Arguments
from core_thread_manager import ThreadableTestCase
from geometry import LocationTestCase
from settings import SettingsTestCase

class TestMemoryMap(ThreadableTestCase, LocationTestCase, SettingsTestCase):
    def setUp(self):
        super(TestMemoryMap, self).setUp()
        self.arguments = Arguments("settings.json", [
            "--vehicle-class", "Mock_Vehicle", "--no-infrared-sensor"
        ])
        self.environment = Environment.setup(self.arguments, geometry_class="Geometry", simulated=True)
        self.coord_delta = sys.float_info.epsilon * 10
    
    def test_init(self):
        size = 100
        resolution = 5
        altitude = 4.0
        memory_map = Memory_Map(self.environment, size, resolution, altitude)
        self.assertEqual(memory_map.get_size(), size * resolution)
        self.assertEqual(memory_map.resolution, resolution)
        self.assertIsInstance(memory_map.get_map(), np.ndarray)
        self.assertEqual(memory_map.get_map().shape, (size * resolution, size * resolution))
        self.assertEqual(memory_map.bl, self.environment.get_location(-size/2, -size/2, altitude))
        self.assertEqual(memory_map.tr, self.environment.get_location(size/2, size/2, altitude))

    def test_index(self):
        size = 100
        resolution = 5
        altitude = 4.0

        in_bounds = (size * resolution - 1, 0)
        out_bounds = (size * resolution, -1)

        memory_map = Memory_Map(self.environment, size, resolution, altitude)
        self.environment.get_vehicle().set_location(0.0, 0.0, altitude)

        self.assertEqual(memory_map.get_index(self.environment.get_location()), (250, 250))
        self.assertEqual(memory_map.get_xy_index(self.environment.get_location(size/2, size/10)), (300, 500))

        self.assertTrue(memory_map.index_in_bounds(*in_bounds))
        self.assertFalse(memory_map.index_in_bounds(*out_bounds))

        self.assertTrue(memory_map.location_in_bounds(self.environment.get_location()))
        self.assertFalse(memory_map.location_in_bounds(self.environment.get_location(size,size)))

        with self.assertRaises(KeyError):
            memory_map.set(out_bounds, 1)
        with self.assertRaises(KeyError):
            memory_map.get(out_bounds)

        memory_map.set(in_bounds, 1)
        self.assertEqual(memory_map.get(in_bounds), 1)

        self.assertEqual(len(memory_map.get_nonzero()), 1)
        self.assertIn(in_bounds, memory_map.get_nonzero())
        loc = memory_map.get_location(250, 250)
        location = self.environment.get_location()
        self.assertEqual(loc, location)

        self.assertEqual(memory_map.get_location(*in_bounds), memory_map.get_nonzero_locations()[0])

        self.assertEqual(memory_map.get_location(0, 0), memory_map.bl)
        self.assertEqual(memory_map.get_location(250, 250), self.environment.get_location())

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
        loc = memory_map.get_location(*idx)
        self.assertAlmostEqual(loc.north, location.north, delta=self.coord_delta)
        self.assertAlmostEqual(loc.east, location.east, delta=self.coord_delta)
        self.assertEqual(loc.down, location.down)
