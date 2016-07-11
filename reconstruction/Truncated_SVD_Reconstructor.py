import numpy as np
import scipy.sparse.linalg
from Reconstructor import Reconstructor

class Truncated_SVD_Reconstructor(Reconstructor):
    def __init__(self, arguments):
        """
        Initialize the truncated SVD reconstructor object.
        """

        super(Truncated_SVD_Reconstructor, self).__init__(arguments)

        self._singular_values = self._settings.get("singular_values")

    @property
    def type(self):
        """
        Get the type of the reconstructor.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_truncated_svd_reconstructor"

    def execute(self, weight_matrix, rssi, buffer=None):
        """
        Perform the singular value decomposition algorithm. We aim to solve
        `Ax = b` where `A` is the weight matrix and `b` is a column vector
        of signal strength measurements. We solve this equation to obtain
        `x`, containing the intensities for the pixels of the reconstructed
        image. We stabilize the solution by using only the `k` largest
        singular values.
        """

        A = weight_matrix
        b = rssi
        U, S, Vt = scipy.sparse.linalg.svds(A, self._singular_values)
        A_inv = np.dot(np.dot(Vt.T, np.diag(np.reciprocal(S))), U.T)
        return np.dot(A_inv, b)
