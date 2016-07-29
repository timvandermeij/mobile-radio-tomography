import itertools
import math
import numpy as np

from Greedy_Assignment import Greedy_Assignment
from ..geometry.Geometry_Grid import Geometry_Grid
from ..reconstruction.Weight_Matrix import Weight_Matrix
from ..settings import Arguments

class Problem(object):
    """
    Generic problem statement structure.
    
    A problem consists of a dimension of the input variables, the domains of 
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
        """
        Convert a list of `steps` to a full list of the problem's dimension.

        The returned vector of step sizes has the same number of elements as
        the number of variables that the problem has.
        """

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
            v[self._bool_indices] = np.random.randint(2, size=len(self._bool_indices[0]))

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

    def is_feasible(self, point):
        return all(constraint(point) for constraint in self.constraints)

    def evaluate_point(self, point, feasible=None):
        """
        Evaluate a single individual `point`.
        The `point` is a vector containing variable values.

        This checks whether this vector is feasible according to all of the
        problem constraints, and calculates the objective function values for
        the vector. These two evaluations are returned, where the feasibility
        is a boolean and the objectives are a list of function values.

        If `feasible` is given, then this method assumes that the feasibility
        of the point is the values of `feasible`, and that the point already
        has its final form provided by `format_point`.
        """

        if feasible is None:
            point = self.format_point(point)
            Feasible = self.is_feasible(point)
        else:
            Feasible = feasible

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

        For integer variables, we ensure that the values remain inside the
        domains of the problem by cyclically transferring them to the other
        side of the bounds. The values themselves are not converted to integer
        here to avoid bias to certain values. Use `format_point` to convert
        an individual to its final representation.
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

            if len(self._int_indices[0]) > 0:
                self._clip(x_new, self._int_indices)

        return x_new

    def _clip(self, values, indices):
        """
        Cyclically clip a vector of `values` so that the values with the given
        `indices` remain within the domain of the problem. Values that are too
        low are transferred by the same magnitude below the upper bound,
        and vice versa.
        """

        low = self.domain[0]
        high = self.domain[1]
        clipped = np.remainder(values - low, high - low - 0.5) + low
        values[indices] = clipped[indices]

    def format_point(self, point):
        """
        Convert an individual vector `point` to its final representation.

        This converts integer variables to their rounded versions.
        """

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

    def get_objective_names(self):
        """
        Get a list of names for the objective functions.

        The names are short key-like descriptions for the objectives.
        The list must be of the same length as `get_objectives`.
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
        if len(self.domain) > 2 and len(self._bool_indices[0]) > 0:
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

        # Import the settings for the planning problem.
        self.arguments = arguments
        self.arguments.get_settings("reconstruction").set("model_class", "Ellipse_Model")
        self.settings = self.arguments.get_settings("planning_problem")
        self.N = self.settings.get("number_of_measurements")
        self.network_size = self.settings.get("network_size")
        self.padding = self.settings.get("network_padding")

        num_variables, domain = self.get_domain()
        super(Reconstruction_Plan, self).__init__(num_variables, domain)

        # The actual network sizes excluding the padding.
        self.network_width = self.network_size[0] - self.padding[0]*2
        self.network_height = self.network_size[1] - self.padding[1]*2
        self.size = [self.network_width, self.network_height]

        # Initial weight matrix object which can be filled with current 
        # locations during evaluations and reset to be reused.
        self.weight_matrix = self.get_weight_matrix()

        # Resulting output from the weight matrix.
        self.matrix = None
        self.unsnappable = 0
        self.distances = None

        # The maximum number of unsnappable points in an individual.
        self.unsnappable_max = self.N * self.settings.get("unsnappable_rate")

        # A grid-based Geometry object that the Problem instance can use to 
        # make lines and points, if necessary.
        self.geometry = Geometry_Grid()

        self.assigner = Greedy_Assignment(self.arguments, self.geometry)
        self.delta_rate = self.settings.get("delta_rate")

        self.travel_distance = 0.0
        self.sensor_distances = np.empty(0)

    def get_domain(self):
        """
        Determine the domain of each variable and the number of variables that
        the problem instance requires.
        """

        raise NotImplementedError("Subclass must implement `get_domain`")

    def get_weight_matrix(self):
        """
        Create a clean weight matrix for the problem's parameters.
        """

        return Weight_Matrix(self.arguments, self.padding, self.size,
                             snap_inside=True, number_of_links=self.N)

    def format_steps(self, steps):
        # Convert a list of step sizes that has the same number of elements as 
        # there are variables for a single measurement so that they apply to 
        # each variable of each measurement.
        if len(steps) == self.dim/self.N:
            repeated_steps = itertools.chain(*[[s] * self.N for s in steps])
            return np.array(list(repeated_steps))

        return super(Reconstruction_Plan, self).format_steps(steps)

    def generate_positions(self, point, index):
        """
        Generate a pair of positions from an individual `point` using the
        variable value at `index` and any dependent variable based on the index.

        The result is a list containing the two positions, which themselves are
        2-length lists with the position coordinates.
        """

        raise NotImplementedError("Subclass must implement `generate_positions(point, index)`")

    def get_positions(self, point, weight_matrix):
        """
        Generate pairs of positions from an individual `point`, which is a list
        of variable values.

        The positions are checked against the given `weight_matrix` for
        snappability and other constraints. The weight matrix is therefore
        updated in this method, and it is not safe to use the same weight matrix
        on multiple individuals without resetting it in between.

        The result is a numpy array of selected (potentially snapped) positions
        and the number of unsnappable positions. The numpy array has three
        dimensions, the first grouping the position pairs, the second splitting
        those pairs into one position, and finally the two coordinates of the
        positions.
        """

        unsnappable = 0

        # Generate positions, check snappability and create weight matrix
        positions = []

        point = self.format_point(point)
        for i in range(self.N):
            sensor_points = self.generate_positions(point, i)
            snapped_points = self.select_positions(sensor_points, weight_matrix)
            if snapped_points is None:
                unsnappable += 1
            else:
                positions.append(snapped_points)

        return np.array(positions), unsnappable

    def select_positions(self, sensor_points, weight_matrix):
        """
        Select the positions for the given `sensor_points` using the weight
        matrix passed into `weight_matrix`.

        This method updates the weight matrix with the given points, and
        returns the final positions for the sensors which may be changed by the
        snap to boundary algorithm of the weight matrix.
        The method returns `None` when the positions could not be snapped.
        """

        snapped_points = weight_matrix.update(*sensor_points)
        return snapped_points

    def evaluate_point(self, point, feasible=None):
        self.weight_matrix.reset()
        positions, unsnappable = self.get_positions(point, self.weight_matrix)

        # Set up variables used by the constraint and objective functions.
        if positions.size > 0:
            # Generate distances between all the pairs of sensor positions.
            pair_diffs = positions[:, 0, :] - positions[:, 1, :]
            self.sensor_distances = np.linalg.norm(pair_diffs, axis=1)
        else:
            self.sensor_distances = np.empty(0)

        self.unsnappable = unsnappable

        # Check whether the point is feasible before performing more 
        # calculations that are only used for objective functions.
        if feasible is None:
            point = self.format_point(point)
            feasible = self.is_feasible(point)

        if feasible:
            self.matrix = self.weight_matrix.output()

            # If the sensor distances to waypoint distances ratio is 1, then 
            # there is no need to calculate the waypoint distance.
            if self.delta_rate < 1.0:
                distance = self.assigner.assign(positions)[1]
                self.travel_distance = float(distance)
                if self.travel_distance == np.inf:
                    feasible = False
            else:
                self.travel_distance = 0.0

        return super(Reconstruction_Plan, self).evaluate_point(point, feasible)

    def get_objectives(self):
        return [
            # Matrix should have many columns (pixels) that have multiple links 
            # (measurements) intersecting that pixel.
            lambda x: -np.sum(np.sum(self.matrix > 0, axis=0)),
            # The distances of the links should be minimized, since a longer 
            # link is weaker and thus contributes less clearly to a solution of 
            # the reconstruction.
            lambda x: self.delta_rate * self.sensor_distances.sum() + \
                      (1 - self.delta_rate) * self.travel_distance
            # Matrix should have values that are similar to each other in the 
            # columns, so that pixels are evenly measured by links
            #lambda x: np.var(self.matrix, axis=0).mean()
        ]

    def get_objective_names(self):
        return ["intersections", "distances"]

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
        # - whether to snap an angle into a cardinal direction if it is close
        #   enough such a direction.
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
            # Use two step sizes for offset and angle variables respectively, 
            # and use a sane default for the boolean cardinal variable.
            pairs = [steps[0]] * self.N + [steps[1]] * self.N
            return np.array([pairs + [0.5]*self.N]).flatten()

        return super(Reconstruction_Plan_Continuous, self).format_steps(steps)

    def generate_positions(self, point, index):
        offset = point[index]
        angle = point[index+self.N]
        cardinal = point[index+2*self.N]

        if angle == math.pi/2 or (cardinal and self.geometry.check_angle(angle, math.pi/2, math.pi/8)):
            # Straight upward angle, which are not very nice to calculate in 
            # the goniometric functions.
            return [[offset, 0], [offset, self.network_size[1]]]
        if angle < math.pi/2:
            beta = math.pi/2 - angle
        else:
            beta = angle - math.pi/2

        # Define the function of the line as y = ax + b
        if cardinal and self.geometry.check_angle(angle, 0.0, math.pi/8):
            # Straight rightward line without a slope, so y = b
            a = 0.0
        else:
            a = math.tan(angle)
        b = offset / math.sin(beta)
        return [[0, b], [self.network_size[0], a*self.network_size[0]+b]]

class Reconstruction_Plan_Discrete(Reconstruction_Plan):
    def __init__(self, arguments):
        super(Reconstruction_Plan_Discrete, self).__init__(arguments)
        self._use_mutation_operator = self.settings.get("mutation_operator")

    def get_domain(self):
        num_variables = self.N*4
        # Variables:
        # x and y coordinates for two measurement points, natural numbers.
        # Valid coordinates are within the grid size bounds and also not inside 
        # the network itself.
        max_y = [self.network_size[0]+1]*self.N
        max_x = [self.network_size[1]+1]*self.N
        domain = (
            # Minimum values per variable
            np.array([[0]*num_variables]).flatten(),
            # Maximum values per variable
            np.array([max_x, max_y, max_x, max_y]).flatten(),
            # Whether variables are boolean or real
            np.array([[np.int]*num_variables]).flatten()
        )

        return num_variables, domain

    def format_steps(self, steps):
        if len(steps) == 2:
            # Use two step sizes for x and y variables respectively.
            pairs = [steps[0]] * self.N + [steps[1]] * self.N
            return np.array([pairs + pairs]).flatten()

        return super(Reconstruction_Plan_Discrete, self).format_steps(steps)

    def mutate(self, point, steps):
        if self._use_mutation_operator:
            # Ensure we work on a copy of the original individual, so that it 
            # is left untouched.
            point = np.copy(point)
            for i in range(self.N):
                # Randomly choose an axis. If we do so, make one of the points 
                # of a measurement snap toward the other side of the grid. This 
                # causes the points to spread out more and make it more likely 
                # that the measurement intersects with the network more.
                axis = np.random.choice([-1, 0, 1])
                if axis == -1:
                    continue

                other_axis = (axis+1) % 2
                diff = self.size[axis]
                if point[i + axis*self.N] + diff > self.network_size[axis]:
                    diff = -diff

                s = steps[i+other_axis*self.N] * np.random.randn()

                # The variable for the other axis
                other_point = point[i + other_axis*self.N]
                other_padding = self.padding[other_axis]
                other_start = other_padding + self.size[other_axis]
                other_end = self.network_size[other_axis]
                if 0 <= other_point < other_padding or other_start < other_point < other_end:
                    s = self.size[other_axis]/2 * s

                point[i + (axis+2)*self.N] = point[i + axis*self.N] + diff
                point[i + (other_axis+2)*self.N] += s

        return super(Reconstruction_Plan_Discrete, self).mutate(point, steps)

    def generate_positions(self, point, index):
        return [
            [int(point[index]), int(point[index+self.N])],
            [int(point[index+2*self.N]), int(point[index+3*self.N])]
        ]

    def select_positions(self, sensor_points, weight_matrix):
        # Check whether the points are acceptable for the weight matrix, 
        # otherwise we discard the points.
        snapped_points = super(Reconstruction_Plan_Discrete, self).select_positions(sensor_points, weight_matrix)
        if snapped_points is None:
            return None

        new_points = []
        for sensor_point, snapped_point in zip(sensor_points, snapped_points):
            # Keep valid unsnapped points since we may be able to perform 
            # measurements on different grid positions in the padding region.
            # Otherwise, ensure that the snapped point is on a grid position. 
            # This possible loses accuracy but should still give a good 
            # distribution of the points.
            if weight_matrix.is_valid_point(sensor_point):
                new_points.append(sensor_point)
            else:
                new_points.append([round(coord) for coord in snapped_point])

        return new_points
