import numpy as np
from __init__ import __package__
from reconstruction.Signal_Strength_File_Reader import Signal_Strength_File_Reader
from reconstruction.Weight_Matrix import Weight_Matrix
from reconstruction.Least_Squares_Reconstructor import Least_Squares_Reconstructor
from reconstruction.Viewer import Viewer

def main():
    size = (21,21)
    positions = [
        (0,0), (0,3), (0,6), (0,9), (0,12), (0,15), (0,18), (0,21), (3,21),
        (6,21), (9,21), (12,21), (15,21), (18,21), (21,21), (21,18), (21,15),
        (21,12), (21,9), (21,6), (21,3), (21,0), (18,0), (15,0), (12,0), (9,0),
        (6,0), (2,0)
    ]
    distance_lambda = 0.2
    weight_matrix = Weight_Matrix(size, positions, distance_lambda)

    walking = Signal_Strength_File_Reader('walking.csv', len(positions))
    walking_rssi = walking.read()
    reconstructor = Least_Squares_Reconstructor(weight_matrix.create())
    pixels = reconstructor.execute(walking_rssi)

    viewer = Viewer(pixels, size)
    viewer.show()

if __name__ == "__main__":
    main()
