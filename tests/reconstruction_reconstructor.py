import numpy as np
from ..reconstruction.Reconstructor import Reconstructor
from ..settings.Arguments import Arguments
from settings import SettingsTestCase

class TestReconstructionReconstructor(SettingsTestCase):
    def setUp(self):
        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction")
        self.reconstructor = Reconstructor(self.settings)

    def test_initialize(self):
        # Verify that settings for the reconstructor are available.
        self.assertEqual(self.reconstructor._settings, self.settings)

    def test_execute(self):
        # Verify that the interface requires subclasses to implement
        # the `execute` method.
        with self.assertRaises(NotImplementedError):
            self.reconstructor.execute(np.empty(0), [])
