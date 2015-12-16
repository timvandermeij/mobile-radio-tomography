import math
import numpy as np

class Memory_Map(object):
    """
    A memory map of the environment that the vehicle keeps track of using measurements from the distance sensor.
    """

    def __init__(self, environment, memory_size, resolution=1, altitude=0.0):
        """
        Create a memory map with a given number of meters per dimension `memory_size`, number of entries per meter `resolution` at the operating altitude `altitude` in meters.
        """
        self.environment = environment
        self.geometry = self.environment.get_geometry()

        # The number of entries per dimension
        self.size = int(memory_size * resolution)
        self.resolution = resolution
        self.map = np.zeros((self.size, self.size))
        self.altitude = altitude

        # The `bl` and `tr` are the first and last points that fit in the 
        # matrix in both dimensions, respectively. The bounds are based off 
        # from the current vehicle location.
        self.bl = self.environment.get_location(-memory_size/2, -memory_size/2, self.altitude)
        self.tr = self.environment.get_location(memory_size/2, memory_size/2, self.altitude)

        dlat, dlon, dalt = self.geometry.diff_location_meters(self.bl, self.tr)
        self.dlat = dlat
        self.dlon = dlon

    def get_size(self):
        """
        Get the number of entries in each dimension.
        """
        return self.size

    def get_resolution(self):
        """
        Get the number of entries per meter in each dimension.
        """
        return self.resolution

    def get_index(self, loc):
        """
        Convert location coordinates to indices for a two-dimensional matrix.
        """
        dlat, dlon, dalt = self.geometry.diff_location_meters(self.bl, loc)
        y = (dlat / self.dlat) * self.size
        x = (dlon / self.dlon) * self.size
        return (int(y),int(x))

    def get_xy_index(self, loc):
        """
        Convert location coordinates to indices for plotting (x,y).

        For any positioning other than displaying an image, matplotlib assumes the value is given in (x,y) order instead of (y,x).
        """
        return tuple(reversed(self.get_index(loc)))

    def index_in_bounds(self, i, j):
        """
        Check whether a given index is within the bounds of the memory map.

        The two-dimensional index is given separately as `i` and `j`, corresponding to y and x coordinates, respectively.
        """
        if 0 <= i < self.size and 0 <= j < self.size:
            return True

        return False

    def location_in_bounds(self, loc):
        """
        Check whether a given location `loc` is within the bounds of the memory map.
        """
        return self.index_in_bounds(*self.get_index(loc))

    def get(self, idx):
        """
        Retrieve the memory map value for a given index `idx`.

        The index is given as a sequence type.
        If the index is not within the bounds of the map, a `KeyError` is raised.
        Otherwise, the value in the map is returned.
        """
        i,j = idx
        if self.index_in_bounds(i,j):
            return self.map[i,j]

        raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def set(self, idx, value=0):
        """
        Set the memory map value for a given index `idx` to a numerical `value`.

        The index is given as a sequence type.
        If the index is not within the bounds of the map, a `KeyError` is raised.
        Otherwise, the value is set within the map.
        """
        i,j = idx
        if self.index_in_bounds(i,j):
            self.map[i,j] = value
        else:
            raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def get_location(self, i, j):
        """
        Convert an index to a Location object that describes the map location.

        The index is given separately as `i` and `j`.
        The given location is at the same altitude as the memory map.
        It might be an imprecise location for the grid index.
        """
        return self.geometry.get_location_meters(self.bl, i/float(self.resolution), j/float(self.resolution))

    def get_map(self):
        """
        Retrieve a numpy array containing the memory map values.
        """
        return self.map

    def get_nonzero(self):
        """
        Retrieve the indices where the map is nonzero, i.e. there is an object.
        """
        return zip(*np.nonzero(self.map == 1))

    def get_nonzero_locations(self):
        """
        Retrieve Location objects for the indices where there is an object.
        """
        return [self.get_location(*idx) for idx in self.get_nonzero()]

    def handle_sensor(self, sensor_distance, angle):
        """
        Given a distance sensor's measured distance `sensor_distance` and its current angle `angle`, add the detected point to the memory map.
        Returns the calculated location of the detected point.
        """
        # Estimate the location of the point based on the distance from the 
        # distance sensor as well as our own angle.
        location = self.environment.get_location()
        loc = self.geometry.get_location_angle(location, sensor_distance, angle)
        idx = self.get_index(loc)

        # Place point location in the memory map.
        try:
            self.set(idx, 1)
        except KeyError:
            pass

        return loc
