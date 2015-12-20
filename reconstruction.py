from __init__ import __package__
from reconstruction.Weight_Matrix import Weight_Matrix

def main():
    size = (4,4)
    positions = [(0,2), (2,0), (4, 2), (2,4)]
    distance_lambda = 0.5
    weight_matrix = Weight_Matrix(size, positions, distance_lambda)
    print(weight_matrix.create())

if __name__ == "__main__":
    main()
