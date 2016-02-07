import sys
import numpy as np
import matplotlib.pyplot as plt
from ..settings import Arguments, Settings

class Viewer(object):
    def __init__(self, settings, size):
        """
        Initialize the viewer object.
        """

        if isinstance(settings, Arguments):
            settings = settings.get_settings("reconstruction_viewer")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

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

        plt.clf()
        self._plot = plt.imshow(np.array(pixels).reshape(self._size), origin='lower',
                               cmap=self._cmap, interpolation=self._interpolation)
        plt.pause(sys.float_info.epsilon)
