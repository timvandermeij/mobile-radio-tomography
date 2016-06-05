import numpy as np
from ..reconstruction.Snap_To_Boundary import Snap_To_Boundary
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..settings.Arguments import Arguments
from settings import SettingsTestCase

class TestReconstructionWeightMatrix(SettingsTestCase):
    def setUp(self):
        self.origin = [0, 0]
        self.size = [4, 4]
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction_weight_matrix")
        self.weight_matrix = Weight_Matrix(self.settings, self.origin, self.size)

    def test_initialization(self):
        # Verify that only `Settings` and `Arguments` objects can be used to initialize.
        Weight_Matrix(self.arguments, self.origin, self.size)
        Weight_Matrix(self.settings, self.origin, self.size)
        with self.assertRaises(ValueError):
            Weight_Matrix(None, self.origin, self.size)

        self.assertEqual(self.weight_matrix._lambda, self.settings.get("distance_lambda"))
        self.assertEqual(self.weight_matrix._origin, self.origin)
        self.assertEqual(self.weight_matrix._width, self.size[0])
        self.assertEqual(self.weight_matrix._height, self.size[1])
        self.assertIsInstance(self.weight_matrix._snapper, Snap_To_Boundary)
        self.assertIsInstance(self.weight_matrix._distances, np.ndarray)
        self.assertIsInstance(self.weight_matrix._matrix, np.ndarray)
        self.assertIsInstance(self.weight_matrix._gridX, np.ndarray)
        self.assertIsInstance(self.weight_matrix._gridY, np.ndarray)

    def test_is_valid_point(self):
        # Only points that are outside the network are valid points.
        self.assertTrue(self.weight_matrix.is_valid_point((4, 4)))
        self.assertFalse(self.weight_matrix.is_valid_point((3, 3)))

    def test_update(self):
        # Unsnappable points should be ignored.
        self.assertEqual(self.weight_matrix.update((0, 5), (5, 5)), None)

        # Snapped points that are equal should be ignored.
        self.assertEqual(self.weight_matrix.update((4, 4), (5, 5)), None)

        # The weight matrix should not be correct yet.
        self.assertFalse(self.weight_matrix.check())

        for i in range(0, 4):
            points = [(0, i), (4, i)]
            self.assertEqual(self.weight_matrix.update(*points), points)
            points = [(i, 0), (i, 4)]
            self.assertEqual(self.weight_matrix.update(*points), points)

        self.assertTrue(self.weight_matrix.check())

    def test_check(self):
        # Matrices not consisting entirely of non-zero columns must fail the test.
        self.weight_matrix._matrix = np.zeros(self.size)
        self.assertEqual(self.weight_matrix.check(), False)

        # Matrices consisting of only non-zero columns must pass the test.
        self.weight_matrix._matrix = np.ones(self.size)
        self.assertEqual(self.weight_matrix.check(), True)

    def test_output(self):
        # The internal matrix must be returned.
        self.weight_matrix._matrix = np.random.random(self.size)
        self.assertTrue((self.weight_matrix.output() == self.weight_matrix._matrix).all())

    def test_reset(self):
        for i in range(0, 4):
            self.weight_matrix.update((0, i), (4, i))
            self.weight_matrix.update((i, 0), (i, 4))

        self.assertTrue(self.weight_matrix.check())
        self.weight_matrix.reset()
        self.assertFalse(self.weight_matrix.check())
