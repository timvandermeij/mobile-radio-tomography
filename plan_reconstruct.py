import os
import sys
import time

import matplotlib
# Make it possible to run matplotlib in SSH
displayless = 'DISPLAY' not in os.environ or os.environ['DISPLAY'] == ''
if displayless:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

from __init__ import __package__
from planning import Reconstruction_Planning

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

def main(argv):
    # Initialize, read parameters from input and set up problems
    stamp = int(time.time())
    usage = "Usage: plan_reconstruct.py <problem> <algo> <mu> <t_max> <steps...>"
    try:
        p = argv[0].upper() if len(argv) > 0 else "RP"
        algo = argv[1].upper() if len(argv) > 1 else "SMS-EMOA"
        mu = int(argv[2]) if len(argv) > 2 else 15
        t_max = int(argv[3]) if len(argv) > 3 else 100
        steps = [float(s) for s in argv[4:]] if len(argv) > 4 else [0.5]
    except:
        print(usage)
        return

    # TODO: Define problem
    problem = None
    print(usage)
    return

    if algo == "NSGA":
        evo = Reconstruction_Planning.NSGA(problem, mu, t_max, steps)
    else:
        evo = Reconstruction_Planning.SMS_EMOA(problem, mu, t_max, steps)

    P, Objectives, Feasible = evo.evolve()

    # Print feasible solutions in a sorted manner.
    indices = [i for i in range(mu) if Feasible[i]]
    indices = sorted(indices, key=lambda i: Objectives[i][0])
    if len(indices) == 0:
        print("No feasible solutions found after {} iterations!".format(t_max))
    else:
        print("Search variables an objective values for feasible solutions:")
        for i in indices:
            print("{}. {}: {}".format(i, P[i], Objectives[i]))

    # Plot the pareto front between the two objectives.
    title = "Pareto front for {} with {}, t={}".format(p, algo, t_max)
    print(title)
    plt.clf()
    plt.title(title)
    plt.xlabel("Objective 1")
    plt.ylabel("Objective 2")
    o1 = [Objectives[i][0] for i in indices]
    o2 = [Objectives[i][1] for i in indices]
    plt.plot(o1, o2, marker='o')

    do_plot("front-{}.eps".format(stamp))

if __name__ == "__main__":
    main(sys.argv[1:])
