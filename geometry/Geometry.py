import sys
import math
from droneapi.lib import Location

class Geometry(object):
    """
    Geometry utility functions
    This is a class with functions that calculate distances, locations or 
    angles based on specific input.
    This can be based on 
    Note that some functions assume certain properties of the earth's surface, 
    such as it being spherical or being flat. Depending on these assumptions, 
    these functions may have different accuracies across distances.
    Note that (`y`,`x`) = (`lat`,`lon`) = (`N`,`E`).

    The base class does uses meters as the base unit for coordinates.
    Use `Geometry_Spherical` for geographic coordinates on a spherical earth.
    """

    def bearing_to_angle(self, bearing):
        """
        Convert a `bearing` to the usual angle representation, both in radians.
        Bearings increase clockwise rather than counterclockwise, and they 
        start at 0 degrees when facing north, much like a compass. In order to 
        calculate using normal geometric models, we can convert it to angles 
        easily.
        """
        return -(bearing - math.pi/2.0) % (math.pi*2.0)

    def angle_to_bearing(self, angle):
        """
        Convert an `angle` into the bearing notation, both in radians.
        """
        return -(angle - math.pi/2.0) % (math.pi*2.0)

    def _meters_to_coordinates(self, north, east):
        # Since we just put everything in meters, we do not do anything here
        return (north,east)

    def get_location_meters(self, original_location, north, east, alt=0):
        """
        Returns a Location object containing the latitude/longitude `north` and `east` (floating point) meters from the 
        specified `original_location`, and optionally `alt` meters above the `original_location`. The returned Location has the same and `is_relative` value as `original_location`.
        """

        # New position in meters
        newlat = original_location.lat + north
        newlon = original_location.lon + east
        newalt = original_location.alt + alt
        return Location(newlat, newlon, newalt, original_location.is_relative)

    def get_distance_meters(self, location1, location2):
        """
        Get the distance in meters between two Location objects.

        We use standard Euclidean distance.
        """
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        return math.sqrt((dlat*dlat) + (dlon*dlon))

    def get_angle(self, location1, location2):
        """
        Get the angle in radians for the segment between locations `location1` and `location2` compared to the cardinal directions.

        Does not take curvature of earth in account, and should thus be used only for close locations.
        """
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        angle = math.atan2(dlat, dlon)

        return (angle + 2*math.pi) % (2*math.pi)

    def diff_angle(self, a1, a2):
        # Based on http://stackoverflow.com/a/7869457 but for radial angles
        return (a1 - a2 + math.pi) % (2*math.pi) - math.pi

    def ray_intersects_segment(self, P, start, end):
        '''
        Given a location point `P` and an edge of two endpoints `start` and `end` of a line segment, returns boolean whether the ray starting from the point eastward intersects the edge.
        '''
        # Based on http://rosettacode.org/wiki/Ray-casting_algorithm#Python but 
        # cleaned up logic and clarified somewhat
        epsilon = 0.0001
        if start.lat > end.lat:
            # Swap start and end of segment
            start,end = end,start
        if P.lat == start.lat or P.lat == end.lat:
            # Move point off of the line
            P = Location(P.lat + epsilon, P.lon, P.alt, P.is_relative)

        if P.lat < start.lat or P.lat > end.lat or P.lon > max(start.lon, end.lon):
            return False
        if P.lon < min(start.lon, end.lon):
            return True

        if abs(start.lon - end.lon) > epsilon:
            ang_out = (end.lat - start.lat) / (end.lon - start.lon)
        else:
            ang_out = sys.float_info.max

        if abs(start.lon - P.lon) > epsilon:
            ang_in = (P.lat - start.lat) / (P.lon - start.lon)
        else:
            ang_in = sys.float_info.max

        return ang_in >= ang_out

    def get_point_edges(self, points):
        """
        From a given list of `points` in a polygon (sorted on edge positions), generate a list of edges, which are tuples of two points of the line segment.
        """
        return zip(points, list(points[1:]) + [points[0]])

class Geometry_Spherical(Geometry):
    def get_location_meters(self, original_location, north, east, alt=0):
        """
        Returns a Location object containing the latitude/longitude `north` and `east` (floating point) meters from the 
        specified `original_location`, and optionally `alt` meters above the `original_location`. The returned Location has the same and `is_relative` value as `original_location`.
        The function is useful when you want to move the vehicle around specifying locations relative to 
        the current vehicle position.
        The algorithm is relatively accurate over small distances (10m within 1km) except close to the poles.
        For more information see:
        http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
        """
        # Radius of "spherical" earth
        EARTH_RADIUS = 6378137.0

        # Coordinate offsets in radians
        lat = north / EARTH_RADIUS
        lon = east / (EARTH_RADIUS * math.cos(original_location.lat * math.pi/180))

        # New position in decimal degrees
        newlat = original_location.lat + (lat * 180/math.pi)
        newlon = original_location.lon + (lon * 180/math.pi)
        newalt = original_location.alt + alt
        return Location(newlat, newlon, newalt, original_location.is_relative)

    def get_distance_meters(self, location1, location2):
        """
        Returns the ground distance in meters between two Location objects.

        This method is an approximation, and will not be accurate over large distances and close to the 
        earth's poles. It comes from the ArduPilot test code: 
        https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
        """
        d = super(Geometry_Spherical, self).get_distance_meters(location1, location2)
        return d * 1.113195e5
