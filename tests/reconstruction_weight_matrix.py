import numpy as np
from ..reconstruction.Snap_To_Boundary import Snap_To_Boundary
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..settings.Arguments import Arguments
from settings import SettingsTestCase

class TestReconstructionWeightMatrix(SettingsTestCase):
    def setUp(self):
        self.origin = [0, 0]
        self.size = [4, 4]
        self.pixels = self.size[0] * self.size[1]
        self.links = 10
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction_ellipse_model")
        self.weight_matrix = Weight_Matrix(self.arguments, self.origin,
                                           self.size)

    def test_initialization(self):
        # Verify that only `Arguments` objects can be used to initialize.
        with self.assertRaises(TypeError):
            Weight_Matrix(self.settings, self.origin, self.size)
        with self.assertRaises(TypeError):
            Weight_Matrix(None, self.origin, self.size)

        self.assertIsInstance(self.weight_matrix._distances, np.ndarray)
        self.assertEqual(self.weight_matrix._distances.shape, (0, self.pixels))
        self.assertIsInstance(self.weight_matrix._matrix, np.ndarray)
        self.assertEqual(self.weight_matrix._matrix.shape, (0, self.pixels))
        self.assertEqual(self.weight_matrix._origin, self.origin)
        self.assertEqual(self.weight_matrix._width, self.size[0])
        self.assertEqual(self.weight_matrix._height, self.size[1])
        self.assertIsInstance(self.weight_matrix._snapper, Snap_To_Boundary)
        self.assertIsInstance(self.weight_matrix._grid_x, np.ndarray)
        self.assertIsInstance(self.weight_matrix._grid_y, np.ndarray)

    def test_initialization_number_of_links(self):
        weight_matrix = Weight_Matrix(self.arguments, self.origin, self.size,
                                      number_of_links=self.links)
        self.assertEqual(weight_matrix._number_of_links, self.links)
        self.assertEqual(weight_matrix._distances.shape,
                         (self.links, self.pixels))
        self.assertEqual(weight_matrix._matrix.shape, (self.links, self.pixels))
        self.assertEqual(weight_matrix._link_count, 0)
        self.assertEqual(weight_matrix._distance_count, 0)

    def test_is_valid_point(self):
        # Only points that are outside the network are valid points.
        self.assertTrue(self.weight_matrix.is_valid_point((4, 4)))
        self.assertFalse(self.weight_matrix.is_valid_point((3, 3)))

    def test_update(self):
        # Unsnappable points should be ignored.
        self.assertIsNone(self.weight_matrix.update((0, 5), (5, 5)))

        # Snapped points that are equal should be ignored.
        self.assertIsNone(self.weight_matrix.update((4, 4), (5, 5)))

        # The weight matrix should not be correct yet.
        self.assertFalse(self.weight_matrix.check())

        # Points that create links that cover the network together should be 
        # accepted, and then make the weight matrix correct.
        for i in range(0, 4):
            points = [(0, i), (4, i)]
            self.assertEqual(self.weight_matrix.update(*points), points)
            points = [(i, 0), (i, 4)]
            self.assertEqual(self.weight_matrix.update(*points), points)

        self.assertTrue(self.weight_matrix.check())

    def test_update_snap_inside(self):
        weight_matrix = Weight_Matrix(self.arguments, self.origin, self.size,
                                      snap_inside=True, number_of_links=1)

        # Points inside the network should be accepted when `snap_inside` is 
        # enabled. They fill the matrix.
        self.assertEqual(weight_matrix.update((1, 2), (2, 3)), [(0, 1), (3, 4)])
        self.assertEqual(weight_matrix._link_count, 1)

        self.assertEqual(weight_matrix.update((2, 3), (3, 2)), [(1, 4), (4, 1)])
        self.assertEqual(weight_matrix._link_count, 2)

        self.assertEqual(weight_matrix._matrix.shape, (2, self.pixels))

    def test_check(self):
        # Matrices that constain non-zero columns must fail the test.
        self.weight_matrix._matrix = np.zeros((self.links, self.pixels))
        self.weight_matrix._matrix[:, 1] = 1
        self.assertEqual(self.weight_matrix.check(), False)

        # Matrices consisting of only non-zero columns must pass the test.
        self.weight_matrix._matrix = np.ones((self.links, self.pixels))
        self.assertEqual(self.weight_matrix.check(), True)

    def test_output(self):
        # The internal matrix must be returned.
        self.weight_matrix._matrix = np.random.random((self.links, self.pixels))
        self.assertTrue(np.array_equal(self.weight_matrix.output(),
                                       self.weight_matrix._matrix))

    def test_reset(self):
        for i in range(0, 4):
            self.weight_matrix.update((0, i), (4, i))
            self.weight_matrix.update((i, 0), (i, 4))

        self.assertTrue(self.weight_matrix.check())
        self.weight_matrix.reset()
        self.assertFalse(self.weight_matrix.check())
