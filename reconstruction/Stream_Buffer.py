from Buffer import Buffer

class Stream_Buffer(Buffer):
    def __init__(self, options=None):
        """
        Initialize the stream buffer object.
        """

        super(Stream_Buffer, self).__init__(options)

        if options is None:
            raise ValueError("No origin and size have been provided.")

        self._origin = options["origin"]
        self._size = options["size"]
