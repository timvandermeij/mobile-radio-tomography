import json
import sys
import numpy as np
from __init__ import __package__
from settings import Arguments
from reconstruction.Signal_Strength_File_Reader import Signal_Strength_File_Reader
from reconstruction.Weight_Matrix import Weight_Matrix
from reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from reconstruction.SVD_Reconstructor import SVD_Reconstructor
from reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor
from reconstruction.Viewer import Viewer

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("reconstruction")

    # Set the reconstructor class.
    reconstructors = {
        "least-squares": Least_Squares_Reconstructor,
        "svd": SVD_Reconstructor,
        "truncated-svd": Truncated_SVD_Reconstructor
    }
    reconstructor = settings.get("reconstructor")
    if reconstructor not in reconstructors:
        print("Unknown reconstructor '{}'".format(reconstructor))
        sys.exit(1)

    reconstructor_class = reconstructors[reconstructor]

    # Read the reconstruction data file.
    filename = settings.get("filename")
    with open("reconstruction_data/{}.json".format(filename)) as data:
        reconstruction_data = json.load(data)
        size = reconstruction_data["size"]
        positions = reconstruction_data["positions"]

    weight_matrix = Weight_Matrix(arguments, size, positions)
    reconstructor = reconstructor_class(arguments, weight_matrix.create())

    viewer = Viewer(arguments, size)
    viewer.show()

    arguments.check_help()

    data = Signal_Strength_File_Reader("reconstruction_data/{}.csv".format(filename),
                                       len(positions))
    previous_sweep = None
    for _ in range(data.size()):
        sweep = data.get_sweep()
        if previous_sweep is not None:
            # Generally successive sweeps are very similar. Subtracting the previous
            # sweep from the current sweep makes differences stand out more.
            pixels = reconstructor.execute(sweep - previous_sweep)
        else:
            pixels = reconstructor.execute(sweep)
        previous_sweep = sweep
        viewer.update(pixels)

if __name__ == "__main__":
    main(sys.argv[1:])
