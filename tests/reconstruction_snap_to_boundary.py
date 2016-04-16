import unittest
from ..reconstruction.Snap_To_Boundary import Snap_To_Boundary, Point

class TestReconstructionSnapToBoundary(unittest.TestCase):
    def setUp(self):
        origin = [0, 2]
        width = 4
        height = 4
        self.snapper = Snap_To_Boundary(origin, width, height)

    def test_same_point(self):
        # Equal start and end points are rejected.
        self.assertIsNone(self.snapper.execute([2, 6], [2, 6]))

    def test_is_outside(self):
        # Start point inside the network are rejected.
        self.assertFalse(self.snapper.is_outside(Point(1, 3)))
        self.assertTrue(self.snapper.is_outside(Point(5, 3)))
        self.assertIsNone(self.snapper.execute([1, 3], [5, 3]))

        # End point inside the network are rejected.
        self.assertTrue(self.snapper.is_outside(Point(-1, 5)))
        self.assertFalse(self.snapper.is_outside(Point(3, 3)))
        self.assertIsNone(self.snapper.execute([-1, 5], [3, 3]))

        # Both start and end point inside the network are rejected.
        self.assertIsNone(self.snapper.execute([1, 3], [3, 3]))

        # Both start and end point outside the network are fine.
        self.assertIsNotNone(self.snapper.execute([-1, 5], [5, 3]))

    def test_is_intersecting(self):
        # Lines that do not intersect any boundary are rejected.
        self.assertIsNone(self.snapper.execute([2, 0], [5, 2]))

        # Lines that intersect at least one boundary are fine.
        self.assertIsNotNone(self.snapper.execute([2, 1], [5, 3]))

        # Horizontal and vertical lines do not cause a division by zero error.
        self.assertIsNone(self.snapper.execute([-1, 7], [5, 7]))
        self.assertIsNone(self.snapper.execute([5, 1], [5, 7]))

    def test_is_on_boundary(self):
        # Points that are already on a boundary remain the same.
        expected = [Point(2, 6), Point(2, 2)]
        self.assertEqual(self.snapper.execute([2, 6], [2, 2]), expected)

        expected = [Point(0, 3), Point(4, 3)]
        self.assertEqual(self.snapper.execute([0, 3], [4, 3]), expected)

    def test_execute(self):
        # Left and right boundary, decreasing line (negative delta y).
        expected = [Point(0, 14/3.0), Point(4, 10/3.0)]
        self.assertEqual(self.snapper.execute([-1, 5], [5, 3]), expected)

        # Left and right boundary, increasing line (positive delta y).
        expected = [Point(0, 31/6.0), Point(4, 35/6.0)]
        self.assertEqual(self.snapper.execute([-1, 5], [5, 6]), expected)

        # Top and bottom boundary, decreasing line (negative delta y).
        expected = [Point(1/3.0, 2), Point(5/3.0, 6)]
        self.assertEqual(self.snapper.execute([0, 1], [2, 7]), expected)

        # Top and bottom boundary, increasing line (positive delta y).
        expected = [Point(17/6.0, 2), Point(13/6.0, 6)]
        self.assertEqual(self.snapper.execute([3, 1], [2, 7]), expected)

        # Horizontal lines are handled properly.
        expected = [Point(0, 4), Point(4, 4)]
        self.assertEqual(self.snapper.execute([-1, 4], [5, 4]), expected)

        # Vertical lines are handled properly.
        expected = [Point(2, 2), Point(2, 6)]
        self.assertEqual(self.snapper.execute([2, 1], [2, 7]), expected)

    def test_execute_snap_inside(self):
        self.snapper._snap_inside = True

        # Left and right boundary, decreasing line (negative delta y).
        expected = [Point(0, 11/2.0), Point(4, 7/2.0)]
        self.assertEqual(self.snapper.execute([1, 5], [3, 4]), expected)

        # Left and right boundary, increasing line (positive delta y).
        expected = [Point(0, 5/2.0), Point(4, 9/2.0)]
        self.assertEqual(self.snapper.execute([1, 3], [3, 4]), expected)

        # Top and bottom boundary, decreasing line (negative delta y).
        expected = [Point(1/2.0, 6), Point(5/2.0, 2)]
        self.assertEqual(self.snapper.execute([1, 5], [2, 3]), expected)

        # Top and bottom boundary, increasing line (positive delta y).
        expected = [Point(1/2.0, 2), Point(5/2.0, 6)]
        self.assertEqual(self.snapper.execute([1, 3], [2, 5]), expected)

        # Left and top boundary
        expected = [Point(0, 3), Point(3, 6)]
        self.assertEqual(self.snapper.execute([1, 4], [2, 5]), expected)

        # Top and right boundary
        expected = [Point(1, 6), Point(4, 3)]
        self.assertEqual(self.snapper.execute([2, 5], [3, 4]), expected)

        # Bottom and right boundary
        expected = [Point(1, 2), Point(4, 5)]
        self.assertEqual(self.snapper.execute([2, 3], [3, 4]), expected)

        # Left and bottom boundary
        expected = [Point(0, 5), Point(3, 2)]
        self.assertEqual(self.snapper.execute([1, 4], [2, 3]), expected)

        # Horizontal lines are handled properly.
        expected = [Point(0, 4), Point(4, 4)]
        self.assertEqual(self.snapper.execute([1, 4], [3, 4]), expected)

        # Vertical lines are handled properly.
        expected = [Point(2, 2), Point(2, 6)]
        self.assertEqual(self.snapper.execute([2, 3], [2, 5]), expected)

        # One line inside and one line on boundary makes inside line snap away.
        # Left (on boundary) and top (inside) boundary.
        expected = [Point(0, 4), Point(2, 6)]
        self.assertEqual(self.snapper.execute([0, 4], [1, 5]), expected)

        # Left (from boundary) and bottom (inside) boundary.
        expected = [Point(0, 4-1/2.0), Point(3, 2)]
        self.assertEqual(self.snapper.execute([-1, 4], [1, 3]), expected)

        # Top (far from boundary) and bottom (inside) boundary.
        expected = [Point(7/2.0, 6), Point(3/2.0, 2)]
        self.assertEqual(self.snapper.execute([5, 9], [2, 3]), expected)

        # (Top) left (inside) and right (from boundary).
        # Note that the points are internally resorted to snap the outside 
        # point first, but the result is ordered like the input arguments.
        expected = [Point(0, 6), Point(4, 4)]
        self.assertEqual(self.snapper.execute([2, 5], [6, 3]), expected)
