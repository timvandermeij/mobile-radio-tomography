# Package imports
from ..settings import Arguments

class Model(object):
    """
    Base class for all signal disruption models.

    This class is responsible for setting up the basic characteristics
    of the signal disruption model.
    """

    def __init__(self, arguments):
        """
        Initialize the signal disruption model.

        The `arguments` parameter is used to load settings for a specific
        signal disruption model type.

        Classes that inherit this base class may extend this method.
        """

        # Load settings for a specific signal disruption model type.
        if isinstance(arguments, Arguments):
            self._settings = arguments.get_settings(self.type)
        else:
            raise TypeError("'arguments' must be an instance of Arguments")

    @property
    def type(self):
        raise NotImplementedError("Subclasses must implement the `type` property")

    def assign(self, length, source_distances, destination_distances):
        raise NotImplementedError("Subclasses must implement `assign(length, \
                                   source_distances, destination_distances)`")
