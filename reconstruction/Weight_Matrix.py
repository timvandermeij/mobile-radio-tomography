import itertools
import numpy as np

class Weight_Matrix(object):
    def __init__(self, size, positions, distance_lambda):
        """
        Initialize the weight matrix object.
        """

        self._size = size
        self._positions = positions
        self._lambda = distance_lambda

    def create(self):
        """
        Create a weight matrix for the reconstruction phase.

        Refer to the following papers for the principles or code
        that this method is based on:
        - "Radio tomographic imaging with wireless networks" by
          Joey Wilson and Neal Patwari
        - "Algorithms and models for radio tomographic imaging"
          by Alyssa Milburn
        """

        # Prepare sensor and link data. Only links with different source
        # and destination sensors are used, so there are no self links.
        sensor_count = len(self._positions)
        sensors = range(sensor_count)
        link_count = (sensor_count ** 2) - sensor_count
        links = list(itertools.permutations(sensors, 2))
        width, height = self._size

        # Create a mesh grid for the space covered by the sensors.
        # This represents a pixel grid that we use to find out which
        # pixels are intersected by a link.
        coordinatesX, coordinatesY = zip(*self._positions)
        x = np.linspace(min(coordinatesX), max(coordinatesX), width)
        y = np.linspace(min(coordinatesY), max(coordinatesY), height)
        gridX, gridY = np.meshgrid(x, y)

        # Calculate the distance from each sensor to each pixel on
        # the grid using the Pythagorean theorem.
        distances = np.zeros((sensor_count, width * height))
        for sensor_id in sensors:
            position = self._positions[sensor_id]
            distance = np.sqrt((gridX - position[0]) ** 2 + (gridY - position[1]) ** 2)
            distances[sensor_id] = distance.flatten()

        # Create the weight matrix using the Pythagorean theorem for
        # calculation of the link lengths. The weight matrix contains
        # the weight of each pixel on the grid for each link. An ellipse
        # model is applied to determine which pixels have an influence
        # on the measured signal strength of a link. Pixels that have
        # no influence have a weight of zero. A higher weight implies
        # a higher influence on the signal strength. Pixels of short
        # links have a higher weight than those of longer links.
        weight_matrix = np.zeros((link_count, width * height))
        for index, link in enumerate(links):
            source_id, destination_id = link
            source = self._positions[source_id]
            destination = self._positions[destination_id]
            length = np.sqrt((destination[0] - source[0]) ** 2 + (destination[1] - source[1]) ** 2)
            weight = (distances[source_id] + distances[destination_id] < length + self._lambda)
            weight_matrix[index] = (1.0 / np.sqrt(length)) * weight

        return weight_matrix
