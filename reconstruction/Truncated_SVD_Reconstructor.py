import numpy as np
import scipy as sp
import scipy.sparse.linalg

class Truncated_SVD_Reconstructor(object):
    def __init__(self, weight_matrix):
        """
        Initialize the truncated SVD reconstructor object.
        """

        self._weight_matrix = weight_matrix

    def execute(self, rssi_values):
        """
        Perform the singular value decomposition algorithm. We aim to solve
        `Ax = b` where `A` is the weight matrix and `b` is a column vector
        of signal strength measurements. We solve this equation to obtain
        `x`, containing the intensities for the pixels of the reconstructed
        image. We stabilize the solution by using only the `k` largest
        singular values.
        """

        A = self._weight_matrix
        b = rssi_values
        k = 100
        U, S, Vt = sp.sparse.linalg.svds(A, k)
        A_inv = np.dot(np.dot(Vt.T, np.diag(np.reciprocal(S))), U.T)
        return np.dot(A_inv, b)
