# Core imports
import os
import sys
import time
import json

# matplotlib imports
import matplotlib
try:
    # Make it possible to run matplotlib in displayless (console-only) mode
    matplotlib.use('Agg' if 'DISPLAY' not in os.environ or os.environ['DISPLAY'] == '' else matplotlib.get_backend())
except ValueError as e:
    raise ImportError("Could not load matplotlib backend: {}".format(e.message))
finally:
    import matplotlib.pyplot as plt

# Package imports
from __init__ import __package__
from core.Thread_Manager import Thread_Manager
from planning.Runner import Planning_Runner
from settings import Arguments

def do_plot(name):
    """
    Finish plotting by saving or showing the plot.
    """

    backend = matplotlib.get_backend()
    if backend.lower() == 'agg' or 'SAVE_PATH' in os.environ:
        path = os.environ['SAVE_PATH'] if 'SAVE_PATH' in os.environ else '.'
        filename = "{}/{}".format(path, name)
        plt.savefig(filename)
        print("Saved plot as {}".format(filename))
    else:
        print("Close the plot window to continue.")
        try:
            plt.show()
        except StandardError:
            # Somethimes things go wrong in the plot display (such as when 
            # clicking close button too fast), so ignore those errors.
            pass

def do_data(name, data):
    """
    Handle data output.
    Either write a JSON file with the given `name` for the `data` object, or
    print the data to the standard output.
    """

    if matplotlib.get_backend() == 'Agg' or 'SAVE_PATH' in os.environ:
        path = os.environ['SAVE_PATH'] if 'SAVE_PATH' in os.environ else '.'
        filename = "{}/{}.json".format(path, name)
        with open(filename, 'wb') as f:
            json.dump(data, f)
    else:
        print(data)

def iteration_callback(algorithm, data):
    t = data["iteration"]
    cur_time = data["cur_time"]
    speed = t/float(cur_time)
    print("Iteration {} ({} sec, {} it/s)".format(t, cur_time, speed))

    Feasible = data["feasible"]
    Objectives = data["objectives"]
    scores = list(sorted((i for i in range(algorithm.mu) if Feasible[i]), key=lambda i: Objectives[i]))
    if scores:
        idx = scores[len(scores)/2]
        print("Current knee point objectives: {}".format(Objectives[idx]))

    print("Infeasible count: {}".format(algorithm.mu - sum(Feasible)))

def main(argv):
    # Initialize, read parameters from input and set up problems
    stamp = int(time.time())

    thread_manager = Thread_Manager()
    arguments = Arguments("settings.json", argv)

    runner = Planning_Runner(arguments, thread_manager, iteration_callback)

    arguments.check_help()

    t_max = runner.get_iteration_limit()
    size = runner.get_population_size()

    print("Settings: Algorithm {}, mu={}, t_max={}".format(runner.algorithm.get_name(), size, t_max))
    print("Steps: {}".format(runner.algorithm.steps))

    indices = runner.start()

    # Show feasible solutions in a sorted manner.
    if len(indices) == 0:
        print("No feasible solutions found after {} iterations!".format(t_max))
        return

    print("Search variables an objective values for feasible solutions:")
    # If we have fewer nondominated solutions than the total number of 
    # individuals, then only show the nondominated ones. Otherwise, just show 
    # all feasible solutions.
    c = 0
    for i in indices:
        c += 1

        positions, unsnappable = runner.get_positions_plot(i, c, len(indices))
        if positions.size == 0:
            continue

        print("{}. {} ({})".format(i, runner.get_objectives(i), unsnappable))

        do_data("positions-{}-{}".format(stamp, c), positions.tolist())
        do_plot("display-{}-{}.eps".format(stamp, c))

    # Plot the pareto front between the two objectives.
    print("Pareto front after t={}".format(t_max))

    runner.make_pareto_plot()

    do_plot("front-{}.eps".format(stamp))

if __name__ == "__main__":
    main(sys.argv[1:])
