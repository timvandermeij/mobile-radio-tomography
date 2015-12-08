import math
import numpy as np

class Memory_Map(object):
    """
    A memory map of the environment that the vehicle keeps track of using measurements from the distance sensor.
    """

    def __init__(self, environment, memory_size, altitude):
        self.environment = environment
        self.geometry = self.environment.get_geometry()

        # The number of entries per dimension
        self.size = memory_size
        self.map = np.zeros((self.size, self.size))

        # The `bl` and `tr` are the first and last points that fit in the 
        # matrix in both dimensions, respectively. The bounds are based off 
        # from the current vehicle location.
        self.bl = self.environment.get_location(-self.size/2, -self.size/2, altitude)
        self.tr = self.environment.get_location(self.size/2, self.size/2, altitude)

        dlat, dlon, dalt = self.geometry.diff_location_meters(self.bl, self.tr)
        self.dlat = dlat
        self.dlon = dlon

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
        if 0 <= i < self.size and 0 <= j < self.size:
            return True

        return False

    def location_in_bounds(self, loc):
        return self.index_in_bounds(*self.get_index(loc))

    def get(self, idx):
        i,j = idx
        if self.index_in_bounds(i,j):
            return self.map[i,j]

        raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def set(self, idx, value=0):
        i,j = idx
        if self.index_in_bounds(i,j):
            self.map[i,j] = value
        else:
            raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def get_location(self, i, j):
        return self.geometry.get_location_meters(self.bl, i, j)

    def get_map(self):
        return self.map

    def get_nonzero(self):
        """
        Retrieve the indices where the map is nonzero, i.e. there is an object.
        """
        return zip(*np.nonzero(self.map == 1))

    def get_nonzero_locations(self):
        return [self.get_location(*idx) for idx in self.get_nonzero()]

    def handle_sensor(self, sensor_distance, angle):
        """
        Given a distance sensor's measured distance `sensor_distance` and its current angle `angle`, add the detected point to the memory map.
        Returns the calculated location of the detected point.
        """
        # Estimate the location of the point based on the distance from the 
        # distance sensor as well as our own angle.
        loc = self.geometry.get_location_angle(self.environment.get_location(), sensor_distance, angle)
        idx = self.get_index(loc)

        # Place point location in the memory map.
        try:
            self.set(idx, 1)
        except KeyError:
            pass

        return loc
