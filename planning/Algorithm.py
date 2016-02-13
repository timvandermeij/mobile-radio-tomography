import numpy as np
from collections import OrderedDict
import itertools

from ..settings import Arguments

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
        self.t_max = self.settings.get("iteration_limit")
        self.t_debug = self.settings.get("iteration_debug")

        # Make steps as long as necessary, and convert to numpy array for easy 
        # per-component application.
        self.steps = self.problem.format_steps(self.settings.get("step_size"))

    def evolve(self):
        """
        Perform the evolutionary algorithm and find solutions.
        """

        print("Settings: Problem {}, Algo {}, mu={}, t_max={}".format(self.problem.__class__.__name__, self.__class__.__name__, self.mu, self.t_max))
        print("Steps: {}".format(self.steps))

        # For our initial population of size mu, generate random vectors with 
        # values in a feasible interval using domain specification.
        P = [self.problem.get_random_vector() for _ in range(self.mu)]

        # Evaluate objectives and constraints for points in the population.
        Feasible, Objectives = self.problem.evaluate(P)

        # For t = 1, 2, ..., t_max
        for t in xrange(1, self.t_max+1):
            if t % self.t_debug == 0:
                print("Iteration {}".format(t))
                scores = list(sorted((i for i in range(self.mu) if Feasible[i]), key=lambda i: Objectives[i]))
                if scores:
                    idx = scores[len(scores)/2]
                    print("Current knee point objectives: {}".format(Objectives[idx]))
                print("Infeasible count: {}".format(self.mu - sum(Feasible)))

            # Select random index s of the mu points
            s = np.random.randint(self.mu)
            # Create a mutated point x_new from x(s) by altering each component 
            # with a normal distributed random number generator. This is done 
            # on each component using numpy broadcasting.
            x_new = self.problem.mutate(P[s], self.steps)

            # Evaluate objectives and constraints for x_new
            NewFeasible, NewObjectives = self.problem.evaluate([x_new])
            P.append(x_new)
            Feasible.append(NewFeasible[0])
            Objectives.append(NewObjectives[0])

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
            Rk, todelete = self.KLP(P, Objectives)
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
