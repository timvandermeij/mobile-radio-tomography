import numpy as np

class Dead_Reckoning(object):
    def __init__(self):
        """
        Initialize the dead reckoning object to an empty square.
        """

        self._position = (0, 0)

    def get(self):
        """
        Get the current position.
        """

        return self._position

    def set(self, distance, angle=90):
        """
        Set the current position given a traveled distance and an angle.
        """

        x = self._position[0] + (np.cos(np.deg2rad(angle)) * distance)
        y = self._position[1] + (np.sin(np.deg2rad(angle)) * distance)
        self._position = (x, y)
