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
from planning.Runner import Planning_Runner
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

    runner = Planning_Runner(arguments)

    arguments.check_help()

    indices = runner.start()
    t_max = runner.get_iteration_limit()
    size = runner.get_population_size()

    # Show feasible solutions in a sorted manner.
    if len(indices) == 0:
        print("No feasible solutions found after {} iterations!".format(t_max))
        return

    print("Search variables an objective values for feasible solutions:")
    # If we have fewer nondominated solutions than the total number of 
    # individuals, then only show the nondominated ones. Otherwise, just show 
    # all feasible solutions.
    layer = 0 if len(indices) < size else None
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
