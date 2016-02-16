import numpy as np
from Snap_To_Boundary import Snap_To_Boundary
from ..settings import Arguments, Settings

class Weight_Matrix(object):
    def __init__(self, settings, origin, size):
        """
        Initialize the weight matrix object.
        """

        if isinstance(settings, Arguments):
            settings = settings.get_settings("reconstruction_weight_matrix")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._lambda = settings.get("distance_lambda")

        self._origin = origin
        self._width, self._height = size
        self._snapper = Snap_To_Boundary(self._origin, self._width, self._height)

        # Create a grid for the space covered by the network. This represents a pixel
        # grid that we use to determine which pixels are intersected by a link. The
        # value 0.5 is used to obtain the center of each pixel.
        x = np.linspace(0.5, self._width - 0.5, self._width)
        y = np.linspace(0.5, self._height - 0.5, self._height)
        self._gridX, self._gridY = np.meshgrid(x, y)

        self.reset()

    def update(self, source, destination):
        """
        Update the weight matrix. Each update adds a new row to the matrix.
        This method returns whether or not the update was successful.

        Refer to the following papers for the principles or code
        that this method is based on:
        - "Radio tomographic imaging with wireless networks" by
          Joey Wilson and Neal Patwari
        - "Algorithms and models for radio tomographic imaging"
          by Alyssa Milburn
        """

        # Snap the source and destination points to the boundaries of the network.
        snapped_points = self._snapper.execute(source, destination)
        if snapped_points is None:
            # If the points cannot be snapped, ignore the measurement.
            return False

        source, destination = snapped_points

        # Get the index of the source sensor. Add it to the list if it does not exist.
        new_sensors = []
        try:
            source_index = self._sensors.index(source)
        except ValueError:
            self._sensors.append(source)
            new_sensors.append(source)
            source_index = len(self._sensors) - 1

        # Get the index of the destination sensor. Add it to the list if it does not exist.
        try:
            destination_index = self._sensors.index(destination)
        except ValueError:
            self._sensors.append(destination)
            new_sensors.append(destination)
            destination_index = len(self._sensors) - 1

        # Calculate the distance from a sensor to each center of a pixel on the
        # grid using the Pythagorean theorem. Do this only for new sensors.
        for sensor in new_sensors:
            distance = np.sqrt((self._gridX - sensor[0]) ** 2 + (self._gridY - sensor[1]) ** 2)
            self._distances = np.vstack([self._distances, distance.flatten()])

        # Update the weight matrix by adding a row for the new link. We use the
        # Pythagorean theorem for calculation of the link's length. The weight matrix
        # contains the weight of each pixel on the grid for each link. An ellipse
        # model is applied to determine which pixels have an influence on the measured
        # signal strength of a link. Pixels that have no influence have a weight of
        # zero. A higher weight implies a higher influence on the signal strength.
        # Pixels of short links have a higher weight than those of longer links.
        length = np.sqrt((destination[0] - source[0]) ** 2 + (destination[1] - source[1]) ** 2)
        weight = (self._distances[source_index] + self._distances[destination_index] < length + self._lambda)
        row = (1.0 / np.sqrt(length)) * weight
        self._matrix = np.vstack([self._matrix, row])

        return True

    def check(self):
        """
        Check if the weight matrix is complete, i.e., if the columns of the
        matrix all contain at least one non-zero entry.
        """

        return all(self._matrix.any(axis=0))

    def output(self):
        """
        Output the weight matrix only if it is complete.
        """

        if not self.check():
            raise ValueError("The weight matrix contains columns with only zeros.")

        return self._matrix

    def reset(self):
        """
        Reset the weight matrix object to its default state.
        """

        self._matrix = np.empty((0, self._width * self._height))
        self._distances = np.empty((0, self._width * self._height))
        self._sensors = []
