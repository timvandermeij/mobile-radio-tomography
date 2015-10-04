import math
import numpy as np

class Memory_Map(object):
    """
    A memory map of the environment that the drone keeps track of using measurements from the distance sensor.
    """

    def __init__(self, environment, memory_size):
        # The `bl` and `tr` are the first and last points that fit in the 
        # matrix in both dimensions, respectively. The bounds are based off 
        # from the current vehicle location. The `memory_size` is the number of 
        # entries per dimension.
        self.environment = environment
        self.geometry = self.environment.get_geometry()
        self.size = memory_size
        self.map = np.zeros((self.size, self.size))
        self.bl = self.environment.get_location(-self.size/2, -self.size/2)
        self.tr = self.environment.get_location(self.size/2, self.size/2)

    def get_index(self, loc):
        """
        Convert location coordinates to indices for a two-dimensional matrix.
        """
        dlat = self.tr.lat - self.bl.lat
        dlon = self.tr.lon - self.bl.lon
        y = ((loc.lat - self.bl.lat) / dlat) * self.size
        x = ((loc.lon - self.bl.lon) / dlon) * self.size
        return (y,x)

    def get_xy_index(self, loc):
        """
        Convert location coordinates to indices for plotting (x,y).

        For any positioning other than displaying an image, matplotlib assumes the value is given in (x,y) order instead of (y,x).
        """
        return list(reversed(self.get_index(loc)))

    def get(self, idx):
        i,j = idx
        if 0 <= i < self.size and 0 <= j < self.size:
            return self.map[i,j]

        raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def set(self, idx, value=0):
        i,j = idx
        if 0 <= i < self.size and 0 <= j < self.size:
            self.map[i,j] = value
        else:
            raise KeyError("i={} and/or j={} out of bounds ({}).".format(i, j, self.size))

    def get_location(self, i, j):
        return self.geometry.get_location_meters(self.bl, i, j)

    def get_map(self):
        return self.map

    def handle_sensor(self, sensor_distance, angle):
        # Estimate the location of the point based on the distance from the 
        # distance sensor as well as our own angle.
        dy = math.sin(angle) * sensor_distance
        dx = math.cos(angle) * sensor_distance
        loc = self.environment.get_location(dy, dx)
        idx = self.get_index(loc)

        print("Estimated location: {}, {} idx={}".format(loc.lat, loc.lon, idx))

        # Place point location in the memory map.
        try:
            self.set(idx, 1)
        except KeyError:
            pass
