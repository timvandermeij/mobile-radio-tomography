import sys
import numpy as np
import matplotlib.pyplot as plt

class Dead_Reckoning_Map(object):
    def __init__(self, size=10, resolution=10):
        """
        Initialize the dead reckoning map to an empty square.
        """

        self._resolution = resolution

        self._map = np.zeros((size * resolution, size * resolution))
        self._position = (0, 0)

        self._image = plt.imshow(self._map, origin='lower', cmap='Greys', interpolation='none')

    def get(self):
        """
        Get the entire dead reckoning map.
        """

        return self._map

    def set(self, distance, angle=90):
        """
        Set a point on the dead reckoning map given a traveled
        distance and an angle.
        """

        x = self._position[0] + (np.cos(np.deg2rad(angle)) * distance)
        y = self._position[1] + (np.sin(np.deg2rad(angle)) * distance)

        pixel_x = round(x * self._resolution)
        pixel_y = round(y * self._resolution)

        self._map[pixel_y][pixel_x] = 1
        self._position = (x, y)

    def plot(self):
        """
        Visualize the points in the dead reckoning map.
        """

        self._image.set_data(self._map)
        self._image.autoscale()
        plt.pause(sys.float_info.epsilon)
