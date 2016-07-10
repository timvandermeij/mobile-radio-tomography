import numpy as np
from mock import patch, PropertyMock
from ..reconstruction.Reconstructor import Reconstructor
from ..settings.Arguments import Arguments
from settings import SettingsTestCase

class TestReconstructionReconstructor(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction")

        type_mock = PropertyMock(return_value="reconstruction")
        with patch.object(Reconstructor, "type", new_callable=type_mock):
            self.reconstructor = Reconstructor(self.arguments)

    def test_initialization(self):
        # Verify that only `Arguments` objects can be used to initialize.
        with self.assertRaises(TypeError):
            Reconstructor(self.settings)
        with self.assertRaises(TypeError):
            Reconstructor(None)

        # Reconstructors do not need to have associated settings.
        type_mock = PropertyMock(return_value="reconstruction_svd_reconstructor")
        with patch.object(Reconstructor, "type", new_callable=type_mock):
            reconstructor = Reconstructor(self.arguments)

            self.assertEqual(reconstructor._settings, None)

        # Verify that settings for the reconstructor are available.
        self.assertEqual(self.reconstructor._settings, self.settings)

    def test_type(self):
        # Verify that the interface requires subclasses to implement
        # the `type` property.
        with self.assertRaises(NotImplementedError):
            dummy = self.reconstructor.type

    def test_execute(self):
        # Verify that the interface requires subclasses to implement
        # the `execute` method.
        with self.assertRaises(NotImplementedError):
            self.reconstructor.execute(np.empty(0), [])
