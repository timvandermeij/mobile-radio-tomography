import sys
import time
from __init__ import __package__
from settings import Arguments
from reconstruction.Dump_Reader import Dump_Reader
from reconstruction.Weight_Matrix import Weight_Matrix
from reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from reconstruction.SVD_Reconstructor import SVD_Reconstructor
from reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor
from reconstruction.Viewer import Viewer

def main(argv):
    arguments = Arguments("settings.json", argv)
    settings = arguments.get_settings("reconstruction")

    # Create the reader.
    filename = settings.get("filename")
    reader = Dump_Reader("reconstruction_data/{}.json".format(filename))

    # Create the reconstructor.
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
    reconstructor = reconstructor_class(arguments)

    # Create the viewer.
    viewer = Viewer(arguments, reader.get_size())
    viewer.show()

    # Create the weight matrix.
    weight_matrix = Weight_Matrix(arguments, reader.get_origin(), reader.get_size())
    arguments.check_help()

    # Execute the reconstruction and visualization.
    rssi = []
    while reader.count_packets() > 0:
        packet = reader.get_packet()
        rssi.append(packet.get("rssi"))
        weight_matrix.update(packet)
        if weight_matrix.check():
            pixels = reconstructor.execute(weight_matrix.output(), rssi)
            viewer.update(pixels)
            time.sleep(settings.get("pause_time"))

if __name__ == "__main__":
    main(sys.argv[1:])
