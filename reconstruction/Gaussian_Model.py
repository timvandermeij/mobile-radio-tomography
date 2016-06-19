# Library imports
import numpy as np

# Package imports
from Model import Model

class Gaussian_Model(Model):
    """
    Signal disruption model based on the log-distance path loss model
    where environmental noise is modeled using a Gaussian function.
    """

    def __init__(self, arguments):
        """
        Initialize the Gaussian model.
        """

        super(Gaussian_Model, self).__init__(arguments)

        self._sigma = self._settings.get("sigma")

    @property
    def type(self):
        """
        Get the type of the signal disruption model.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_gaussian_model"

    def assign(self, length, source_distances, destination_distances):
        """
        Assign weights to all pixels on the grid for a given link.

        Provided are the `length` of the link, calculated using the Pythagorean
        theorem, and the `source_distances` and `destination_distances`, both
        NumPy arrays containing the distances from, respectively, the source
        and destination sensor locations to each center of a pixel on the grid.
        """

        return self._gaussian((source_distances + destination_distances) - length)

    def _gaussian(self, x):
        """
        Get the value for a given `x` coordinate of a Gaussian function
        with alpha value 1 and mu value 0.
        """

        return np.exp(-((x ** 2) / (2 * (self._sigma ** 2))))
