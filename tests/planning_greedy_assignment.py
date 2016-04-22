import numpy as np
from ..geometry.Geometry import Geometry_Grid
from ..planning.Greedy_Assignment import Greedy_Assignment
from ..settings import Arguments
from settings import SettingsTestCase

class TestPlanningGreedyAssignment(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", [])
        self.geometry = Geometry_Grid()
        self.assigner = Greedy_Assignment(self.arguments, self.geometry)

    def test_init(self):
        self.assertEqual(self.assigner._geometry, self.geometry)
        self.assertEqual(self.assigner._number_of_vehicles, 2)
        self.assertEqual(self.assigner._home_locations, [[0, 0], [0, 9]])
        self.assertEqual(self.assigner._vehicle_pairs, [(1, 2), (2, 1)])

    def test_assign(self):
        positions = np.array([[[3, 0], [5, 6]],
                              [[2, 9], [0, 1]],
                              [[0, 0], [1, 6]],
                              [[4, 8], [9, 1]]])

        assignment, distance = self.assigner.assign(positions)

        # Input is left untouched.
        self.assertEqual(positions.shape, (4, 2, 2))

        # We receive a good assignment.
        self.assertEqual(assignment, {
            1: [[0, 0, 0, 2], [0, 1, 0, 2], [3, 0, 0, 2], [9, 1, 0, 2]],
            2: [[1, 6, 0, 1], [2, 9, 0, 1], [5, 6, 0, 1], [4, 8, 0, 1]]
        })
