# Core imports
from functools import partial

# Library imports
import numpy as np
import scipy.sparse
import scipy.optimize

# Package imports
from Reconstructor import Reconstructor
from ..settings import Arguments, Settings

class Total_Variation_Reconstructor(Reconstructor):
    def __init__(self, settings):
        """
        Initialize the total variation reconstructor object.
        """

        super(Total_Variation_Reconstructor, self).__init__(settings)

        if isinstance(settings, Arguments):
            settings = settings.get_settings("reconstruction_total_variation_reconstructor")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._alpha = settings.get("alpha")
        self._beta = settings.get("beta")
        self._solver_method = settings.get("solver_method")
        self._solver_iterations = settings.get("solver_iterations")

        self._D = None
        self._guess = None

    def execute(self, weight_matrix, rssi, buffer=None):
        """
        Perform the total variation algorithm. We aim to solve `Ax = b` where
        `A` is the weight matrix and `b` is a column vector of signal strength
        measurements. We solve this equation to obtain `x`, containing the
        intensities for the pixels of the reconstructed image. We smoothen the
        solution with a difference matrix that approximates the derivative of
        the intended image. This ensures that there are as few differences as
        possible between connected pixels.
        """

        if buffer is None:
            raise ValueError("Buffer must be provided to create the difference matrix")

        A = scipy.sparse.csc_matrix(weight_matrix)
        b = rssi

        # Create the difference matrix for the total variation factor.
        width, height = buffer.size
        if self._D is None:
            self._D = self._create_difference_matrix(width, height)

        # Solve the total variation problem.
        if self._guess is None:
            self._guess = np.zeros(width * height)

        options = {
            "maxiter": self._solver_iterations
        }
        total_variation = partial(self._calculate_total_variation, A, b)
        total_variation_gradient = partial(self._calculate_total_variation_gradient, A, b)
        solution = scipy.optimize.minimize(total_variation, self._guess, options=options,
                                           jac=total_variation_gradient, method=self._solver_method)
        return solution.x

    def _create_difference_matrix(self, width, height):
        """
        Create the difference matrix for the total variation factor.

        The difference matrix is the sum of the difference matrices in all four
        directions: left, right, up and down. These matrices approximate the
        derivate of the desired image in a certain direction. We use a simple
        [-1, 1] convolution kernel, as used for the forward and backward
        difference measures.

        The difference matrix is used to ensure that the desired image is
        smooth, i.e., that there as as few differences between neighboring
        pixels as possible. In fact, one can think of the difference matrix
        as an edge detection operation: edges of the objects are maintained,
        but noise outside of the edges is suppressed as much as possible.
        """

        number_of_pixels = width * height

        left_difference_matrix = np.zeros((number_of_pixels, number_of_pixels))
        right_difference_matrix = np.zeros((number_of_pixels, number_of_pixels))
        up_difference_matrix = np.zeros((number_of_pixels, number_of_pixels))
        down_difference_matrix = np.zeros((number_of_pixels, number_of_pixels))

        for x in xrange(width):
            for y in xrange(height):
                index = x + y * width

                if x > 0:
                    left_difference_matrix[index][index - 1] = -1
                    left_difference_matrix[index][index] = 1
                if x < width - 1:
                    right_difference_matrix[index][index] = 1
                    right_difference_matrix[index][index + 1] = -1
                if y > 0:
                    up_difference_matrix[index][index - width] = -1
                    up_difference_matrix[index][index] = 1
                if y < height - 1:
                    down_difference_matrix[index][index] = 1
                    down_difference_matrix[index][index + width] = -1

        return scipy.sparse.csc_matrix(left_difference_matrix + right_difference_matrix +
                                       up_difference_matrix + down_difference_matrix)

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

        return sum(np.sqrt((self._D * x) ** 2 + self._beta ** 2))

    def _calculate_total_variation_gradient(self, A, b, x):
        """
        Calculate the total variation gradient for a given solution `x`. We take
        the gradient, a vector of partial derivatives, to be equal to the total
        derivative (approximately the combination of the partial derivatives)
        and calculate that instead.
        """

        least_squares_derivative = ((A.T * A) * x) - (A.T * b)
        total_variation_factor_derivative = (self._D * x) / np.sqrt((self._D * x) ** 2 + self._beta ** 2)

        return least_squares_derivative + self._alpha * total_variation_factor_derivative
