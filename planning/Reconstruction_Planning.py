# Evolutionary Multiobjective Optimization algorithms and problem sets

import numpy as np
from collections import OrderedDict
import itertools

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
            for constraint in self.constraints:
                Feasible[idx] = Feasible[idx] and constraint(x)

            Objectives[idx] = [objective(x) for objective in self.objectives]

        return Feasible, Objectives

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

class Algorithm(object):
    def __init__(self, problem, mu, t_max, steps):
        self.problem = problem
        self.mu = mu
        self.t_max = t_max
        # Make steps as long as necessary, and convert to numpy array for easy 
        # per-component application.
        dim = self.problem.dim
        self.steps = np.array((steps * ((dim / len(steps)) + 1))[:dim])

    def evolve(self):
        """
        Perform the evolutionary algorithm and find solutions.
        """

        print("Settings: Problem {}, Algo {}, mu={}, t_max={}".format(self.problem.__class__.__name__, self.__class__.__name__, mu, t_max))
        print("Steps: {}".format(steps))

        # For our initial population of size mu, generate random vectors with 
        # values in a feasible interval using domain specification.
        P = [self.problem.get_random_vector() for _ in range(self.mu)]
        #print("Initial population: {}".format(P))

        # Evaluate objectives and constraints for points in the population.
        Feasible, Objectives = self.problem.evaluate(P)

        # For t = 1, 2, ..., t_max
        for t in xrange(1, self.t_max+1):
            if t % 10000 == 0:
                print("Iteration {}".format(t))

            # Select random index s of the mu points
            s = np.random.randint(self.mu)
            # Create a mutated point x_new from x(s) by altering each component 
            # with a normal distributed random number generator. This is done 
            # on each component using numpy broadcasting.
            x_new = self.problem.mutate(P[s], self.steps)
            #print("Mutated {} into {}".format(P[s], x_new))

            # Evaluate objectives and constraints for x_new
            NewFeasible, NewObjectives = self.problem.evaluate([x_new])
            P.append(x_new)
            Feasible.append(NewFeasible[0])
            Objectives.append(NewObjectives[0])
            #print(Feasible)
            #print(Objectives)

            # Track which points are dominated or infeasible. We track the 
            # indices from the points list.
            Delete = np.nonzero(np.array(Feasible) == False)[0]

            # First delete the infeasible solutions, then we will care about 
            # the nondominated solutions. This differs from the original 
            # implementation, hopefully this is a good decision.
            if len(Delete) == 0:
                R = self.sort_nondominated(Objectives)
                Delete = list(itertools.chain(*[Rk.keys() for Rk in R[1:]]))

            if len(Delete) > 0:
                # Randomly delete one of the solutions. If it is the new point, 
                # then we do not need to do anything (we just forget it in next 
                # iteration), otherwise we replace the deleted point with the 
                # new point.
                # We use numpy.random.randint to select key instead of 
                # numpy.random.choice because of compatibility with older 
                # Numpy.
                idx = Delete[np.random.randint(len(Delete))]
            else:
                # Delete the individual with the smallest crowding distance 
                # (NSGA) or hypervolume contribution (SMS-EMOA)
                C = self.sort_contribution(R[0])

                idx = np.argmin(C)

            del P[idx]
            del Feasible[idx]
            del Objectives[idx]

        return P, Objectives, Feasible

    def KLP(self, P, Objectives):
        """
        Perform the Kung, Luccio, and Preparata algorithm to determine
        nondominated solutions. The given list P must contain objective values 
        for exactly two objective functions. It must be sorted in the first 
        objective value already.

        We return a dictionary of objective values that should be kept,
        indexed by the original individual indices, and a list of indices that
        should be removed from P for another run because they are nondominated.
        """

        # For now just 2D-KLP, we don't need anything else in our cases.
        T = OrderedDict()
        # Since we perform minimization, we want to find lower values instead 
        # of higher values like in the original 2D-KLP algorithm. Thus yStar 
        # starts out as infinity and decreases within the algorithm.
        yStar = np.inf
        todelete = []
        for idx, i in enumerate(P):
            if Objectives[i][1] < yStar:
                T[i] = Objectives[i]
                yStar = Objectives[i][1]
                todelete.append(idx)

        return T, todelete

    def sort_nondominated(self, Objectives):
        """
        Sort a list of objective values for individuals into groups of
        nondominated and dominated solutions.

        The resulting list contains dictionaries with the original indices of
        the given list and their objective values. The first dictionary in this
        list are nondominated individuals, the rest are dominated.
        """

        # Sort P by first coordinate in ascending order, since we do 
        # minimization. P only contains the keys the the objective values of 
        # the points.
        P = sorted(range(len(Objectives)), key=lambda i: Objectives[i][0], reverse=False)
        R = []
        # TODO: Speed up sorting by just putting all the other solutions in the 
        # next group after one go? They are all nondominated anyway and 
        # probably do not use them for anything else.
        while len(P) > 0:
            Rk, todelete = KLP(P, Objectives)
            R.append(Rk)
            # Need to delete in reverse order so that the subsequent indexes 
            # are still correct.
            for idx in reversed(todelete):
                del P[idx]

        return R

    def sort_contribution(self, Rk):
        return Rk

class NSGA(Algorithm):
    def crowding_distance(self,Rk):
        """
        Calculate the crowding distances of individuals for the NSGA-II
        algorithm. The individuals are nondominated and have their objective
        values. This function can work with any number of objective functions.

        The resulting list contains values that indicate how useful each
        individual is to have in a potential Pareto front; points that are less
        close to others are more useful to keep.
        """

        C = [0 for _ in Rk.items()]
        i = 0
        for idx in Rk.keys():
            for j in xrange(len(Rk[idx])):
                # Sort the keys of the points according to the objective j
                keys = sorted(Rk.keys(), key=lambda i: Rk[i][j])
                # Location of the index idx in the sorted keys
                v = keys.index(idx)
                l = Rk[keys[v-1]][j] if v > 0 else -np.inf
                u = Rk[keys[v+1]][j] if v < len(Rk)-1 else np.inf
                C[i] += 2 * (u - l)

            i += 1

        return C

    def sort_contribution(self, Rk):
        return self.crowding_distance(Rk)

class SMS_EMOA(Algorithm):
    def hypervolume_contribution(self, Rk):
        """
        Calculate the 2D hypervolume contribution of individuals for the
        SMS-EMOA algorithm. The individuals are nondominated and have their
        objective values.

        The resulting list contains values that indicate how useful each
        individual is to have in a potential Pareto front; points that have
        a larger hypervolume around themselves are more useful to keep.
        """

        # 2D only.
        # Sort by first coordinate
        X = sorted(Rk.keys(), key=lambda i: Rk[i][0])
        C = [0 for _ in X]
        for i, idx in enumerate(X):
            l = Rk[X[i-1]][1] if i > 0 else -np.inf
            u = Rk[X[i+1]][0] if i < len(Rk)-1 else np.inf
            C[i] = (Rk[idx][1] - l) * (u - Rk[idx][0])

        return C

    def sort_contribution(self, Rk):
        return self.hypervolume_contribution(Rk)
