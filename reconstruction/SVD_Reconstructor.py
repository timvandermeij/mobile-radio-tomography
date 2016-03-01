import numpy as np
from Reconstructor import Reconstructor

class SVD_Reconstructor(Reconstructor):
    def __init__(self, settings):
        """
        Initialize the SVD reconstructor object.
        """

        super(SVD_Reconstructor, self).__init__(settings)

    def execute(self, weight_matrix, rssi):
        """
        Perform the singular value decomposition algorithm. We aim to solve
        `Ax = b` where `A` is the weight matrix and `b` is a column vector
        of signal strength measurements. We solve this equation to obtain
        `x`, containing the intensities for the pixels of the reconstructed
        image.
        """

        A = weight_matrix
        b = rssi
        U, S, Vt = np.linalg.svd(A, full_matrices=False)
        A_inv = np.dot(np.dot(Vt.T, np.diag(np.reciprocal(S))), U.T)
        return np.dot(A_inv, b)