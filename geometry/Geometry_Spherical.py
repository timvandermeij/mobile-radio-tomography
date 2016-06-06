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

    def get_locations_frame(self, location1, location2):
        """
        Retrieve the location frame from a `Locations` object `location1` that
        is of equal type as `location2`.
        """

        if isinstance(location2, LocationLocal):
            return location1.local_frame
        elif isinstance(location2, LocationGlobal):
            return location1.global_frame
        else:
            return location1.global_relative_frame

    def equalize(self, location1, location2):
        if isinstance(location1, Locations):
            location1 = self.get_locations_frame(location1, location2)
        if isinstance(location2, Locations):
            location2 = self.get_locations_frame(location2, location1)

        if type(location1) is type(location2):
            return location1, location2

        if isinstance(location1, LocationLocal):
            location1 = self.get_location_meters(self.home_location, location1.north,
                                                 location1.east, -location1.down)
        elif isinstance(location2, LocationLocal):
            location2 = self.get_location_meters(self.home_location, location2.north,
                                                 location2.east, -location2.down)

        if type(location1) is type(location2):
            return location1, location2

        alt = self.home_location.alt
        if isinstance(location2, LocationGlobal):
            location2 = LocationGlobalRelative(location2.lat, location2.lon,
                                               location2.alt - alt)
        elif isinstance(location2, LocationGlobalRelative):
            location2 = LocationGlobal(location2.lat, location2.lon,
                                       location2.alt + alt)

        return location1, location2

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
        return original_location.__class__(newlat, newlon, newalt)

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
