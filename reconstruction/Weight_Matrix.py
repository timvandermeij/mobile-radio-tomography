import numpy as np
from ..settings import Arguments, Settings

class Weight_Matrix(object):
    def __init__(self, settings, size):
        """
        Initialize the weight matrix object.
        """

        if isinstance(settings, Arguments):
            settings = settings.get_settings("reconstruction_weight_matrix")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._lambda = settings.get("distance_lambda")

        self._width, self._height = size
        self._matrix = np.empty((0, self._width * self._height))
        self._sensors = []
        self._links = []

    def update(self, packet):
        """
        Update the weight matrix with a packet. Each update adds a new
        row to the weight matrix.

        Refer to the following papers for the principles or code
        that this method is based on:
        - "Radio tomographic imaging with wireless networks" by
          Joey Wilson and Neal Patwari
        - "Algorithms and models for radio tomographic imaging"
          by Alyssa Milburn
        """

        # Get the index of the source sensor. Add it to the list if it does not exist.
        # TODO: snap to boundary
        source = (packet.get("from_latitude"), packet.get("from_longitude"))
        try:
            source_index = self._sensors.index(source)
        except ValueError:
            self._sensors.append(source)
            source_index = len(self._sensors) - 1

        # Get the index of the destination sensor. Add it to the list if it does not exist.
        # TODO: snap to boundary
        destination = (packet.get("to_latitude"), packet.get("to_longitude"))
        try:
            destination_index = self._sensors.index(destination)
        except ValueError:
            self._sensors.append(destination)
            destination_index = len(self._sensors) - 1

        # Add the link to the link list.
        # TODO: do we need to keep this?
        link = (source_index, destination_index)
        self._links.append(link)

        # Create a mesh grid for the space covered by the sensors.
        # This represents a pixel grid that we use to find out which
        # pixels are intersected by a link.
        # TODO: optimize
        coordinatesX, coordinatesY = zip(*self._sensors)
        x = np.linspace(min(coordinatesX), max(coordinatesX), self._width)
        y = np.linspace(min(coordinatesY), max(coordinatesY), self._height)
        gridX, gridY = np.meshgrid(x, y)

        # Calculate the distance from each sensor to each pixel on
        # the grid using the Pythagorean theorem.
        # TODO: optimize
        distances = np.empty((len(self._sensors), self._width * self._height))
        for index, sensor in enumerate(self._sensors):
            distance = np.sqrt((gridX - sensor[0]) ** 2 + (gridY - sensor[1]) ** 2)
            distances[index] = distance.flatten()

        # Update the weight matrix by adding a row for the new link. We use the
        # Pythagorean theorem for calculation of the link's length. The weight matrix
        # contains the weight of each pixel on the grid for each link. An ellipse
        # model is applied to determine which pixels have an influence on the measured
        # signal strength of a link. Pixels that have no influence have a weight of
        # zero. A higher weight implies a higher influence on the signal strength.
        # Pixels of short links have a higher weight than those of longer links.
        source_id, destination_id = link
        source = self._sensors[source_id]
        destination = self._sensors[destination_id]
        length = np.sqrt((destination[0] - source[0]) ** 2 + (destination[1] - source[1]) ** 2)
        weight = (distances[source_id] + distances[destination_id] < length + self._lambda)
        row = (1.0 / np.sqrt(length)) * weight
        self._matrix = np.vstack([self._matrix, row])

        # TODO: remove old data after a while?

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
