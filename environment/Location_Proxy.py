from ..geometry.Geometry import Geometry

class Location_Proxy(object):
    """
    An object that allows retrieving information about locations relative to the
    current position of a vehicle.
    """

    def __init__(self, geometry):
        if not isinstance(geometry, Geometry):
            raise TypeError("`geometry` must be an instance of `Geometry`")

        self._geometry = geometry

    @property
    def geometry(self):
        """
        Retrieve the `Geometry` object.
        """

        return self._geometry

    @property
    def location(self):
        """
        Retrieve the location of the vehicle that the proxy tracks.

        This can be one of the `LocationGlobal`, `LocationGlobalRelative` or
        `LocationLocal` types, or a multiple-frame `Locations` object, provided
        by `dronekit`. Preferably, it should be a location that the `Geometry`
        supports.
        """

        raise NotImplementedError("Subclasses must implement `location`")

    def get_location(self, north=0, east=0, alt=0):
        """
        Retrieve the current location of the vehicle that the proxy object is
        tracking, or a point relative to the location of the vehicle given by
        its `north`, `east` and `alt` offsets in meters.
        """

        return self._geometry.get_location_meters(self.location,
                                                  north, east, alt)

    def get_distance(self, location):
        """
        Get the distance to the `location` from the vehicle's location.
        """

        return self._geometry.get_distance_meters(self.location, location)
