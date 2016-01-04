import numpy as np
import matplotlib.pyplot as plt

class Viewer(object):
    def __init__(self, pixels, size):
        """
        Initialize the viewer object.
        """

        self.pixels = np.array(pixels).reshape(size)

    def show(self):
        """
        Display a heat map of the pixel intensities.
        """

        plt.imshow(self.pixels, origin='lower', cmap='Greys', interpolation='none')
        plt.show()
