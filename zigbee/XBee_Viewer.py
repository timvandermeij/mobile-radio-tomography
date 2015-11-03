import sys
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from math import *
from ..settings import Arguments, Settings

class XBee_Viewer(object):
    def __init__(self, settings):
        """
        Initialize the viewer. Note that this does not start the viewer yet.
        """

        if isinstance(settings, Arguments):
            self.settings = settings.get_settings("xbee_viewer")
        elif isinstance(settings, Settings):
            self.settings = settings
        else:
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self.points = []
        self.arrows = []
        self.started = False

    def _start(self):
        """
        Start the viewer by configuring and showing the (correctly scaled) plot window.
        """

        if self.started:
            return

        self.started = True
        plt.xlim(0, self.settings.get("size"))
        plt.ylim(0, self.settings.get("size"))
        plt.gca().set_aspect("equal", adjustable="box")
        plt.ion()
        plt.show()

    def draw_points(self):
        """
        Draw all points (representing the sensors in the network) in a circular shape.
        The spacing between the points is equal.
        """

        self._start()

        # Add an offset to display the circle in the middle of the plot window.
        offset = self.settings.get("size") / 2
        
        # Add the ground station separately.
        self.points.append((0,0))
        plt.plot(0, 0, linestyle="None", marker="o", color="black", markersize=10)

        for angle in np.arange(0, 2 * pi, (2 * pi) / self.settings.get("number_of_sensors")):
            x = offset + (cos(angle) * self.settings.get("circle_radius"))
            y = offset + (sin(angle) * self.settings.get("circle_radius"))
            self.points.append((x, y))
            plt.plot(x, y, linestyle="None", marker="o", color="black", markersize=10)

    def draw_arrow(self, point_from, point_to, color="red"):
        """
        Draw an arrow from a given point to another given point.
        """

        options = {
            "arrowstyle": "<-, head_width=1, head_length=1",
            "color": color,
            "linewidth": 2
        }
        arrow = plt.annotate("", self.points[point_from], self.points[point_to], arrowprops=options)
        self.arrows.append(arrow)

    def refresh(self):
        """
        Redraw the plot to make new arrows or points visible in the plot window.
        """

        plt.pause(sys.float_info.epsilon)

    def clear_arrows(self):
        """
        Remove all arrows from the plot.
        """

        for arrow in self.arrows:
            arrow.remove()

        self.arrows = []
