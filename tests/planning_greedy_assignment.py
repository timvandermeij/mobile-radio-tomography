import numpy as np
from mock import patch
from ..core.Import_Manager import Import_Manager
from ..geometry.Geometry_Grid import Geometry_Grid
from ..location.Line_Follower import Line_Follower_Direction
from ..planning.Collision_Avoidance import Collision_Avoidance
from ..planning.Greedy_Assignment import Greedy_Assignment
from ..settings import Arguments
from ..waypoint.Waypoint import Waypoint, Waypoint_Type
from settings import SettingsTestCase

class TestPlanningGreedyAssignment(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", [
            "--network-padding", "5", "5"
        ])
        self.geometry = Geometry_Grid()
        self.import_manager = Import_Manager()
        self.assigner = Greedy_Assignment(self.arguments, self.geometry,
                                          self.import_manager)

    def test_init(self):
        self.assertEqual(self.assigner._geometry, self.geometry)
        self.assertEqual(self.assigner._import_manager, self.import_manager)

        self.assertEqual(self.assigner._number_of_vehicles, 2)
        self.assertEqual(self.assigner._home_locations, [[0, 0], [0, 19]])
        self.assertEqual(self.assigner._vehicle_pairs, [(1, 2), (2, 1)])

    def test_assign(self):
        positions = np.array([[[3, 0], [5, 16]],
                              [[2, 19], [0, 1]],
                              [[0, 0], [1, 16]],
                              [[0, 2], [4, 19]],
                              [[4, 18], [19, 1]]])

        assignment, distance = self.assigner.assign(positions)

        # Input is left untouched.
        self.assertEqual(positions.shape, (5, 2, 2))

        # We receive a good assignment.
        wait = Waypoint_Type.WAIT
        self.assertIsInstance(assignment, dict)
        self.assertEqual(len(assignment), 2)
        self.assertEqual(assignment[1], [
            [0, 0, 0, Waypoint_Type.HOME, 0, 1, -1],
            [0, 1, 0, wait, 2, 1, 0], [0, 2, 0, wait, 2, 1, 1],
            [3, 0, 0, wait, 2, 1, 2], [0, 0, 0, wait, 2, 1, 3],
            [19, 1, 0, wait, 2, 1, 4]
        ])
        self.assertEqual(assignment[2], [
            [0, 19, 0, Waypoint_Type.HOME, 0, 1, -1],
            [2, 19, 0, wait, 1, 1, 0], [4, 19, 0, wait, 1, 1, 1],
            [5, 16, 0, wait, 1, 1, 2], [1, 16, 0, wait, 1, 1, 3],
            [4, 18, 0, wait, 1, 1, 4]
        ])

        # The assignment is valid, i.e., the distance is not infinite due to 
        # conflicting paths
        self.assertNotEqual(distance, np.inf)

    def test_assign_conflict(self):
        positions = np.array([[[0, 0], [0, 0]]])

        assignment, distance = self.assigner.assign(positions)

        # A conflicting assignment results in an empty dictionary.
        self.assertEqual(assignment, {})

        # The distance of a conflicting assignment is set to infinity.
        self.assertEqual(distance, np.inf)

    @patch.object(Collision_Avoidance, "update",
                  side_effect=(([(3, 0)], 0.0), ([], 0.0)))
    def test_assign_export(self, update_mock):
        positions = np.array([[[3, 4], [0, 18]]])
        assignment = self.assigner.assign(positions, export=False)[0]

        self.assertEqual(update_mock.call_count, 2)

        # We receive a good assignment.
        self.assertIsInstance(assignment, dict)
        self.assertEqual(len(assignment), 2)
        self.assertEqual(len(assignment[1]), 3)
        self.assertEqual(len(assignment[2]), 2)

        pass_waypoint = assignment[1][1]
        self.assertIsInstance(pass_waypoint, Waypoint)
        self.assertEqual(pass_waypoint.name, Waypoint_Type.PASS)
        self.assertEqual(pass_waypoint.vehicle_id, 1)
        self.assertEqual(pass_waypoint.location.north, 3)
        self.assertEqual(pass_waypoint.location.east, 0)

        first_waypoint = assignment[1][2]
        self.assertIsInstance(first_waypoint, Waypoint)
        self.assertEqual(first_waypoint.name, Waypoint_Type.WAIT)
        self.assertEqual(first_waypoint.vehicle_id, 1)
        self.assertEqual(first_waypoint.location.north, 3)
        self.assertEqual(first_waypoint.location.east, 4)
        self.assertEqual(first_waypoint.wait_id, 2)
        self.assertEqual(first_waypoint.wait_count, 1)

        second_waypoint = assignment[2][1]
        self.assertEqual(second_waypoint.name, Waypoint_Type.WAIT)
        self.assertEqual(second_waypoint.vehicle_id, 2)
        self.assertEqual(second_waypoint.location.north, 0)
        self.assertEqual(second_waypoint.location.east, 18)
        self.assertEqual(second_waypoint.wait_id, 1)
        self.assertEqual(second_waypoint.wait_count, 1)

    def test_get_new_direction(self):
        cases = [
            # current direction, new north, new east, expected new direction
            [Line_Follower_Direction.DOWN, 0, 0, Line_Follower_Direction.DOWN],
            [Line_Follower_Direction.UP, 1, 0, Line_Follower_Direction.UP],
            [Line_Follower_Direction.RIGHT, 1, 0, Line_Follower_Direction.UP],
            [Line_Follower_Direction.UP, 0, 1, Line_Follower_Direction.RIGHT],
            [Line_Follower_Direction.LEFT, 0, 1, Line_Follower_Direction.RIGHT],
            [Line_Follower_Direction.UP, -1, 1, Line_Follower_Direction.DOWN]
        ]

        msg = "Direction {0} to ({1},{2}) results in new direction {3}"
        self.assigner._current_positions = [(0, 0)]
        for case in cases:
            self.assigner._current_directions = [case[0]]
            new_position = (case[1], case[2])
            self.assertEqual(self.assigner._get_new_direction(0, new_position),
                             case[3], msg=msg.format(*case))
