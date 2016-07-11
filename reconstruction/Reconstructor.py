from ..settings import Arguments

# pylint: disable=undefined-all-variable
__all__ = [
    "SVD_Reconstructor", "Total_Variation_Reconstructor", "Truncated_SVD_Reconstructor"
]

class Reconstructor(object):
    def __init__(self, arguments):
        """
        Initialize the reconstructor object.
        """

        if isinstance(arguments, Arguments):
            try:
                self._settings = arguments.get_settings(self.type)
            except KeyError:
                # Reconstructors do not need to have associated settings,
                # such as the SVD reconstructor.
                self._settings = None
        else:
            raise TypeError("'arguments' must be an instance of Arguments")

    @property
    def type(self):
        raise NotImplementedError("Subclasses must implement the `type` property")

    def execute(self, weight_matrix, rssi, buffer=None):
        raise NotImplementedError("Subclasses must implement execute(weight_matrix, rssi, buffer)")
