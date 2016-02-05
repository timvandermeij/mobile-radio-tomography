import math
import numpy as np

from ..reconstruction.Snap_To_Boundary import Snap_To_Boundary
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..settings import Arguments

class Problem(object):
    """
    Generic problem statement structure.
    
    A problem consists of a dimsension of the input variables, the domains of 
    the input variables, objectives and constraints. The input vectors are 
    also generated, mutated and evaluated for feasibility and objective 
    fitness here.
    """

    def __init__(self, dim, domain=None):
        """
        Initialize a problem with the dimension of the solution variable sets,
        and the domains of each of the variables.

        The dimension is an integer >= 0 that determines the number of 
        variables used in both the linear programming objective functions and 
        the constraints.
        The domain is then a tuple containing the minimal and maximal values of
        these variables. The values can be scalar values, or each can be
        a numpy vector containing the bound value for every variable in order.
        If the tuple has a third component, then this value determines
        whether the variables are binary or real. Again, this can either be
        `True` to add constraints to make all variables binary, or it can be
        a numpy array of booleans that determine which variables are binary,
        in order.
        """

        self.dim = dim
        if domain is None:
            self.domain = (0.0, 1.0)
        else:
            domain = tuple(domain)
            if len(domain) < 2:
                raise(ValueError("Incorrect domain type"))
            self.domain = domain

        # Cache objectives and constraints so that they do not have to be 
        # recreated every time
        self.objectives = self.get_objectives()
        self.constraints = self.get_constraints()

    def get_random_vector(self):
        """
        Create a vector of the dimension length with random values.

        The resulting vector has random values between the domains of each
        variable, and random 0 or 1 values for binary variables.
        """

        # Alter domain from [0.0, 1.0) to [d[0], d[1])
        # Note that self.domain can also be a tuple of numpy arrays, which then 
        # work componentwise.
        low = self.domain[0]
        high = self.domain[1]
        v = (np.random.rand(self.dim) * (high - low)) + low
        # If there is a d[2], then this tells us which element is a binary type 
        # and which ones are reals.
        if len(self.domain) > 2:
            indices = np.nonzero(self.domain[2])
            v[indices] = np.random.random_integers(0, 1, size=len(indices[0]))

        return v

    def evaluate(self, points):
        """
        Evaluate a list of vectors containing variable values.

        This checks for each of these vectors whether they are feasible
        according to all of the problem constraints, and calculates the
        objective function values for them. These two evaluations are returned,
        each as a list of evaluations for every vector.
        """

        Feasible = [True for _ in points]
        Objectives = [[] for _ in points]
        for idx, x in enumerate(points):
            Feasible[idx], Objectives[idx] = self.evaluate_point(x)

        return Feasible, Objectives

    def evaluate_point(self, point):
        """
        Evaluate a single individual. a vector containing variable values.

        This checks whether this vector is feasible according to all of the
        problem constraints, and calculates the objective function values for
        the vector. These two evaluations are returned, where the feasibility
        is a boolean and the objectives are a list of function values.
        """
        Feasible = all(constraint(point) for constraint in self.constraints)
        Objective = [objective(point) for objective in self.objectives]

        return Feasible, Objective

    def mutate(self, point, steps):
        """
        Mutate a given vector of variable values with dimension length using
        a vector of step sizes as parameters for the mutation operators.

        For real variables, the mutation operator changes each point using
        random values from a normal distribution, with each step determining
        the variance sigma of this distribution for one variable. Higher step
        sizes therefore increase the mutation speed, and lower steps decrease.

        For binary variables, the mutation operator flips each value
        independently, but only if a uniform random value is higher than the
        step size threshold. Higher step sizes decrease the probability of
        flipping, while lower step sizes increase flip mutation frequency.
        """

        x_new = point + steps * np.random.randn(self.dim)
        if len(self.domain) > 2:
            # Bitwise flip based on independent chances.
            # We check whether a value is above the probability of flipping.
            # If so, then the calculation becomes |1 - old| which flips the bit
            # Otherwise, the calculation is |0 - old| which keeps the old value
            indices = np.nonzero(self.domain[2])
            x_new[indices] = np.absolute(
                (np.random.rand(len(indices[0])) > np.array(steps)[indices[0]])
                - point[indices]
            )

        return x_new

    def get_objectives(self):
        """
        Get a list of objective functions.

        The functions in the list are lambdas that accept a vector of values,
        and returns a floating point objective value for the entire individual.
        Since we model minimization problems, this value should become smaller
        when an individual is better than another one.
        One can use member variables and numpy tiling tricks to calculate the
        objective function values in one go.
        """

        return []

    def get_constraints(self):
        """
        Get a list of constraint functions.

        The functions in the list are lambdas that accept a vector of values,
        and returns a boolean feasibility value for the entire individual.
        An unfit individual should be given a `False` value by at least one of
        the constraints that it violates. Subclasses should extend the list
        provided by the `Problem` class, which generates constraints for the
        domains of the variables.
        """

        constraints = [
            lambda x: np.all(x >= self.domain[0])
        ]
        if len(self.domain) > 2:
            # Using + and * as logical OR/AND operators to allow binary values.
            # We check whether either the normal bound is satisfied, or that 
            # the value is binary and is at most 1.
            constraints.extend([
                lambda x: np.all(
                    (x < self.domain[1]) +
                    (self.domain[2] * (x <= self.domain[2]))
                )
            ])
        else:
            constraints.extend([
                lambda x: np.all(x < self.domain[1])
            ])

        return constraints

class Reconstruction_Plan(Problem):
    def __init__(self, arguments):
        """
        Initialize the reconstruction planning problem.

        The number of measurements that we intend to make is a fixed parameter
        and cannot be optimized by the current algorithm in one run.

        The network size is defined in the same way as in the weight matrix
        of the reconstruction problem itself.
        """

        if not isinstance(arguments, Arguments):
            raise ValueError("'arguments' must be an instance of Arguments")

        self.settings = arguments.get_settings("planning_problem")
        N = self.settings.get("number_of_measurements")
        network_size = self.settings.get("network_size")

        # Variables:
        # - distances from the origin of each measurement line y_1 .. y_n
        #   domain: from -network_y**2 to network_y**2 (in meters)
        # - angles of each measurement line compared to the x axis a_1 .. a_n
        #   domain: from 0.0 to math.pi (in radians)
        #   This corresponds to slopes.
        domain = (
            # Minimum values per variable
            np.array([[-network_size[1]**2]*N, [0.0]*N]).flatten(),
            # Maximum values per variable
            np.array([[network_size[1]**2]*N, [math.pi]*N]).flatten()
        )
        super(Reconstruction_Plan, self).__init__(N*2, domain)

        # Initial weight matrix object which is filled with current locations 
        # during evaluations.
        self.weight_matrix = Weight_Matrix(arguments, network_size, [])
        self.matrix = None
        self.snapper = Snap_To_Boundary([0, 0], *network_size)
        self.unsnappable = False

        self.N = N
        self.network_size = network_size

    def generate_positions(self, offset, angle):
        if angle == math.pi/2:
            return [[offset, 0], [offset, self.network_size[1]]]
        if angle < math.pi/2:
            beta = math.pi/2 - angle
        else:
            beta = angle - math.pi/2

        a = math.tan(angle)
        b = offset / math.sin(beta)
        return [[0, b], [self.network_size[0], a*self.network_size[0]+b]]

    def evaluate_point(self, point):
        self.unsnappable = False

        # Generate positions, check snappability and create weight matrix
        positions = []
        for i in range(self.N):
            sensor_points = self.generate_positions(point[i], point[i+self.N])
            snapped_points = self.snapper.execute(*sensor_points)
            if snapped_points is None:
                print("Unsnappable: {}, {}".format(*sensor_points))
                self.unsnappable = True
            else:
                positions.extend([[p.x, p.y] for p in snapped_points])

        self.weight_matrix.set_positions(positions)
        self.matrix = self.weight_matrix.create(full=False)
        if all(self.matrix.any(axis=0)):
            print(self.matrix)

        return super(Reconstruction_Plan, self).evaluate_point(point)

    def get_objectives(self):
        return [
            # Matrix should have values filled as much as possible, so that 
            # lines contribute a lot to the solution
            lambda x: -self.matrix.sum(),
            lambda x: -self.matrix.any(axis=0).sum(),
            # Matrix should have values that are similar to each other in the 
            # columns, so that pixels are evenly measured by links
            #lambda x: np.var(self.matrix, axis=0).mean()
        ]

    def get_constraints(self):
        constraints = super(Reconstruction_Plan, self).get_constraints()
        constraints.extend([
            # Variables should not be in such a way that a pair of positions do 
            # not intersect with the network
            lambda x: not self.unsnappable#,
            # Matrix must not have columns that have only zeroes, since then 
            # a pixel in the image is not intersected by any line
            #lambda x: np.all(self.matrix.any(axis=0))
        ])
        return constraints
