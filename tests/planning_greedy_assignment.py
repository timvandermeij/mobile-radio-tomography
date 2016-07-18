import numpy as np
from ..geometry.Geometry_Grid import Geometry_Grid
from ..planning.Greedy_Assignment import Greedy_Assignment
from ..settings import Arguments
from ..waypoint.Waypoint import Waypoint_Type
from settings import SettingsTestCase

class TestPlanningGreedyAssignment(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", [])
        self.geometry = Geometry_Grid()
        self.assigner = Greedy_Assignment(self.arguments, self.geometry)

    def test_init(self):
        self.assertEqual(self.assigner._geometry, self.geometry)
        self.assertEqual(self.assigner._number_of_vehicles, 2)
        self.assertEqual(self.assigner._home_locations, [[0, 0], [0, 19]])
        self.assertEqual(self.assigner._vehicle_pairs, [(1, 2), (2, 1)])

    def test_assign(self):
        positions = np.array([[[3, 0], [5, 16]],
                              [[2, 19], [0, 1]],
                              [[0, 0], [1, 16]],
                              [[4, 18], [19, 1]]])

        assignment = self.assigner.assign(positions)[0]

        # Input is left untouched.
        self.assertEqual(positions.shape, (4, 2, 2))

        # We receive a good assignment.
        wait = Waypoint_Type.WAIT
        self.assertIsInstance(assignment, dict)
        self.assertEqual(len(assignment), 2)
        self.assertEqual(assignment[1], [
            [0, 0, 0, wait, 2, 1], [0, 1, 0, wait, 2, 1],
            [3, 0, 0, wait, 2, 1], [19, 1, 0, wait, 2, 1]
        ])
        self.assertEqual(assignment[2], [
            [1, 16, 0, wait, 1, 1], [2, 19, 0, wait, 1, 1],
            [5, 16, 0, wait, 1, 1], [4, 18, 0, wait, 1, 1]
        ])
