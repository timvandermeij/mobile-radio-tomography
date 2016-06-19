# Core imports
import unittest

# Library imports
from mock import patch, PropertyMock
import numpy as np

# Package imports
from ..reconstruction.Model import Model
from ..settings.Arguments import Arguments

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

    def test_execute(self):
        # Verify that the interface requires subclasses to implement
        # the `execute(link_length, source_distances, destination_distances)` method.
        with self.assertRaises(NotImplementedError):
            self.model.execute(42, np.empty(0), np.empty(0))
