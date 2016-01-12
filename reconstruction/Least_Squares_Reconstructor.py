import numpy as np

class Least_Squares_Reconstructor(object):
    def __init__(self, weight_matrix):
        """
        Initialize the least-squares reconstructor object.
        """

        self._weight_matrix = weight_matrix

    def execute(self, rssi_values):
        """
        Perform the least-squares algorithm. We aim to solve
        `Ax = b` where `A` is the weight matrix and `b` is a column
        vector of signal strength measurements. We solve this
        equation to obtain `x`, containing the intensities for the
        pixels of the reconstructed image.
        """

        A = self._weight_matrix
        b = rssi_values
        return np.linalg.lstsq(A, b)[0]
