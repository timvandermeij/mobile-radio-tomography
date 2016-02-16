class Reconstructor(object):
    def __init__(self, settings):
        """
        Initialize the reconstructor object.
        """

        self._settings = settings

    def execute(self):
        raise NotImplementedError("Subclasses must implement execute(weight_matrix, rssi)")
