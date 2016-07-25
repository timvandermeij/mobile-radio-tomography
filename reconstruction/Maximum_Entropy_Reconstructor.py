# Core imports
from functools import partial

# Library imports
import numpy as np
import scipy.sparse
import scipy.optimize

# Package imports
from Reconstructor import Reconstructor

class Maximum_Entropy_Reconstructor(Reconstructor):
    def __init__(self, arguments):
        """
        Initialize the maximum entropy reconstructor object.
        """

        super(Maximum_Entropy_Reconstructor, self).__init__(arguments)

        self._alpha = self._settings.get("entropy_alpha")
        self._solver_method = self._settings.get("entropy_solver_method")
        self._solver_iterations = self._settings.get("entropy_solver_iterations")

        self._guess = None

    @property
    def type(self):
        """
        Get the type of the reconstructor.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_maximum_entropy_reconstructor"

    def execute(self, weight_matrix, rssi, buffer=None):
        """
        Perform the maximum entropy algorithm. We aim to solve `Ax = b` where
        `A` is the weight matrix and `b` is a column vector of signal strength
        measurements. We solve this equation to obtain `x`, containing the
        intensities for the pixels of the reconstructed image. We smoothen the
        solution by minimizing the maximum Shannon entropy. This reduces the
        number of differences between neighboring pixels.
        """

        if buffer is None:
            raise ValueError("Buffer has not been provided")

        A = scipy.sparse.csc_matrix(weight_matrix)
        b = rssi

        if self._guess is None:
            width, height = buffer.size
            self._guess = np.zeros(width * height)

        options = {
            "maxiter": self._solver_iterations
        }
        maximum_entropy = partial(self._calculate, A, b)
        solution = scipy.optimize.minimize(maximum_entropy, self._guess, options=options,
                                           method=self._solver_method)
        return solution.x

    def _calculate(self, A, b, x):
        """
        Calculate the maximum entropy for a given solution `x`. This method
        represents what will be minimized by SciPy's optimizer.

        Refer to the book "Handbook of image and video processing" (chapter 3.6,
        section 2.3) by Al Bovik for the formula used for this method.
        """

        return np.linalg.norm((A * x) - b) + self._alpha * self._calculate_factor(x)

    def _calculate_factor(self, x):
        """
        Calculate the maximum entropy factor for a given solution `x`. This factor
        is used in the method above to calculate the maximum entropy of `x`.

        Refer to the book "Handbook of image and video processing" (chapter 3.6,
        section 2.3) by Al Bovik for the formula used for this method.
        """

        total_pixels = float(x.size)
        unique_pixels = np.unique(x, return_counts=True)[1]
        probabilities = unique_pixels / total_pixels

        return -np.sum([p * np.log2(p) for p in probabilities])
