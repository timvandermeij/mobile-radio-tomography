# Package imports
from Model import Model

class Line_Model(Model):
    """
    Signal disruption model based on the assumption that the signal strength of
    a link is primarily determined by object lying on the line-of-sight path.
    """

    def __init__(self, arguments):
        """
        Initialize the line model.
        """

        super(Line_Model, self).__init__(arguments)

        self._threshold = self._settings.get("threshold")

    @property
    def type(self):
        """
        Get the type of the signal disruption model.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_line_model"

    def assign(self, length, source_distances, destination_distances):
        """
        Assign weights to all pixels on the grid for a given link.

        Provided are the `length` of the link, calculated using the Pythagorean
        theorem, and the `source_distances` and `destination_distances`, both
        NumPy arrays containing the distances from, respectively, the source
        and destination sensor locations to each center of a pixel on the grid.
        """

        return (source_distances + destination_distances) - length < self._threshold
