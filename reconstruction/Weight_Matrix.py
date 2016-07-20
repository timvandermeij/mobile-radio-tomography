# Library imports
import numpy as np

# Package imports
from Snap_To_Boundary import Snap_To_Boundary, Point
from ..core.Import_Manager import Import_Manager
from ..settings import Arguments

class Weight_Matrix(object):
    def __init__(self, arguments, origin, size, snap_inside=False,
                 number_of_links=0):
        """
        Initialize the weight matrix object.

        The `arguments` is an `Arguments` object. The `origin` is a tuple of two
        coordinates in `(x, y)` form of the bottom left point of the network.
        `size` is a tuple of the same form, containing the width and height of
        the network.

        If `snap_inside` is `True`, then sensor locations inside the network are
        allowed, but snapped to the network boundary. Otherwise, they are
        silently excluded. If `number_of_links` is not `0`, then the weight
        matrix is prefilled with this number of rows, which may be useful in
        contexts where we know the number of measurements beforehand.
        """

        if isinstance(arguments, Arguments):
            settings = arguments.get_settings("reconstruction")
        else:
            raise TypeError("'arguments' must be an instance of Arguments")

        # Create the model object.
        import_manager = Import_Manager()
        model_class = settings.get("model_class")
        model_type = import_manager.load_class(model_class,
                                               relative_module="reconstruction")
        self._model = model_type(arguments)

        # Create the snap to boundary object and initialize variables for the matrix.
        self._distances = None
        self._matrix = None
        self._origin = origin
        self._width, self._height = size

        self._number_of_links = number_of_links
        self._snapper = Snap_To_Boundary(self._origin, self._width,
                                         self._height, snap_inside=snap_inside)

        # Create a grid for the space covered by the network. This represents a pixel
        # grid that we use to determine which pixels are intersected by a link. The
        # value 0.5 is used to obtain the center of each pixel.
        offset_x, offset_y = self._origin
        x = np.linspace(offset_x + 0.5, offset_x + self._width - 0.5, self._width)
        y = np.linspace(offset_y + 0.5, offset_y + self._height - 0.5, self._height)
        self._grid_x, self._grid_y = np.meshgrid(x, y)

        self.reset()

    def is_valid_point(self, point):
        """
        Check whether a given `point` is a valid sensor position, i.e., it is
        outside the network.
        """

        return self._snapper.is_outside(Point(point[0], point[1]))

    def update(self, source, destination):
        """
        Update the weight matrix with a measurement between a `source` and
        `destination` sensor, both given as a tuple of coordinates.
        Each successful update adds a new row to the matrix.
        This method returns a list of coordinate tuples for the two sensors
        in case the update was successful. Otherwise, `None` is returned.

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
            return None

        source, destination = snapped_points

        # Get the index of the source sensor. Add it if it does not exist.
        new_sensors = []
        try:
            source_index = self._sensors[source]
        except KeyError:
            source_index = len(self._sensors)
            self._sensors[source] = source_index
            new_sensors.append(source)

        # Get the index of the destination sensor. Add it if it does not exist.
        try:
            destination_index = self._sensors[destination]
        except KeyError:
            destination_index = len(self._sensors)
            self._sensors[destination] = destination_index
            new_sensors.append(destination)

        # Calculate the distance from a sensor to each center of a pixel on the
        # grid using the Pythagorean theorem. Do this only for new sensors.
        for sensor in new_sensors:
            distance = np.sqrt((self._grid_x - sensor[0]) ** 2 + (self._grid_y - sensor[1]) ** 2)
            if self._distance_count >= self._number_of_links:
                self._distances = np.vstack([self._distances, distance.flatten()])
            else:
                self._distances[self._distance_count, :] = distance.flatten()

            self._distance_count += 1

        # Update the weight matrix by adding a row for the new link. We use the
        # Pythagorean theorem for calculation of the link's length. The weight matrix
        # contains the weight of each pixel on the grid for each link. An ellipse
        # model is applied to determine which pixels have an influence on the measured
        # signal strength of a link. Pixels that have no influence have a weight of
        # zero. A higher weight implies a higher influence on the signal strength.
        # Pixels of short links have a higher weight than those of longer links.
        length = np.sqrt((destination[0] - source[0]) ** 2 + (destination[1] - source[1]) ** 2)
        if length == 0:
            # Source and destination are equal, which might happen after
            # snapping the points to the boundaries.
            return None

        row = self._model.assign(length, self._distances[source_index],
                                 self._distances[destination_index])
        if self._link_count >= self._number_of_links:
            self._matrix = np.vstack([self._matrix, row])
        else:
            self._matrix[self._link_count, :] = row

        self._link_count += 1

        return snapped_points

    def check(self):
        """
        Check if the weight matrix is complete, i.e., if the columns of the
        matrix all contain at least one non-zero entry.
        """

        return all(self._matrix.any(axis=0))

    def output(self):
        """
        Output the weight matrix.
        """

        return self._matrix

    def reset(self):
        """
        Reset the weight matrix object to its default state.
        """

        self._link_count = 0
        self._distance_count = 0
        self._matrix = np.empty((self._number_of_links, self._width * self._height))
        self._distances = np.empty((self._number_of_links, self._width * self._height))
        self._sensors = {}
