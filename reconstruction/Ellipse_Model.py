# Library imports
import numpy as np

# Package imports
from Model import Model

class Ellipse_Model(Model):
    """
    Signal disruption model based on the definition of Fresnel zones,
    modeled by an ellipse with minor axis diameter lambda.
    """

    def __init__(self, arguments):
        """
        Initialize the ellipse model.
        """

        super(Ellipse_Model, self).__init__(arguments)

        self._lambda = self._settings.get("lambda")

    @property
    def type(self):
        """
        Get the type of the signal disruption model.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_ellipse_model"

    def assign(self, length, source_distances, destination_distances):
        """
        Assign weights to all pixels on the grid for a given link.

        Provided are the `length` of the link, calculated using the Pythagorean
        theorem, and the `source_distances` and `destination_distances`, both
        NumPy arrays containing the distances from, respectively, the source
        and destination sensor locations to each center of a pixel on the grid.
        """

        weights = (source_distances + destination_distances < length + self._lambda)
        return (1.0 / np.sqrt(length)) * weights
