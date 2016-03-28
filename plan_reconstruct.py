import os
import sys
import time
import json
import itertools

import matplotlib
# Make it possible to run matplotlib in SSH
displayless = 'DISPLAY' not in os.environ or os.environ['DISPLAY'] == ''
if displayless:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from __init__ import __package__
from planning.Problem import Reconstruction_Plan_Continuous, Reconstruction_Plan_Discrete
from planning import Algorithm
from settings import Arguments

def do_plot(name):
    """
    Finish plotting by saving or showing the plot.
    """

    if displayless or 'SAVE_PATH' in os.environ:
        path = os.environ['SAVE_PATH'] if 'SAVE_PATH' in os.environ else '.'
        filename = "{}/{}".format(path, name)
        plt.savefig(filename)
        print("Saved plot as {}".format(filename))
    else:
        print("Close the plot window to continue.")
        try:
            plt.show()
        except:
            # Somethimes things go wrong in the plot display (such as when 
            # clicking close button too fast), so ignore those errors.
            pass

def do_data(name, data):
    """
    Handle data output.
    Either write a JSON file with the given `name` for the `data` object, or
    print the data to the standard output.
    """

    if displayless or 'SAVE_PATH' in os.environ:
        path = os.environ['SAVE_PATH'] if 'SAVE_PATH' in os.environ else '.'
        filename = "{}/{}.json".format(path, name)
        with open(filename, 'wb') as f:
            json.dump(data, f)
    else:
        print(data)

def main(argv):
    # Initialize, read parameters from input and set up problems
    stamp = int(time.time())

    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("planning")
    algo = settings.get("algorithm_class")

    if settings.get("discrete"):
        problem = Reconstruction_Plan_Discrete(arguments)
    else:
        problem = Reconstruction_Plan_Continuous(arguments)

    if algo not in Algorithm.__dict__:
        raise ValueError("Algorithm class '{}' does not exist".format(algo))

    evo = Algorithm.__dict__[algo](problem, arguments)

    arguments.check_help()

    P, Objectives, Feasible = evo.evolve()

    # Print feasible solutions in a sorted manner.
    indices = [i for i in range(evo.mu) if Feasible[i]]
    indices = sorted(indices, key=lambda i: Objectives[i][0])

    if len(indices) == 0:
        print("No feasible solutions found after {} iterations!".format(evo.t_max))
        return

    R = evo.sort_nondominated(Objectives)

    print("Search variables an objective values for feasible solutions:")
    c = 0
    for i in indices:
        c += 1
        if not Feasible[i]:
            continue
        if len(indices) == evo.mu and i not in R[0]:
            continue

        positions, unsnappable = problem.get_positions(P[i])
        print("{}. {} ({})".format(i, Objectives[i], unsnappable))

        do_data("positions-{}-{}".format(stamp, c), positions.tolist())

        plt.clf()
        plt.title("Planned sensor positions for solution #{}/{} (index {}, f1 = {})".format(c, len(R[0]), i, Objectives[i][0]))
        plt.xlabel("x coordinate")
        plt.ylabel("y coordinate")
        plt.xlim([-0.1, problem.network_size[0]+0.1])
        plt.ylim([-0.1, problem.network_size[1]+0.1])
        plt.gca().set_aspect('equal', adjustable='box')
        plt.xticks(range(problem.network_size[0]+1))
        plt.yticks(range(problem.network_size[1]+1))
        plt.grid()
        # Make network size with padding visible
        plt.gca().add_patch(Rectangle((problem.padding[0], problem.padding[1]),
            problem.network_size[0]-problem.padding[0]*2,
            problem.network_size[1]-problem.padding[1]*2,
            alpha=0.2, edgecolor="grey"
        ))
        lines = [[(p[0,0], p[1,0]), (p[0,1], p[1,1])] for p in positions]

        plt.plot(*itertools.chain(*lines))
        plt.plot(positions[:,:,0].flatten(), positions[:,:,1].flatten(), 'ro')
        do_plot("display-{}-{}.eps".format(stamp, c))

    # Plot the pareto front between the two objectives.
    title = "Pareto front with {}, t={}".format(algo, evo.t_max)
    print(title)
    plt.clf()
    plt.title(title)
    plt.xlabel("Objective 1")
    plt.ylabel("Objective 2")
    for Rk in R:
        o1 = [Objectives[i][0] for i in Rk if Feasible[i]]
        o2 = [Objectives[i][1] for i in Rk if Feasible[i]]
        plt.plot(o1, o2, marker='o')

    do_plot("front-{}.eps".format(stamp))

if __name__ == "__main__":
    main(sys.argv[1:])
