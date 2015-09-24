import matplotlib.pyplot as plt
import numpy as np
from math import *

VIEWER_NUMBER_OF_SENSORS = 8
VIEWER_SIZE = 10 # width and height
VIEWER_CIRCLE_RADIUS = 3

class Viewer:
    def __init__(self):
        # Initialize the viewer with a correctly scaled plot.
        self.points = []

        plt.xlim(0, VIEWER_SIZE)
        plt.ylim(0, VIEWER_SIZE)
        plt.gca().set_aspect("equal", adjustable="box")

    def draw_points(self):
        # Draw a static point for each sensor in a circular shape. The
        # spacing between the points is equal. We add an offset to display
        # the circle in the middle of the plot.
        offset = VIEWER_SIZE / 2
        for angle in np.arange(0, 2 * pi, (2 * pi) / VIEWER_NUMBER_OF_SENSORS):
            x = offset + (cos(angle) * VIEWER_CIRCLE_RADIUS)
            y = offset + (sin(angle) * VIEWER_CIRCLE_RADIUS)
            self.points.append((x, y))
            plt.plot(x, y, linestyle="None", marker="o", color="black", markersize=10)

    def draw_arrow(self, point_from, point_to):
        # Draw an arrow from a given point to another given point.
        options = {
            "arrowstyle": "<-, head_width=1, head_length=1",
            "color": "red",
            "linewidth": 3
        }
        plt.annotate("", self.points[point_from - 1], self.points[point_to - 1], arrowprops=options)

    def display(self):
        plt.show()

def main():
    viewer = Viewer()
    viewer.draw_points()
    viewer.draw_arrow(1, 3)
    viewer.display()

if __name__ == "__main__":
    main()
