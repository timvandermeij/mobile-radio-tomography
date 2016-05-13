import numpy as np
from Reconstructor import Reconstructor

class Least_Squares_Reconstructor(Reconstructor):
    def __init__(self, settings):
        """
        Initialize the least-squares reconstructor object.
        """

        super(Least_Squares_Reconstructor, self).__init__(settings)

    def execute(self, weight_matrix, rssi, buffer=None, guess=None):
        """
        Perform the least-squares algorithm. We aim to solve
        `Ax = b` where `A` is the weight matrix and `b` is a column
        vector of signal strength measurements. We solve this
        equation to obtain `x`, containing the intensities for the
        pixels of the reconstructed image.
        """

        A = weight_matrix
        b = rssi
        return np.linalg.lstsq(A, b)[0]
