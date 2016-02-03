from __init__ import __package__
from reconstruction.Snap_To_Boundary import Snap_To_Boundary

def main():
    snapper = Snap_To_Boundary([2,0], 4, 4)
    points = snapper.execute([1,1], [7,3])
    for point in points:
        print(point)

if __name__ == "__main__":
    main()
