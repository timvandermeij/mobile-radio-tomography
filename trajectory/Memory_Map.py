import numpy as np
from ..environment.Location_Proxy import Location_Proxy

class Memory_Map(object):
    """
    Memory map of the environment that a vehicle uses to keep track of regions
    of influence of known objects using measurements from a distance sensor.
    """

    def __init__(self, proxy, memory_size, resolution=1, altitude=0.0):
        """
        Create a memory map with a given number of meters per dimension
        `memory_size`, number of entries per meter `resolution`
        at the operating altitude `altitude` in meters.

        The `proxy` is a `Location_Proxy` object such as an `Environment`.
        """

        if not isinstance(proxy, Location_Proxy):
            raise TypeError("`proxy` must be a `Location_Proxy` such as an `Environment`")

        self.proxy = proxy
        self.geometry = self.proxy.geometry

        # The number of entries per dimension
        self.size = int(memory_size * resolution)
        self.resolution = resolution
        self.altitude = altitude

        self.clear()

        # The `bl` and `tr` are the first and last points that fit in the 
        # matrix in both dimensions, respectively. The bounds are based off 
        # from the current vehicle location, which is assumed to be in the 
        # center of the area of interest, at ground level, at the moment when 
        # the Memory_Map is initialized.
        offset = memory_size/2.0
        self.bl = self.proxy.get_location(-offset, -offset, self.altitude)
        self.tr = self.proxy.get_location(offset, offset, self.altitude)

        dlat, dlon = self.geometry.diff_location_meters(self.bl, self.tr)[:2]
        self.dlat = dlat
        self.dlon = dlon

    def clear(self):
        """
        Clear the memory map.
        """

        self.map = np.zeros((self.size, self.size))

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
        Convert a location `loc` to indices for a two-dimensional matrix.
        """

        dlat, dlon = self.geometry.diff_location_meters(self.bl, loc)[:2]
        y = (dlat / self.dlat) * self.size
        x = (dlon / self.dlon) * self.size
        return (int(y), int(x))

    def get_xy_index(self, loc):
        """
        Convert a location `loc` to indices for plotting (x,y).

        For any positioning other than displaying an image, matplotlib assumes
        the value is given in (x,y) order instead of (y,x).
        """

        return tuple(reversed(self.get_index(loc)))

    def index_in_bounds(self, i, j):
        """
        Check whether a given index is within the bounds of the memory map.

        The two-dimensional index is given separately as `i` and `j`,
        corresponding to y and x coordinates, respectively.
        """

        return 0 <= i < self.size and 0 <= j < self.size

    def location_in_bounds(self, loc):
        """
        Check whether a location `loc` is within the bounds of the memory map.
        """

        return self.index_in_bounds(*self.get_index(loc))

    def get(self, idx):
        """
        Retrieve the memory map value for a given index `idx`.

        The index is given as a sequence type (y,x).
        If the index is not within the bounds of the map, this method raises
        a `KeyError`. Otherwise, the numeric value in the map is returned.
        """

        i, j = idx
        if i < 0 or j < 0:
            raise KeyError("i={} and/or j={} incorrect: must be nonnegative indexes".format(i, j))

        try:
            return self.map[i, j]
        except IndexError as e:
            raise KeyError("i={} and/or j={} incorrect: {}".format(i, j, e.message))

    def set(self, idx, value=0):
        """
        Set the memory map value for a given index `idx` to a numerical `value`.

        The index is given as a sequence type.
        If the index is not within the bounds of the map, this method raises
        a `KeyError`. Otherwise, the value is set within the map.
        """

        i, j = idx
        if i < 0 or j < 0:
            raise KeyError("i={} and/or j={} incorrect: must be nonnegative indexes".format(i, j))

        try:
            self.map[i, j] = value
        except IndexError as e:
            raise KeyError("i={} and/or j={} incorrect: {}".format(i, j, e.message))

    def get_location_value(self, loc):
        """
        Retrieve the memory map value for a given Location `loc`.

        If the location is not within the bounds of the map, this method raises
        a `KeyError`. Otherwise, the numeric value in the map is returned.
        """

        return self.get(self.get_index(loc))

    def set_location_value(self, loc, value=0):
        """
        Set the memory map value for a given Location `loc` to a numerical
        `value`.

        If the location is not within the bounds of the map, this method raises
        a `KeyError`. Otherwise, the value is set at the corresponding index
        within the map.
        """

        idx = self.get_index(loc)
        self.set(idx, value=value)

    def set_multi(self, coords, value=0):
        """
        Set the memory map value for multiple coordinates `coords` at once to
        the same numerical `value`.

        The coordinates are given as a sequence of pairs, e.g., lists or tuples.
        The coordinates correspond with memory map indexes. If any of the
        indexes are not within the bounds of the map, this method raises
        a `KeyError`. Otherwise, the value is set to the appropriate locations
        within the map.
        """

        if not coords:
            return
        if any(idx[0] < 0 or idx[1] < 0 for idx in coords):
            raise KeyError("Some coordinates are invalid: must be nonnegative indexes")

        mask = zip(*coords)

        try:
            self.map[mask] = value
        except IndexError as e:
            raise KeyError("Some coordinates are invalid: {}".format(e.message))

    def get_location(self, i, j):
        """
        Convert an index to a Location object that describes the map location.

        The index is given separately as `i` and `j`.
        The given location is at the same altitude as the memory map.
        It might be an imprecise location for the grid index.
        """

        return self.geometry.get_location_meters(self.bl,
                                                 i/float(self.resolution),
                                                 j/float(self.resolution))

    def get_map(self):
        """
        Retrieve a numpy array containing the memory map values.
        """

        return self.map

    def get_nonzero(self):
        """
        Retrieve the indices of the map where there is an object.

        An object has a nonzero value stored in the map index.

        Returns a list of tuple indices.
        """

        return zip(*np.nonzero(self.map))

    def get_nonzero_array(self):
        """
        Retrieve an array of indices of the map where there is an object.

        Returns a numpy array with 2 columns with one index per row.
        """

        return np.array(np.nonzero(self.map)).T

    def get_nonzero_locations(self):
        """
        Retrieve location objects for the indices where there is an object.
        """

        return [self.get_location(*idx) for idx in self.get_nonzero()]

    def handle_sensor(self, sensor_distance, angle):
        """
        Add a detected object point to the map, given a distance sensor's
        measured distance `sensor_distance` and its current angle `angle`.

        Returns the calculated location of the detected point.
        """

        # Estimate the location of the point based on the distance from the 
        # distance sensor as well as our own angle.
        location = self.proxy.get_location()
        loc = self.geometry.get_location_angle(location, sensor_distance, angle)
        idx = self.get_index(loc)

        # Place point location in the memory map.
        try:
            self.set(idx, 1)
        except KeyError:
            pass

        return loc
