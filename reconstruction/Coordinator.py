from Weight_Matrix import Weight_Matrix

class Coordinator(object):
    def __init__(self, arguments, buffer):
        """
        Initialize the coordinator object.

        The coordinator maintains the weight matrix and the RSSI vector for the
        reconstruction process.
        """

        self._weight_matrix = Weight_Matrix(arguments, buffer.origin, buffer.size)
        self._rssi = []
        self._endpoints = []

    def get_weight_matrix(self):
        """
        Get the weight matrix (as a NumPy array).
        """

        return self._weight_matrix.output()

    def get_rssi_vector(self):
        """
        Get the RSSI vector (as a list).
        """

        return self._rssi

    def update(self, packet):
        """
        Update the weight matrix and RSSI vector given an XBee packet object `packet`.
        """

        source = (packet.get("from_latitude"), packet.get("from_longitude"))
        destination = (packet.get("to_latitude"), packet.get("to_longitude"))
        rssi = packet.get("rssi")

        # If the endpoints already exist (i.e., the link has already been measured before),
        # we can simply replace the existing RSSI value for the link. This keeps both the
        # weight matrix and the RSSI vector minimal.
        endpoints = (source, destination)
        if endpoints in self._endpoints:
            index = self._endpoints.index(endpoints)
            self._rssi[index] = rssi
            return True

        # If the weight matrix has been updated, store the RSSI value.
        if self._weight_matrix.update(source, destination) is not None:
            self._rssi.append(rssi)
            self._endpoints.append(endpoints)
            return True

        return False
