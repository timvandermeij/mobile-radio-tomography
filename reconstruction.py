import sys
from __init__ import __package__
from settings import Arguments
from reconstruction.Dump_Reader import Dump_Reader
from reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from reconstruction.SVD_Reconstructor import SVD_Reconstructor
from reconstruction.Truncated_SVD_Reconstructor import Truncated_SVD_Reconstructor

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

    arguments.check_help()

    filename = settings.get("filename")
    data = Dump_Reader("reconstruction_data/{}.json".format(filename))
    while data.count_packets() > 0:
        print(data.get_packet().get_all())

if __name__ == "__main__":
    main(sys.argv[1:])
