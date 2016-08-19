import numpy as np
from dronekit import LocationLocal
from ..geometry.Geometry_Grid import Geometry_Grid
import geometry

class TestGeometryGrid(geometry.TestGeometry):
    """
    Grid geometry test case.

    This tests the `Geometry_Grid` class. All test methods are inherited from
    `GeometryTestCase`, but some are overridden here.
    """

    def setUp(self):
        super(TestGeometryGrid, self).setUp()
        self.geometry = Geometry_Grid()

    def test_get_distance_meters(self):
        loc = LocationLocal(5.0, 2.0, -1.0)
        loc2 = self.geometry.get_location_meters(loc, 3.0, 4.0)
        self.assertAlmostEqual(self.geometry.get_distance_meters(loc, loc2),
                               7.0, delta=self.dist_delta)

    def test_norm(self):
        # 3 * 3 + 4 * 4 = 9 + 16 = 25 which is 5 squared.
        self.assertEqual(self.geometry.norm(3.0, 4.0), 7.0)
        self.assertEqual(self.geometry.norm(-1.0, 4.0, 1.5), 6.5)

    def test_get_neighbor_offsets(self):
        offsets = self.geometry.get_neighbor_offsets()
        self.assertEqual(offsets.shape, (4, 2))

        # pylint: disable=bad-continuation,bad-whitespace
        self.assertTrue(np.array_equal(offsets, [          (-1, 0),
                                                  (0, -1),           (0, 1),
                                                            (1, 0)         ]))
