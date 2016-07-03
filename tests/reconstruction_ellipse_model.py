# Library imports
import numpy as np

# Package imports
from ..reconstruction.Ellipse_Model import Ellipse_Model
from ..settings.Arguments import Arguments
from reconstruction_model import ModelTestCase

class TestReconstructionEllipseModel(ModelTestCase):
    def setUp(self):
        super(TestReconstructionEllipseModel, self).setUp()

        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction_ellipse_model")

        self.model = Ellipse_Model(self.arguments)

    def test_initialization(self):
        # The lambda member variable must be set.
        self.assertEqual(self.model._lambda, self.settings.get("lambda"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.model.type, "reconstruction_ellipse_model")

    def test_assign(self):
        length, source_distances, destination_distances = self.get_assign_data()

        # The assigned weights must form an ellipse.
        weights = self.model.assign(length, source_distances,
                                    destination_distances)

        factor = 1.0 / np.sqrt(length)
        expected = np.array([
            # pylint: disable=bad-whitespace
            factor, factor, 0,      0,
            factor, factor, factor, 0,
            0,      factor, factor, factor,
            0,      0,      factor, factor
        ]).reshape(4, 4)

        self.assertTrue((weights == expected).all())
