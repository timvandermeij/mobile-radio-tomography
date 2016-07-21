# Core imports
from functools import partial

# Library imports
import numpy as np
import scipy.sparse
import scipy.optimize

# Package imports
from Reconstructor import Reconstructor

class Total_Variation_Reconstructor(Reconstructor):
    def __init__(self, arguments):
        """
        Initialize the total variation reconstructor object.
        """

        super(Total_Variation_Reconstructor, self).__init__(arguments)

        self._alpha = self._settings.get("alpha")
        self._beta = self._settings.get("beta")
        self._solver_method = self._settings.get("solver_method")
        self._solver_iterations = self._settings.get("solver_iterations")

        self._guess = None

    @property
    def type(self):
        """
        Get the type of the reconstructor.

        The type is equal to the name of the settings group.
        """

        return "reconstruction_total_variation_reconstructor"

    def execute(self, weight_matrix, rssi, buffer=None):
        """
        Perform the total variation algorithm. We aim to solve `Ax = b` where
        `A` is the weight matrix and `b` is a column vector of signal strength
        measurements. We solve this equation to obtain `x`, containing the
        intensities for the pixels of the reconstructed image. We smoothen the
        solution by minimizing the gradient. This reduces the number of
        differences between neighboring pixels.
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
        total_variation = partial(self._calculate_total_variation, A, b)
        total_variation_gradient = partial(self._calculate_total_variation_gradient, A, b)
        solution = scipy.optimize.minimize(total_variation, self._guess, options=options,
                                           jac=total_variation_gradient, method=self._solver_method)
        return solution.x

    def _calculate_total_variation(self, A, b, x):
        """
        Calculate the total variation for a given solution `x`. This method
        represents what will be minimized by SciPy's optimizer.

        Refer to the paper "Regularization methods for radio tomographic imaging"
        by Joey Wilson, Neal Patwari and Fernando Guevara Vasquez for the
        formula used for this method.
        """

        return (0.5 * np.linalg.norm((A * x) - b) +
                self._alpha * self._calculate_total_variation_factor(x))

    def _calculate_total_variation_factor(self, x):
        """
        Calculate the total variation factor for a given solution `x`. This factor
        is used in the method above to calculate the total variation of `x`.

        Refer to the paper "Regularization methods for radio tomographic imaging"
        by Joey Wilson, Neal Patwari and Fernando Guevara Vasquez for the
        formula used for this method.
        """

        return np.sum(np.sqrt(np.gradient(x) ** 2 + self._beta ** 2))

    def _calculate_total_variation_gradient(self, A, b, x):
        """
        Calculate the total variation gradient for a given solution `x`. We take
        the gradient, a vector of partial derivatives, to be equal to the total
        derivative (approximately the combination of the partial derivatives)
        and calculate that instead.
        """

        least_squares_derivative = ((A.T * A) * x) - (A.T * b)
        total_variation_factor_derivative = np.gradient(x) / np.sqrt(np.gradient(x) ** 2 + self._beta ** 2)

        return least_squares_derivative + self._alpha * total_variation_factor_derivative
