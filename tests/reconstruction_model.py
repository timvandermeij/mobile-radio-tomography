# Core imports
import unittest

# Library imports
from mock import patch, PropertyMock
import numpy as np

# Package imports
from ..reconstruction.Model import Model
from ..settings.Arguments import Arguments

class ModelTestCase(unittest.TestCase):
    """
    Test case for the signal disruption model classes. It provides
    example data for testing weight assignment.
    """

    def get_assign_data(self):
        """
        Generate data for testing the `assign` method of `Model` classes.
        """

        def distance(x, y):
            """
            Helper function to calculate the distance from location
            (0, 0) to the pixel center location of pixel (x, y).
            """

            return np.sqrt((x + 0.5) ** 2 + (y + 0.5) ** 2)

        # The grid contains 16 pixels (four by four). The link goes from
        # location (0, 0) to location (4, 4). Location (0, 0) is located
        # in the top left corner and location (4, 4) is located in the
        # bottom right corner of the grid.
        length = np.sqrt(4 ** 2 + 4 ** 2)
        source_distances = np.array([
            distance(0, 0), distance(1, 0), distance(2, 0), distance(3, 0),
            distance(0, 1), distance(1, 1), distance(2, 1), distance(3, 1),
            distance(0, 2), distance(1, 2), distance(2, 2), distance(3, 2),
            distance(0, 3), distance(1, 3), distance(2, 3), distance(3, 3)
        ]).reshape(4, 4)
        destination_distances = np.flipud(np.fliplr(source_distances))

        return length, source_distances, destination_distances

class TestReconstructionModel(unittest.TestCase):
    def setUp(self):
        super(TestReconstructionModel, self).setUp()

        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction")

        type_mock = PropertyMock(return_value="reconstruction")
        with patch.object(Model, "type", new_callable=type_mock):
            self.model = Model(self.arguments)

    def test_initialization(self):
        # Not providing an `Arguments` object raises an exception.
        with self.assertRaises(TypeError):
            Model(None)

        # The settings must be loaded when an `Arguments` object is provided.
        self.assertEqual(self.model._settings, self.settings)

    def test_type(self):
        # Verify that the interface requires subclasses to implement
        # the `type` property.
        with self.assertRaises(NotImplementedError):
            dummy = self.model.type

    def test_assign(self):
        # Verify that the interface requires subclasses to implement
        # the `assign(length, source_distances, destination_distances)` method.
        with self.assertRaises(NotImplementedError):
            self.model.assign(42, np.empty(0), np.empty(0))
