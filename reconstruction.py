import numpy as np
from __init__ import __package__
from reconstruction.Weight_Matrix import Weight_Matrix
from reconstruction.Reconstructor import Reconstructor
from reconstruction.Viewer import Viewer

def main():
    size = (4,4)
    positions = [(0,2), (2,0), (4, 2), (2,4)]
    distance_lambda = 0.5
    weight_matrix = Weight_Matrix(size, positions, distance_lambda)

    rssi = np.array([
        -39, -45, -43,
        -38, -37, -40,
        -46, -37, -38,
        -44, -39, -37
    ])
    reconstructor = Reconstructor(weight_matrix.create())
    pixels = reconstructor.execute(rssi)

    viewer = Viewer(pixels, size)
    viewer.show()

if __name__ == "__main__":
    main()
