import math
from dronekit import Locations, LocationLocal, LocationGlobal, LocationGlobalRelative
from Geometry import Geometry

class Geometry_Spherical(Geometry):
    """
    Geometry that operates on a spherical Earth.
    """

    # Radius of "spherical" earth
    EARTH_RADIUS = 6378137.0

    COORD_TO_METERS = 1.113195e5

    def __init__(self):
        super(Geometry_Spherical, self).__init__()
        self.home_location = LocationGlobal(0.0, 0.0, 0.0)

    def set_home_location(self, home_location):
        if isinstance(home_location, Locations):
            self.home_location = home_location.global_frame
        elif isinstance(home_location, LocationGlobal):
            self.home_location = home_location
        else:
            raise TypeError("Home location must be global for spherical geometry, got: {}".format(home_location))

    def get_location_frame(self, location):
        if not isinstance(location, Locations):
            raise TypeError("`location` must be a `Locations` object")

        return location.global_relative_frame

    def get_locations_frame(self, location1, location2):
        """
        Retrieve the location frame from a `Locations` object `location1` that
        is of equal type as `location2`.
        """

        if not isinstance(location1, Locations):
            raise TypeError("`location1` must be a `Locations` object")

        if isinstance(location2, LocationLocal):
            return location1.local_frame
        if isinstance(location2, LocationGlobal):
            return location1.global_frame
        if isinstance(location2, (Locations, LocationGlobalRelative)):
            return location1.global_relative_frame

        raise TypeError("`location2` must be a `Location` type")

    def equalize(self, location1, location2):
        # If one of the locations is a `Locations` object, retrieve the frame 
        # that is equal to the other.
        if isinstance(location1, Locations):
            location1 = self.get_locations_frame(location1, location2)
        if isinstance(location2, Locations):
            location2 = self.get_locations_frame(location2, location1)

        # Safety check that the provided locations are supported.
        valid_types = (LocationLocal, LocationGlobal, LocationGlobalRelative)
        if not isinstance(location1, valid_types):
            raise TypeError("`location1` must be a `Location` type")
        if not isinstance(location2, valid_types):
            raise TypeError("`location2` must be a `Location` type")

        # If the locations are of equal types due to the `Locations` frame 
        # matching, or they had equal types to begin with, then we return them.
        if type(location1) is type(location2):
            return location1, location2

        # If one of the locations is a `LocationLocal` object, then use its 
        # coordinates to make a global relative location.
        if isinstance(location1, LocationLocal):
            coords = self.get_coordinates(location1)
            location1 = self.get_location_meters(self.home_location, *coords)
        elif isinstance(location2, LocationLocal):
            coords = self.get_coordinates(location2)
            location2 = self.get_location_meters(self.home_location, *coords)

        # If the locations are now both `LocationGlobalRelative` objects, then 
        # return them.
        if type(location1) is type(location2):
            return location1, location2

        # One of the locations must now be a `LocationGlobal` object, while the 
        # other is a `LocationGlobalRelative` object. Convert the second 
        # location to conform to the first one.
        alt = self.home_location.alt
        if isinstance(location2, LocationGlobal):
            location2 = LocationGlobalRelative(location2.lat, location2.lon,
                                               location2.alt - alt)
        elif isinstance(location2, LocationGlobalRelative):
            location2 = LocationGlobal(location2.lat, location2.lon,
                                       location2.alt + alt)

        return location1, location2

    def make_location(self, lat, lon, alt=0.0):
        return LocationGlobalRelative(lat, lon, alt)

    def get_coordinates(self, location):
        if isinstance(location, LocationLocal):
            return super(Geometry_Spherical, self).get_coordinates(location)

        if isinstance(location, Locations):
            location = location.global_relative_frame
        elif not isinstance(location, (LocationGlobal, LocationGlobalRelative)):
            raise TypeError("`location` must be a Location object")

        return location.lat, location.lon, location.alt

    def get_location_local(self, location):
        if isinstance(location, LocationLocal):
            return location
        elif isinstance(location, Locations):
            return location.local_frame

        dlat, dlon, dalt = self.diff_location_meters(self.home_location, location)
        if isinstance(location, LocationGlobal):
            return LocationLocal(dlat, dlon, -dalt)
        elif isinstance(location, LocationGlobalRelative):
            return LocationLocal(dlat, dlon, -location.alt)

    def get_location_meters(self, original_location, north, east, alt=0):
        """
        Returns a Location object containing the latitude/longitude `north` and
        `east` (floating point) meters from the specified `original_location`,
        and optionally `alt` meters above the `original_location`. The returned
        location is the same type as `original_location`.

        The algorithm is relatively accurate over small distances, and has an
        error of at most 10 meters for displacements up to 1 kilometer, except
        when close to the poles.

        For more information see:
        http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
        """

        if isinstance(original_location, LocationLocal):
            return super(Geometry_Spherical, self).get_location_meters(original_location, north, east, alt)

        if isinstance(original_location, Locations):
            original_location = original_location.global_relative_frame

        # Coordinate offsets in radians
        lat = north / self.EARTH_RADIUS
        lon = east / (self.EARTH_RADIUS * math.cos(original_location.lat * math.pi/180))

        # New position in decimal degrees
        newlat = original_location.lat + (lat * 180/math.pi)
        newlon = original_location.lon + (lon * 180/math.pi)
        newalt = original_location.alt + alt
        if isinstance(original_location, LocationGlobal):
            return LocationGlobal(newlat, newlon, newalt)

        return LocationGlobalRelative(newlat, newlon, newalt)

    def get_distance_meters(self, location1, location2):
        """
        Returns the ground distance in meters between two Location objects.

        This method is an approximation, and will not be accurate over large
        distances and close to the earth's poles.

        The algorithm comes from the ArduPilot test code:
        https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
        """

        location1, location2 = self.equalize(location1, location2)
        if isinstance(location1, LocationLocal):
            return super(Geometry_Spherical, self).get_distance_meters(location1, location2)

        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        d = math.sqrt((dlat*dlat) + (dlon*dlon)) * self.COORD_TO_METERS
        return math.sqrt((d*d) + (dalt*dalt))

    @property
    def norm(self):
        # Spherical geometry does not supply a norm directly, since spherical 
        # coordinates are more complex.
        return None

    def _diff_location(self, location1, location2):
        # Only call this method with equalized location types.
        if isinstance(location1, LocationLocal):
            return super(Geometry_Spherical, self)._diff_location(location1, location2)

        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        if isinstance(location1, LocationGlobal):
            return LocationGlobal(dlat, dlon, dalt)

        return LocationGlobalRelative(dlat, dlon, dalt)

    def diff_location_meters(self, location1, location2):
        location1, location2 = self.equalize(location1, location2)
        if isinstance(location1, LocationLocal):
            return super(Geometry_Spherical, self).diff_location_meters(location1, location2)

        diff = self._diff_location(location1, location2)
        dlat = diff.lat * self.EARTH_RADIUS * math.pi/180
        dlon = diff.lon * self.EARTH_RADIUS * math.cos(location1.lat * math.pi/180) * math.pi/180
        return dlat, dlon, diff.alt
