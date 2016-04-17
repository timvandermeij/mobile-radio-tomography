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

        # If the weight matrix has been updated, store the RSSI value.
        if self._weight_matrix.update(source, destination) is not None:
            self._rssi.append(packet.get("rssi"))
            return True

        return False
