import unittest
import numpy as np
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..settings.Arguments import Arguments

class TestReconstructionWeightMatrix(unittest.TestCase):
    def setUp(self):
        origin = [0,0]
        size = [4,4]
        self.arguments = Arguments("settings.json", [])
        self.weight_matrix = Weight_Matrix(self.arguments, origin, size)

    def test_update(self):
        # Lines that cannot be snapped to the boundary should return False.
        self.assertEqual(self.weight_matrix.update((0, 5), (5, 5)), None)

        # The weight matrix should not be correct yet.
        self.assertFalse(self.weight_matrix.check())

        for i in range(0, 4):
            points = [(0, i), (4, i)]
            self.assertEqual(self.weight_matrix.update(*points), points)
            points = [(i, 0), (i, 4)]
            self.assertEqual(self.weight_matrix.update(*points), points)

        self.assertTrue(self.weight_matrix.check())

    def test_reset(self):
        for i in range(0, 4):
            self.weight_matrix.update((0, i), (4, i))
            self.weight_matrix.update((i, 0), (i, 4))

        self.assertTrue(self.weight_matrix.check())

        self.weight_matrix.reset()

        self.assertFalse(self.weight_matrix.check())
