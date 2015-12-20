import numpy as np

class Reconstructor(object):
    def __init__(self, weight_matrix):
        """
        Initialize the reconstructor object.
        """

        self.weight_matrix = weight_matrix

    def execute(self, rssi_values):
        """
        Perform the least-squares algorithm. We aim to solve
        `ax = b` where `a` is the weight matrix and `b` is a column
        vector of signal strength measurements. We solve this
        equation to obtain `x`, containing the intensities for the
        pixels of the reconstructed image.
        """

        a = self.weight_matrix
        b = rssi_values
        return np.linalg.lstsq(a, b)[0]
