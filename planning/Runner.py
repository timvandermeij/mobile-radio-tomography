# Core imports
import itertools
import thread

# Library imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Package imports
from Problem import Reconstruction_Plan_Continuous, Reconstruction_Plan_Discrete
from ..core.Threadable import Threadable

class Planning_Runner(Threadable):
    """
    A supervisor class that handles running the evolutionary algorithm on the
    reconstruction planning problem and creates results and plots from the
    output of the algorithm.
    """

    def __init__(self, arguments, thread_manager, import_manager,
                 iteration_callback=None):
        super(Planning_Runner, self).__init__("planning_runner", thread_manager)

        self.arguments = arguments
        self.settings = self.arguments.get_settings("planning_runner")

        self._import_manager = import_manager
        self._iteration_callback = iteration_callback

        self.reset()

    def _get_problem(self):
        if self.settings.get("discrete"):
            problem_class = Reconstruction_Plan_Discrete
        else:
            problem_class = Reconstruction_Plan_Continuous

        return problem_class(self.arguments, self._import_manager)

    def reset(self):
        """
        Reset the algorithm and problem state.
        """

        self.problem = self._get_problem()

        algo = self.settings.get("algorithm_class")
        algo_class = self._import_manager.load_class(algo, module="Algorithm",
                                                     relative_module="planning")

        self.algorithm = algo_class(self.problem, self.arguments)
        self.algorithm.set_iteration_callback(self._handle_algorithm_data)

        # Whether the algorithm is done running.
        self.done = False

        # Whether the algorithm should halt immediately once it detects the 
        # signal to deactivate.
        self._halt = False

        # Iteration from which we received the data from the iteration callback
        self.current_iteration = 0

        # Population of individuals
        self.P = np.empty(0)

        # Feasibility of individuals
        self.Feasible = np.empty(0)

        # Objective values of individuals
        self.Objectives = np.empty(0)

        # Nondominated layers of solution objectives
        self.R = []

    def _save(self, P, Objectives, Feasible):
        self.P = np.copy(P)
        self.Objectives = np.copy(Objectives)
        self.Feasible = np.copy(Feasible)
        self.R = self.algorithm.sort_nondominated(self.Objectives)

    def _handle_algorithm_data(self, algorithm, data):
        # Pass through to the actual algorithm iteration callback, and track 
        # the current variables in the runner as well.
        if self._iteration_callback is not None:
            self.current_iteration = data["iteration"]
            self._save(data["population"], data["objectives"], data["feasible"])
            self._iteration_callback(algorithm, data)

    def activate(self):
        """
        Run the algorithm in its own thread.
        """

        super(Planning_Runner, self).activate()

        self.reset()
        thread.start_new_thread(self.start, ())

    def deactivate(self):
        """
        Halt the algorithm if it is currently running.

        This throws away the results of the algorithm.

        This makes the iteration limit invalid, so any later runs must either
        reinstantiate the entire runner or set the iteration limit again.
        """

        super(Planning_Runner, self).deactivate()

        self.stop()
        self._halt = True

    def start(self):
        """
        Run the algorithm.

        Returns a list of feasible indices, sorted on the first objective.
        """

        try:
            P, Objectives, Feasible = self.algorithm.evolve()
            if self._halt:
                return []

            self.current_iteration = self.get_iteration_current()
            self._save(P, Objectives, Feasible)
        except:
            if self._halt:
                return []

            super(Planning_Runner, self).interrupt()
            return []

        self.done = True

        return self.get_indices()

    def stop(self):
        """
        Stop the algorithm if it is currently running.

        Compared to `deactivate`, this allows the run to finish at the current
        iteration normally, making it possible to use its results.

        This makes the iteration limit invalid, so any later runs must either
        reinstantiate the entire runner or set the iteration limit again.
        """

        self.set_iteration_limit(0)

    def finish(self):
        """
        Finalize the data from the run and mark it as finished.
        """

    def get_indices(self, sort=0):
        """
        Get the indices of the population list that are feasible.
        The resulting list is sorted according to the objective values with
        index given in `sort`. If the sort index is negative, then the indices
        are not sorted.

        If the algorithm does not yet have (intermediate) results, an empty list
        is returned.
        """

        if self.Feasible.size == 0:
            return []

        indices = [i for i in range(self.get_population_size()) if self.Feasible[i]]
        if sort >= 0:
            indices = sorted(indices, key=lambda i: self.Objectives[i][sort])

        return indices

    def get_objectives(self, i):
        """
        Get the objective values for an individual with index `i` from a run of
        the algorithm.

        If the algorithm does not yet have (intermediate) results, `None` is
        returned.
        """

        if self.Objectives.size == 0:
            return None

        return self.Objectives[i]

    def find_objectives(self, objectives):
        """
        Get the indices of the individuals that have the given objective values
        `objectives`.

        If the algorithm does not yet have (intermediate) results, an empty
        list is returned.
        """

        if self.Objectives.size == 0:
            return []

        return np.nonzero(np.all(self.Objectives == objectives, axis=1))[0]

    def is_feasible(self, i):
        """
        Check whether the individual with index `i` is feasible.

        If the algorithm does not yet have (intermediate) results, `False` is
        returned.
        """

        if self.Feasible.size == 0:
            return False

        return self.Feasible[i]

    def get_positions(self, i):
        """
        Given an index `i` of an individual from a run of the algorithm, return
        the positions and unsnappable count of that solution.

        If the algorithm does not yet have (intermediate) results or if the
        solution is not feasible, then this method returns an empty numpy array
        and zero instead.
        """

        if self.Feasible.size == 0:
            return np.empty(0), 0

        weight_matrix = self.problem.get_weight_matrix()

        return self.problem.get_positions(self.P[i], weight_matrix)

    def get_positions_plot(self, i, plot_number, count, layer=None, axes=None):
        """
        Given an index `i` of an individual from a run of the algorithm, create
        a matplotlib plot for the display of the positions of the vehicles and
        and measurement lines, and return the positions and unsnappable count.

        The `plot_number` is a number to be shown in the plot to give it another
        unique identifier for the layer the individual is in, and `count` is the
        number of individuals of that layer.

        If the algorithm does not yet have (intermediate) results, if the
        individual is not feasible, or if a `layer` is given and the individual
        is not in that layer, then this method returns an empty numpy array and
        zero instead.

        If `axes` is given, then the plot is drawn on those matplotlib axes
        instead of the current plot figure.
        """

        if self.Feasible.size == 0 or not self.Feasible[i]:
            return np.empty(0), 0
        if layer is not None and i not in self.R[layer]:
            return np.empty(0), 0

        positions, unsnappable = self.get_positions(i)

        if axes is None:
            axes = plt.gca()

        axes.cla()

        obj = []
        for f, name in enumerate(self.problem.get_objective_names()):
            obj.append("f{} ({}): {}".format(f+1, name, self.Objectives[i][f]))

        title_format = "Sensor positions for solution #{}/{} (index {})\n{}"
        objectives = ", ".join(obj)
        axes.set_title(title_format.format(plot_number, count, i, objectives))

        # Create axes with limits that keep the network visible, make the plot 
        # square and display ticks and a grid at the network coordinates.
        axes.set_xlabel("x coordinate")
        axes.set_ylabel("y coordinate")
        axes.set_xlim([-0.1, self.problem.network_size[0] + 0.1])
        axes.set_ylim([-0.1, self.problem.network_size[1] + 0.1])
        axes.set_aspect('equal', adjustable='box')
        axes.set_xticks(range(self.problem.network_size[0] + 1))
        axes.set_yticks(range(self.problem.network_size[1] + 1))
        axes.grid(True)

        # Make network size with padding visible
        axes.add_patch(Rectangle(
            (self.problem.padding[0], self.problem.padding[1]),
            self.problem.network_size[0] - self.problem.padding[0] * 2,
            self.problem.network_size[1] - self.problem.padding[1] * 2,
            alpha=0.2, edgecolor="grey"
        ))

        # Plot the measurement lines between locations as well as the vehicle 
        # sensor locations themselves as circles.
        lines = [[tuple(p[:, 0]), tuple(p[:, 1])] for p in positions]

        axes.plot(*itertools.chain(*lines))
        axes.plot(positions[:, :, 0].flatten(), positions[:, :, 1].flatten(), 'ro')

        return positions, unsnappable

    def make_pareto_plot(self, axes=None):
        """
        Create a plot of the Pareto front of all the feasible solutions in 
        the sorted nondominated layers.

        If `axes` is given, then the plot is drawn on those matplotlib axes
        instead of the current plot figure.

        If the algorithm does not yet have (intermediate) results, then this
        method does nothing.
        """

        if self.Feasible.size == 0:
            return

        if axes is None:
            axes = plt.gca()

        axes.cla()

        axes.set_title("Pareto front with {}, t={}".format(self.algorithm.get_name(), self.current_iteration))
        names = self.problem.get_objective_names()
        axes.set_xlabel("Objective 1 ({})".format(names[0]))
        axes.set_ylabel("Objective 2 ({})".format(names[1]))
        for Rk in self.R:
            # Plot the front line of objective values for feasible individuals.
            # Enable the picker events for uses in the control panel.
            o1 = [self.Objectives[i][0] for i in Rk if self.Feasible[i]]
            o2 = [self.Objectives[i][1] for i in Rk if self.Feasible[i]]
            axes.plot(o1, o2, marker='o', picker=5)

    def get_assignment(self, i, export=True):
        """
        Given an index `i` of an individual from a run of the algorithm, return
        the dictionary of ordered waypoint assignments to vehicles. If `export`
        is `True`, then the waypoints are lists that can be exported as JSON.
        Set `export` to `False` to receive `Waypoint` objects instead.

        If the algorithm does not yet have (intermediate) results or if the
        solution is not feasible, then this method returns an empty dictionary.
        """
        
        positions = self.get_positions(i)[0]
        if positions.size == 0:
            return {}

        assignment = self.problem.assigner.assign(positions, export=export)[0]
        return assignment

    def get_iteration_current(self):
        """
        Get the current iteration number that the algorithm is at.

        This is different from `Planning_Runner.current_iteration` which is the
        iteration number from which cached callback data is from.
        """

        return self.algorithm.t_current

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
