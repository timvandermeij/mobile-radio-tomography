import sys
import numpy as np
import matplotlib.pyplot as plt

class Viewer(object):
    def __init__(self, size):
        """
        Initialize the viewer object.
        """

        self.size = size
        self.plot = None

    def show(self):
        """
        Display a heat map of the pixel intensities.
        """

        self.plot = plt.imshow(np.empty(self.size), origin='lower', cmap='Greys', interpolation='none')

    def update(self, pixels):
        """
        Update the viewer with new pixel data.
        """

        self.plot = plt.imshow(np.array(pixels).reshape(self.size), origin='lower', cmap='Greys', interpolation='none')
        plt.pause(sys.float_info.epsilon)
