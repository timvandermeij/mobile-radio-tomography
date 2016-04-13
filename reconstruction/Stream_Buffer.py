from Buffer import Buffer

class Stream_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the stream buffer object.
        """

        super(Stream_Buffer, self).__init__(options)

        self._number_of_sensors = options["number_of_sensors"]
        self._origin = options["origin"]
        self._size = options["size"]
