import itertools
import math
import numpy as np

from ..geometry.Geometry import Geometry
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
        whether the variables are binary, integer or real. This can be a numpy
        array containing types, respectively `bool`, `np.int` and `np.float`.
        """

        self.dim = dim
        if domain is None:
            self.domain = (0.0, 1.0)
            self._bool_indices = ()
            self._int_indices = ()
        else:
            domain = tuple(domain)
            if len(domain) < 2:
                raise(ValueError("Incorrect domain type"))
            self.domain = domain
            self._bool_indices = np.nonzero(domain[2] == bool)
            self._int_indices = np.nonzero(domain[2] == np.int)

        # Cache objectives and constraints so that they do not have to be 
        # recreated every time
        self.objectives = self.get_objectives()
        self.constraints = self.get_constraints()

    def format_steps(self, steps):
        dim = self.dim
        return np.array((steps * ((dim / len(steps)) + 1))[:dim]).flatten()

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
        # If there is a d[2], then this tells us which elements are a binary 
        # type, which ones are integer and which ones are reals.
        if len(self.domain) > 2:
            # Draw random binary values.
            v[self._bool_indices] = np.random.random_integers(0, 1, size=len(self._bool_indices[0]))

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

        point = self.format_point(point)
        Feasible = all(constraint(point) for constraint in self.constraints)
        if Feasible:
            Objective = [float(objective(point)) for objective in self.objectives]
        else:
            Objective = [np.inf for objective in self.objectives]

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
            indices = self._bool_indices[0]
            if len(indices) > 0:
                x_new[self._bool_indices] = np.absolute(
                    (np.random.rand(len(indices)) > np.array(steps)[indices])
                    - point[self._bool_indices]
                )

            low = self.domain[0]
            high = self.domain[1]
            x_new[self._int_indices] = np.remainder(x_new[self._int_indices] - low, high - low - 0.5) + low

        return x_new

    def format_point(self, point):
        if self._int_indices:
            # Round integer variables.
            point = np.copy(point)
            point[self._int_indices] = np.round(point[self._int_indices])

        return point

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
                    ((self.domain[2] == bool) * (x <= self.domain[2]))
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
        self.N = self.settings.get("number_of_measurements")
        self.network_size = self.settings.get("network_size")
        self.padding = self.settings.get("network_padding")

        num_variables, domain = self.get_domain()
        super(Reconstruction_Plan, self).__init__(num_variables, domain)

        # Initial weight matrix object which is filled with current locations 
        # during evaluations.
        size = [self.network_size[0]-self.padding[0]*2, self.network_size[1]-self.padding[1]*2]
        self.weight_matrix = Weight_Matrix(arguments, self.padding, size)
        self.matrix = None
        self.unsnappable = 0
        self.distances = None

        self.unsnappable_max = self.N * self.settings.get("unsnappable_rate")

        self.geometry = Geometry()

    def get_domain(self):
        raise NotImplementedError("Subclass must implement `get_domain`")

    def format_steps(self, steps):
        if len(steps) == self.dim/self.N:
            return np.array(list(itertools.chain(*[[s] * self.N for s in steps]))).flatten()

        return super(Reconstruction_Plan, self).format_steps(steps)

    def generate_positions(self, point, index):
        raise NotImplementedError("Subclass must implement `generate_positions(point, index)`")

    def get_positions(self, point):
        unsnappable = 0

        # Generate positions, check snappability and create weight matrix
        positions = []

        point = self.format_point(point)
        for i in range(self.N):
            sensor_points = self.generate_positions(point, i)
            snapped_points = self.select_positions(sensor_points)
            if snapped_points is None:
                unsnappable += 1
            else:
                positions.append(snapped_points)

        return np.array(positions), unsnappable

    def select_positions(self, sensor_points):
        snapped_points = self.weight_matrix.update(*sensor_points)
        return snapped_points

    def evaluate_point(self, point):
        self.weight_matrix.reset()
        positions, self.unsnappable = self.get_positions(point)

        if positions.size > 0:
            self.distances = np.linalg.norm(positions[:,0,:]-positions[:,1,:], axis=1)
        else:
            self.distances = np.array([])

        self.matrix = self.weight_matrix.output()

        return super(Reconstruction_Plan, self).evaluate_point(point)

    def get_objectives(self):
        return [
            # Matrix should have many columns (pixels) that have multiple links 
            # (measurements) intersecting that pixel.
            lambda x: -np.sum(np.sum(self.matrix > 0, axis=0)),
            # The distances of the links should be minimized, since a longer 
            # link is weaker and thus contributes less clearly to a solution of 
            # the reconstruction.
            lambda x: self.distances.sum()
            # Matrix should have values that are similar to each other in the 
            # columns, so that pixels are evenly measured by links
            #lambda x: np.var(self.matrix, axis=0).mean()
        ]

    def get_constraints(self):
        constraints = super(Reconstruction_Plan, self).get_constraints()
        constraints.extend([
            # Matrix must not have too many columns that have only zeroes, 
            # since then a pixel in the image is not intersected by any line. 
            # This is mostly a baseline to push the evolutionary algorithm in 
            # the right direction, since we also have an objective to make them 
            # intersect more often.
            lambda x: self.weight_matrix.check(),
            # Variables should not be in such a way that a pair of positions do 
            # not intersect with the network. At least it should not happen too 
            # often, otherwise the mission is useless. It can be useful to 
            # allow a number of them, since then we can have missions that 
            # solve the problem with fewer measurements than the fixed 
            # parameter.
            lambda x: self.unsnappable < self.unsnappable_max
        ])
        return constraints

class Reconstruction_Plan_Continuous(Reconstruction_Plan):
    def get_domain(self):
        # Variables:
        # - distances from the origin of each measurement line y_1 .. y_n
        #   domain: from -net_d to net_d (in meters)
        # - angles of each measurement line compared to x axis a_1 .. a_n
        #   domain: from 0.0 to math.pi (in radians)
        #   This corresponds to slopes.
        num_variables = self.N*3
        net_d = math.sqrt((self.network_size[0])**2 + (self.network_size[1])**2)
        domain = (
            # Minimum values per variable
            np.array([[-self.network_size[1]]*self.N, [0.0]*self.N, [0]*self.N]).flatten(),
            # Maximum values per variable
            np.array([[net_d]*self.N, [math.pi]*self.N, [1]*self.N]).flatten(),
            # Whether variables are boolean or real
            np.array([[np.float]*self.N, [np.float]*self.N, [bool]*self.N]).flatten()
        )

        return num_variables, domain

    def format_steps(self, steps):
        if len(steps) == 2:
            pairs = [steps[0]] * self.N + [steps[1]] * self.N
            return np.array([pairs + [0.5]*self.N]).flatten()

        return super(Reconstruction_Plan_Continuous, self).format_steps(steps)

    def generate_positions(self, point, index):
        offset = point[index]
        angle = point[index+self.N]
        cardinal = point[index+2*self.N]

        if angle == math.pi/2 or (cardinal and self.geometry.check_angle(angle, math.pi/2, math.pi/8)):
            return [[offset, 0], [offset, self.network_size[1]]]
        if angle < math.pi/2:
            beta = math.pi/2 - angle
        else:
            beta = angle - math.pi/2

        if cardinal and self.geometry.check_angle(angle, 0.0, math.pi/8):
            a = 0.0
        else:
            a = math.tan(angle)
        b = offset / math.sin(beta)
        return [[0, b], [self.network_size[0], a*self.network_size[0]+b]]

class Reconstruction_Plan_Discrete(Reconstruction_Plan):
    def get_domain(self):
        num_variables = self.N*4
        # Variables:
        # x and y coordinates for two measurement points, natural numbers.
        # Valid coordinates are within the grid size bounds and also not inside 
        # the network itself.
        max_y = [self.network_size[0]]*self.N
        max_x = [self.network_size[1]]*self.N
        domain = (
            # Minimum values per variable
            np.array([[0]*num_variables]).flatten(),
            # Maximum values per variable
            np.array([max_y, max_x, max_y, max_x]).flatten(),
            # Whether variables are boolean or real
            np.array([[np.int]*num_variables]).flatten()
        )

        return num_variables, domain

    def format_steps(self, steps):
        if len(steps) == 2:
            pairs = [steps[0]] * self.N + [steps[1]] * self.N
            return np.array([pairs + pairs]).flatten()

        return super(Reconstruction_Plan_Discrete, self).format_steps(steps)

    def generate_positions(self, point, index):
        return [
            [int(point[index]), int(point[index+self.N])],
            [int(point[index+2*self.N]), int(point[index+3*self.N])]
        ]

    def select_positions(self, sensor_points):
        snapped_points = super(Reconstruction_Plan_Discrete, self).select_positions(sensor_points)
        if snapped_points is None:
            return None

        # Keep the unsnapped points since we may be able to perform 
        # measurements on different grid positions.
        return sensor_points
