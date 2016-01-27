import numpy as np
from time import time

class Dead_Reckoning(object):
    def __init__(self):
        """
        Initialize the dead reckoning object.
        """

        self._position = (0.0, 0.0)
        self._last_time = 0.0
        self._last_vx = 0.0
        self._last_vy = 0.0

    def get(self):
        """
        Get the current position.
        """

        return self._position

    def set_velocity(self, vx, vy):
        """
        Set the current position given speeds in two components.
        """

        cur_time = time()
        if self._last_time == 0.0:
            dt = 0.01
        else:
            dt = cur_time - self._last_time

        x = self._position[0] + (vx + self._last_vx)/2 * dt
        y = self._position[1] + (vy + self._last_vy)/2 * dt
        self._position = (x, y)
        self._last_time = cur_time

    def set(self, distance, angle=0):
        """
        Set the current position given a traveled distance and an angle in radians.
        """

        x = self._position[0] + (np.cos(angle) * distance)
        y = self._position[1] + (np.sin(angle) * distance)
        self._position = (x, y)
