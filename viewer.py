import matplotlib.pyplot as plt
import numpy as np
from settings.Settings import Settings
from math import *

class Viewer:
    def __init__(self, settings):
        # Initialize the viewer with a correctly scaled plot.
        self.points = []
        self.settings = settings

        plt.xlim(0, self.settings.get("size"))
        plt.ylim(0, self.settings.get("size"))
        plt.gca().set_aspect("equal", adjustable="box")

    def draw_points(self):
        # Draw a static point for each sensor in a circular shape. The
        # spacing between the points is equal. We add an offset to display
        # the circle in the middle of the plot.
        offset = self.settings.get("size") / 2
        for angle in np.arange(0, 2 * pi, (2 * pi) / self.settings.get("number_of_sensors")):
            x = offset + (cos(angle) * self.settings.get("circle_radius"))
            y = offset + (sin(angle) * self.settings.get("circle_radius"))
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
    settings = Settings("settings.json", "viewer")

    viewer = Viewer(settings)
    viewer.draw_points()
    viewer.draw_arrow(1, 3)
    viewer.display()

if __name__ == "__main__":
    main()
