import os
import sys
import time
import json

import matplotlib
# Make it possible to run matplotlib in SSH
displayless = 'DISPLAY' not in os.environ or os.environ['DISPLAY'] == ''
if displayless:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

from __init__ import __package__
from planning.Problem import Reconstruction_Plan
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
    algo = settings.get("algorithm_class").upper().replace('-','_')

    problem = Reconstruction_Plan(arguments)

    if algo not in Algorithm.__dict__:
        raise ValueError("Algorithm class '{}' does not exist".format(algo))

    evo = Algorithm.__dict__[algo](problem, arguments)

    arguments.check_help()

    P, Objectives, Feasible = evo.evolve()

    # Print feasible solutions in a sorted manner.
    indices = [i for i in range(evo.mu) if Feasible[i]]
    indices = sorted(indices, key=lambda i: Objectives[i][0])
    R = evo.sort_nondominated(Objectives)

    if len(indices) == 0:
        print("No feasible solutions found after {} iterations!".format(evo.t_max))
    else:
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

            do_data("positions-{}-{}".format(stamp, c), [(p[0], p[1]) for p in positions])

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
            lines = []
            for p in range(0,len(positions),2):
                lines.extend([(positions[p][0], positions[p+1][0]), (positions[p][1], positions[p+1][1]), 'b-'])

            plt.plot(*lines)
            plt.plot([positions[p][0] for p in range(len(positions))], [positions[p][1] for p in range(len(positions))], 'ro')
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
