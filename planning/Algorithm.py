# Core imports
import itertools
import time
from collections import OrderedDict
from functools import partial

# Library imports
import numpy as np

# Package imports
from ..settings import Arguments

__all__ = ["NSGA", "SMS_EMOA"]

class Algorithm(object):
    """
    Evolutionary Multiobjective Optimization algorithm
    """

    def __init__(self, problem, arguments):
        if not isinstance(arguments, Arguments):
            raise ValueError("'arguments' must be an instance of Arguments")

        self.problem = problem
        self.settings = arguments.get_settings("planning_algorithm")
        self.mu = self.settings.get("population_size")
        self.t_current = 0
        self.t_max = self.settings.get("iteration_limit")
        self.t_callback = self.settings.get("iteration_callback")
        self.iteration_callback = None

        # Make steps as long as necessary, and convert to numpy array for easy 
        # per-component application.
        self.steps = self.problem.format_steps(self.settings.get("step_size"))

    def set_iteration_callback(self, callback):
        if not hasattr(callback, "__call__"):
            raise TypeError("Iteration callback is not callable")

        self.iteration_callback = callback

    def evolve(self):
        """
        Perform the evolutionary algorithm and find solutions.
        """

        # For our initial population of size mu, generate random vectors with 
        # values in a feasible interval using domain specification.
        P = [self.problem.get_random_vector() for _ in range(self.mu)]

        # Evaluate objectives and constraints for points in the population.
        Feasible, Objectives = self.problem.evaluate(P)
        Deletions = {
            "infeasible": 0,
            "dominated": 0,
            "contribution": 0
        }

        start_time = time.time()

        # For t_current = 1, 2, ..., t_max (updated at the end of the loop).
        # We use an infinite iterable and stop when the maximum iteration is 
        # reached so that the maximum iteration can be altered while running.
        # We handle the callback for the maximum iteration itself as well.
        t_iter = itertools.count(self.t_current)

        while self.t_current <= self.t_max:
            self.t_current = t_iter.next()

            if self.t_current % self.t_callback == 0 and self.iteration_callback is not None:
                cur_time = time.time() - start_time
                self.iteration_callback(self, {
                    "iteration": self.t_current,
                    "cur_time": cur_time,
                    "population": P,
                    "feasible": Feasible,
                    "objectives": Objectives,
                    "deletions": Deletions
                })

            if self.t_current >= self.t_max:
                break

            self._mutate_and_select(P, Feasible, Objectives, Deletions)

        return P, Objectives, Feasible

    def _mutate_and_select(self, P, Feasible, Objectives, Deletions):
        # Select random index s of the mu points
        s = np.random.randint(self.mu)
        # Create a mutated point x_new from x(s) by altering each component 
        # with a normal distributed random number generator. This is done on 
        # each component using numpy broadcasting.
        x_new = self.problem.mutate(P[s], self.steps)

        # Evaluate objectives and constraints for x_new
        NewFeasible, NewObjectives = self.problem.evaluate([x_new])
        P.append(x_new)
        Feasible.append(NewFeasible[0])
        Objectives.append(NewObjectives[0])

        # Track which points are dominated or infeasible. We track the indices 
        # from the points list.
        Delete = np.nonzero(np.logical_not(np.array(Feasible)))[0]

        # First delete the infeasible solutions, then we will care about the 
        # nondominated solutions. This differs from the original 
        # implementation, hopefully this is a good decision.
        if len(Delete) > 0:
            Deletions["infeasible"] += 1
        else:
            R = self.sort_nondominated(Objectives, all_layers=False)
            Delete = list(itertools.chain(*[Rk.keys() for Rk in R[1:]]))
            if len(Delete) > 0:
                Deletions["dominated"] += 1

        if len(Delete) > 0:
            # Randomly delete one of the solutions. If it is the new point, 
            # then we do not need to do anything (we just forget it in next 
            # iteration), otherwise we replace the deleted point with the new 
            # point.
            # We use numpy.random.randint to select key instead of 
            # numpy.random.choice because of compatibility with older Numpy.
            idx = Delete[np.random.randint(len(Delete))]
        else:
            # Delete the individual with the smallest crowding distance (NSGA) 
            # or hypervolume contribution (SMS-EMOA)
            C = self.sort_contribution(R[0])

            idx = np.argmin(C)
            Deletions["contribution"] += 1

        del P[idx]
        del Feasible[idx]
        del Objectives[idx]

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
        if all(Objectives[i][1] == yStar for i in P):
            return OrderedDict([(i, Objectives[i]) for i in P]), range(len(P))

        todelete = []
        for idx, i in enumerate(P):
            if Objectives[i][1] < yStar:
                T[i] = Objectives[i]
                yStar = Objectives[i][1]
                todelete.append(idx)

        return T, todelete

    def sort_nondominated(self, Objectives, all_layers=True):
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
        first_layer = True
        # Speed up sorting by just putting all the other solutions in the next 
        # group after one go. They are all nondominated anyway and probably do 
        # not use them for anything else.
        while len(P) > 0 and (all_layers or first_layer):
            Rk, todelete = self.KLP(P, Objectives)
            R.append(Rk)
            first_layer = False
            # Need to delete in reverse order so that the subsequent indexes 
            # are still correct.
            for idx in reversed(todelete):
                del P[idx]

        # If we only care about the first layer, then place all other 
        # individuals in the second layer.
        if not all_layers and len(P) > 0:
            R.append(OrderedDict([(i, Objectives[i]) for i in P]))

        return R

    def sort_contribution(self, Rk):
        return Rk

    def get_name(self):
        """
        Get the displayable name of the algorithm.
        """

        raise NotImplementedError("Subclasses must implement `get_name`")

class NSGA(Algorithm):
    def crowding_distance(self, Rk):
        """
        Calculate the crowding distances of individuals for the NSGA-II
        algorithm. The individuals are nondominated and have their objective
        values. This function can work with any number of objective functions.

        The resulting list contains values that indicate how useful each
        individual is to have in a potential Pareto front; points that are less
        close to others are more useful to keep.
        """

        C = np.zeros(len(Rk))
        i = 0

        if len(Rk) == 0:
            return C

        keys = []
        for obj in xrange(len(Rk.values()[0])):
            # Sort the keys of the points according to the objective j (obj)
            keys.append(sorted(Rk.keys(), key=partial(lambda j, i: Rk[i][j], obj)))

        for idx in Rk.keys():
            for j in xrange(len(Rk[idx])):
                # Location of the index idx in the sorted keys
                k = keys[j]
                v = k.index(idx)
                l = Rk[k[v-1]][j] if v > 0 else np.NINF
                u = Rk[k[v+1]][j] if v < len(Rk)-1 else np.inf
                C[i] += 2 * (u - l)

            i += 1

        return C

    def sort_contribution(self, Rk):
        return self.crowding_distance(Rk)

    def get_name(self):
        return "NSGA-II"

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
        C = np.zeros(len(X))
        for i, idx in enumerate(X):
            l = Rk[X[i-1]][1] if i > 0 else np.NINF
            u = Rk[X[i+1]][0] if i < len(Rk)-1 else np.inf
            C[i] = (Rk[idx][1] - l) * (u - Rk[idx][0])

        return C

    def sort_contribution(self, Rk):
        return self.hypervolume_contribution(Rk)

    def get_name(self):
        return "SMS-EMOA"
