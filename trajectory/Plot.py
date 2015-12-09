import math
import sys

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from matplotlib.collections import PatchCollection

from ..environment.Environment_Simulator import Environment_Simulator

class Plot(object):
    """
    Plotter that can display an environment memory map.
    """
    def __init__(self, environment, memory_map, interactive=True):
        self.environment = environment
        self.memory_map = memory_map
        self.interactive = interactive
        self._setup()

    def _create_patch(self, obj):
        if isinstance(obj, tuple):
            return Polygon([self.memory_map.get_xy_index(loc) for loc in obj])
        elif 'center' in obj:
            idx = self.memory_map.get_xy_index(obj['center'])
            return Circle(idx, radius=obj['radius'])

        return None

    def _setup(self):
        # "Cheat" to see 2d map of collision data
        patches = []
        if isinstance(self.environment, Environment_Simulator):
            for obj in self.environment.get_objects():
                patch = self._create_patch(obj)
                if patch is not None:
                    patches.append(patch)

        p = None
        if len(patches) > 0:
            p = PatchCollection(patches, cmap=matplotlib.cm.jet, alpha=0.4)
            patch_colors = 50*np.ones(len(patches))
            p.set_array(np.array(patch_colors))

        self.plot_polygons = p
        self.arrow_options = {
            "arrowstyle": "->",
            "color": "red",
            "linewidth": 2,
            "alpha": 0.5
        }
        self.plt = plt
        self.fig, self.ax = self.plt.subplots()

        # Set up interactive drawing of the memory map. This makes the 
        # dronekit/mavproxy fairly annoyed since it creates additional 
        # threads/windows. One might have to press Ctrl-C and normal keys to 
        # make the program stop.
        self.plt.gca().set_aspect("equal", adjustable="box")
        if self.interactive:
            self.plt.ion()
            self.plt.show()

    def get_plot(self):
        return self.plt

    def display(self):
        if self.plot_polygons is not None:
            self.ax.add_collection(self.plot_polygons)

        self._plot_vehicle_angle()

        self.plt.imshow(self.memory_map.get_map(), origin='lower')
        if self.interactive:
            self.plt.pause(sys.float_info.epsilon)
            self.plt.cla()
        else:
            self.plt.show()

    def plot_lines(self, points):
        geometry = self.environment.get_geometry()
        for edge in geometry.get_point_edges(points):
            start_idx = self.memory_map.get_xy_index(edge[0])
            end_idx = self.memory_map.get_xy_index(edge[1])
            plt.annotate("", end_idx, start_idx, arrowprops=self.arrow_options)

    def _plot_vehicle_angle(self):
        vehicle_idx = self.memory_map.get_xy_index(self.environment.get_location())
        angle = self.environment.get_angle()
        arrow_length = 10.0
        if angle == 0.5*math.pi:
            angle_idx = (vehicle_idx[0], vehicle_idx[1] + arrow_length)
        elif angle == 1.5*math.pi:
            angle_idx = (vehicle_idx[0], vehicle_idx[1] - arrow_length)
        else:
            angle_idx = (vehicle_idx[0] + math.cos(angle) * arrow_length, vehicle_idx[1] + math.sin(angle) * arrow_length)

        self.plt.annotate("", angle_idx, vehicle_idx, arrowprops=self.arrow_options)

    def close(self):
        self.plt.close()
        self.plt = None
