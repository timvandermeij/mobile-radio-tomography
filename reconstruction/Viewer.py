import sys
import numpy as np
import matplotlib.pyplot as plt
from ..settings import Arguments

class Viewer(object):
    def __init__(self, arguments, size):
        """
        Initialize the viewer object.
        """

        if isinstance(arguments, Arguments):
            settings = arguments.get_settings("reconstruction")
        else:
            raise ValueError("'settings' must be an instance of Arguments")

        self._interpolation = settings.get('interpolation')
        self._cmap = settings.get('cmap')
        self._size = size
        self._plot = None

    def show(self):
        """
        Display a heat map of the pixel intensities.
        """

        self._plot = plt.imshow(np.empty(self._size), origin='lower',
                                cmap=self._cmap, interpolation=self._interpolation)

    def update(self, pixels):
        """
        Update the viewer with new pixel data.
        """

        self._plot = plt.imshow(np.array(pixels).reshape(self._size), origin='lower',
                               cmap=self._cmap, interpolation=self._interpolation)
        plt.pause(sys.float_info.epsilon)
