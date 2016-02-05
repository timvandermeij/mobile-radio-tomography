from __init__ import __package__
from reconstruction.Snap_To_Boundary import Snap_To_Boundary

def main():
    snapper = Snap_To_Boundary([0, 0], 10, 10)
    points = snapper.execute([0, 5.55], [10, -12.51])
    for point in points:
        print(point)

if __name__ == "__main__":
    main()
