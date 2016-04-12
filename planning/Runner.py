import itertools
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import thread

import Algorithm
from Problem import Reconstruction_Plan_Continuous, Reconstruction_Plan_Discrete
from ..core.Threadable import Threadable

class Planning_Runner(Threadable):
    """
    A supervisor class that handles running the evolutionary algorithm on the
    reconstruction planning problem and creates results and plots from the
    output of the algorithm.
    """

    def __init__(self, arguments, thread_manager, iteration_callback=None):
        super(Planning_Runner, self).__init__("planning_runner", thread_manager)

        self.settings = arguments.get_settings("planning")
        algo = self.settings.get("algorithm_class")

        if self.settings.get("discrete"):
            self.problem = Reconstruction_Plan_Discrete(arguments)
        else:
            self.problem = Reconstruction_Plan_Continuous(arguments)

        if algo not in Algorithm.__dict__:
            raise ValueError("Algorithm class '{}' does not exist".format(algo))

        self.algorithm = Algorithm.__dict__[algo](self.problem, arguments)

        if iteration_callback is not None:
            self.algorithm.set_iteration_callback(iteration_callback)

        self.done = False

    def activate(self):
        """
        Run the algorithm in its own thread.
        """

        super(Planning_Runner, self).activate()

        thread.start_new_thread(self.start, ())

    def deactivate(self):
        """
        Stop the algorithm if it is currently running.

        This makes the iteration limit invalid, so any later runs must either
        reinstantiate the entire runner or set the iteration limit again.
        """

        super(Planning_Runner, self).deactivate()

        self.set_iteration_limit(0)

    def start(self):
        """
        Run the algorithm.

        Returns a list of feasible indices, sorted on the first objective.
        """

        self.done = False
        try:
            self.P, self.Objectives, self.Feasible = self.algorithm.evolve()
            self.R = self.algorithm.sort_nondominated(self.Objectives)
        except:
            super(Planning_Runner, self).interrupt()
            return []

        self.done = True

        return self.get_indices()

    def get_indices(self):
        """
        Get the indices of the population list that are feasible.
        The resulting list is sorted according to the first objective value.

        If the algorithm is not yet done, an empty list is returned.
        """

        if not self.done:
            return []

        indices = [i for i in range(self.get_population_size()) if self.Feasible[i]]
        indices = sorted(indices, key=lambda i: self.Objectives[i][0])

        return indices

    def get_objectives(self, i):
        """
        Get the objective values for an individual with index `i` from a run of
        the algorithm.

        If the algorithm is not yet done, `None` is returned.
        """

        if not self.done:
            return None

        return self.Objectives[i]

    def get_positions_plot(self, i, plot_number, count, layer=None):
        """
        Given an index `i` of an individual from a run of the algorithm, create
        a matplotlib plot for the display of the positions of the vehicles and
        and measurement lines, and return the positions and unsnappable count.

        The `plot_number` is a number to be shown in the plot to give it another
        unique identifier for the layer the individual is in, and `count` is the
        number of individuals of that layer.

        If the algorithm is not yet done or if the individual is not feasible,
        or if a `layer` is given and the individual is not in that layer, then
        this method returns an empty numpy array and zero instead.
        """

        if not self.done or not self.Feasible[i]:
            return np.empty(0), 0
        if layer is not None and i not in self.R[layer]:
            return np.empty(0), 0

        positions, unsnappable = self.problem.get_positions(self.P[i])
        plt.clf()
        plt.title("Planned sensor positions for solution #{}/{} (index {}, f1 = {})".format(plot_number, count, i, self.Objectives[i][0]))

        # Create axes with limits that keep the network visible, make the plot 
        # square and display ticks and a grid at the network coordinates.
        plt.xlabel("x coordinate")
        plt.ylabel("y coordinate")
        plt.xlim([-0.1, self.problem.network_size[0]+0.1])
        plt.ylim([-0.1, self.problem.network_size[1]+0.1])
        plt.gca().set_aspect('equal', adjustable='box')
        plt.xticks(range(self.problem.network_size[0]+1))
        plt.yticks(range(self.problem.network_size[1]+1))
        plt.grid()

        # Make network size with padding visible
        plt.gca().add_patch(Rectangle(
            (self.problem.padding[0], self.problem.padding[1]),
            self.problem.network_size[0] - self.problem.padding[0] * 2,
            self.problem.network_size[1] - self.problem.padding[1] * 2,
            alpha=0.2, edgecolor="grey"
        ))

        # Plot the measurement lines between locations as well as the vehicle 
        # sensor locations themselves as circles.
        lines = [[(p[0,0], p[1,0]), (p[0,1], p[1,1])] for p in positions]

        plt.plot(*itertools.chain(*lines))
        plt.plot(positions[:,:,0].flatten(), positions[:,:,1].flatten(), 'ro')

        return positions, unsnappable

    def make_pareto_plot(self, axes=None):
        """
        Create a plot of the Pareto front of all the feasible solutions in 
        the sorted nondominated layers.

        If `axes` is given, then the plot is drawn on those matplotlib axes
        instead of the current plot figure.

        Does nothing if the algorithm is not yet finished.
        """

        if not self.done:
            print("not done")
            return

        if axes is None:
            axes = plt.gca()

        axes.cla()

        axes.set_title("Pareto front with {}, t={}".format(self.algorithm.get_name(), self.get_iteration_limit()))
        axes.set_xlabel("Objective 1")
        axes.set_ylabel("Objective 2")
        for Rk in self.R:
            o1 = [self.Objectives[i][0] for i in Rk if self.Feasible[i]]
            o2 = [self.Objectives[i][1] for i in Rk if self.Feasible[i]]
            axes.plot(o1, o2, marker='o')

    def get_iteration_limit(self):
        """
        Get the maximum number of iterations that the algorithm performs.
        """

        return self.algorithm.t_max

    def set_iteration_limit(self, t_max):
        """
        Change the number of iterations that the algorithm performs from the
        current value, which is by default the `iteration_limit` setting value.

        This only has an effect when the algorithm has not yet run.
        """

        self.algorithm.t_max = t_max

    def get_population_size(self):
        """
        Get the number of individuals that the algorithm keeps while evolving
        them and eventually returns after running.
        """

        return self.algorithm.mu
