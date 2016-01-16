class Reconstructor(object):
    def __init__(self, weight_matrix):
        """
        Initialize the reconstructor object.
        """

        self._weight_matrix = weight_matrix

    def execute(self):
        raise NotImplementedError("Subclasses must implement execute(rssi_values)")
