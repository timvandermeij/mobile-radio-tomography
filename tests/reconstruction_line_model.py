# Library imports
import numpy as np

# Package imports
from ..reconstruction.Line_Model import Line_Model
from ..settings.Arguments import Arguments
from reconstruction_model import ModelTestCase

class TestReconstructionLineModel(ModelTestCase):
    def setUp(self):
        super(TestReconstructionLineModel, self).setUp()

        self.arguments = Arguments("settings.json", [])
        self.settings = self.arguments.get_settings("reconstruction_line_model")

        self.model = Line_Model(self.arguments)

    def test_initialization(self):
        # The threshold member variable must be set.
        self.assertEqual(self.model._threshold, self.settings.get("threshold"))

    def test_type(self):
        # The `type` property must be implemented and correct.
        self.assertEqual(self.model.type, "reconstruction_line_model")

    def test_assign(self):
        length, source_distances, destination_distances = self.get_assign_data()

        # The assigned weights must form a line. Note that this is the most 
        # difficult case to determine which pixels are intersected because the 
        # distances from the pixel centers to the endpoints are the largest 
        # when the line is perfectly diagonal. Our algorithm finds that not 
        # only the pixels that are strictly on the diagonal are intersected, 
        # but also some pixels very close to them. Technically their corners 
        # are indeed intersected, but opinions may differ on whether or not 
        # those pixels should be considered intersected.
        weights = self.model.assign(length, source_distances,
                                    destination_distances)
        expected = np.array([
            1, 1, 0, 0,
            1, 1, 1, 0,
            0, 1, 1, 1,
            0, 0, 1, 1
        ]).reshape(4, 4)

        self.assertTrue((weights == expected).all())
