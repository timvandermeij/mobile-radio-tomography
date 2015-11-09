import sys
import math
import numpy as np
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

    # Epsilon value. This should be low enough to not detect different points 
    # as being the same, but high enough to work for both coordinates and 
    # meters.
    EPSILON = 0.0001

    def __init__(self):
        self.home_location = Location(0.0, 0.0, 0.0, is_relative=False)

    def set_home_location(self, home_location):
        if home_location.is_relative:
            raise ValueError("Home location cannot be a relative location")

        self.home_location = home_location

    def equalize(self, location1, location2):
        if location1.is_relative != location2.is_relative:
            if location1.is_relative:
                location1 = Location(location1.lat + self.home_location.lat,
                                     location1.lon + self.home_location.lon,
                                     location1.alt + self.home_location.alt,
                                     is_relative=False)
            if location2.is_relative:
                location2 = Location(location2.lat + self.home_location.lat,
                                     location2.lon + self.home_location.lon,
                                     location2.alt + self.home_location.alt,
                                     is_relative=False)

        return location1, location2

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
        location1, location2 = self.equalize(location1, location2)
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        return math.sqrt((dlat*dlat) + (dlon*dlon) + (dalt*dalt))

    def diff_location_meters(self, location1, location2):
        """
        Get the distance in meters for each axis between two Location objects.
        """
        location1, location2 = self.equalize(location1, location2)
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        return (dlat, dlon, dalt)

    def get_location_angle(self, location, distance, yaw, pitch=0):
        """
        Get a location that is `distance` meters away from the given `location` and has a rotations `yaw` and `pitch`, both in radians.
        """
        dlon = math.cos(yaw) * distance
        dist = math.sin(yaw) * distance # distance for latitude calculation

        dalt = math.sin(pitch) * distance
        dlat = math.cos(pitch) * dist
        return self.get_location_meters(location, dlat, dlon, dalt)

    def get_angle(self, location1, location2):
        """
        Get the 2D angle in radians for the segment between locations `location1` and `location2` compared to the cardinal latitude and longitude directions.

        Does not take curvature of earth in account, and should thus be used only for close locations. Only gives the yaw angle assuming the two locations are at the same level, and thus should not be used for locations at different altitudes.
        """
        location1, location2 = self.equalize(location1, location2)
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        angle = math.atan2(dlat, dlon)

        return (angle + 2*math.pi) % (2*math.pi)

    def diff_angle(self, a1, a2):
        """
        Given two angles `a1` and `a2`, get the angle difference between the two angles, ignoring periodicity.

        The returned difference may have a sign. The sign is negative if the second angle is closest to the first angle when increasing from the first angle counterclockwise. The sign is positive if the second angle is clockwise closest to the first angle.
        The sign should therefore not be regarded as an indication of which angle is smaller than the other. Use `abs` to ensure the difference is non-negative so that it can be compared to difference thresholds.
        """
        # Based on http://stackoverflow.com/a/7869457 but for radial angles
        return (a1 - a2 + math.pi) % (2*math.pi) - math.pi

    def check_angle(self, a1, a2, diff=0.0):
        """
        Check whether two angles `a1` and `a2` are the same or differ only by an angle `diff`, in radians. The difference `diff` must be nonnegative.
        """
        if abs(self.diff_angle(a1, a2)) <= diff:
            return True

        return False

    def get_direction(self, a1, a2):
        """
        Given two angles `a1` and `a2`, get the direction in which the first angle should increase to reach the second angle the quickest.

        Returns `1` if clockwise rotation brings `a1` to `a2` in less than 180 degrees or `-1` if counterclockwise rotation brings `a1` to `a2` in the same fashion. This function never returns `0`.
        """
        diff = self.diff_angle(a1, a2)
        return int(math.copysign(1, diff))

    def ray_intersects_segment(self, P, start, end):
        """
        Given a location point `P` and an edge of two endpoints `start` and `end` of a line segment, returns boolean whether the ray starting from the point eastward intersects the edge.

        This algorithm only checks 2D coordinate values.
        """
        # Based on http://rosettacode.org/wiki/Ray-casting_algorithm#Python but 
        # cleaned up logic and clarified somewhat
        P, start = self.equalize(P, start)
        if start.lat > end.lat:
            # Swap start and end of segment
            start,end = end,start
        if P.lat == start.lat or P.lat == end.lat:
            # Move point off of the line
            P = Location(P.lat + self.EPSILON, P.lon, P.alt, P.is_relative)

        if P.lat < start.lat or P.lat > end.lat or P.lon > max(start.lon, end.lon):
            return False
        if P.lon < min(start.lon, end.lon):
            return True

        if abs(start.lon - end.lon) > self.EPSILON:
            ang_out = (end.lat - start.lat) / (end.lon - start.lon)
        else:
            ang_out = sys.float_info.max

        if abs(start.lon - P.lon) > self.EPSILON:
            ang_in = (P.lat - start.lat) / (P.lon - start.lon)
        else:
            ang_in = sys.float_info.max

        return ang_in >= ang_out

    def get_point_edges(self, points):
        """
        From a given list of `points` in a polygon (sorted on edge positions), generate a list of edges, which are tuples of two points of the line segment.
        """
        if not points:
            return []

        return zip(points, list(points[1:]) + [points[0]])

    def get_plane_vector(self, points):
        """
        Calculate the plane equation from the given `points` that determine a face on the plane.
        """
        # Based on http://stackoverflow.com/a/24540938 expect with less typos 
        # (see http://stackoverflow.com/a/25809052) and more numpy strength

        # Point on the plane
        p = points[0]
        # Vectors from point that define plane direction
        v1 = self.diff_location_meters(p, points[1])
        v2 = self.diff_location_meters(p, points[2])

        # Plane equation values. This is the normal vector of the plane.
        # http://geomalgorithms.com/a04-_planes.html#Normal-Implicit-Equation
        cp = np.cross(v1, v2)
        d = -(cp[0] * p.lat + cp[1] * p.lon + cp[2] * p.alt)

        return cp, d

    def check_dot(self, dot):
        """
        Check whether a given dot product `dot` is large enough to be noticeable.
        This is useful to check whether an intersection between vectors exists.
        """
        return abs(dot) > self.EPSILON

    def get_intersection(self, face, cp, location, u, dot):
        """
        Finish calculating the intersection point of a line `u` from a given `location` and a plane `face`.
        The plane has a vector `cp`, and the line has a dot product with the plane vector `dot`.
        The returned values are the `factor`, is positive if and only if this is a positive ray intersection, and the intersection point `loc_point`.
        """
        # http://geomalgorithms.com/a05-_intersect-1.html#Line-Plane-Intersection
        w = self.diff_location_meters(face[0], location)
        nw_dot = np.dot(cp, w)
        factor = -nw_dot / dot
        u = u * factor
        loc_point = self.get_location_meters(location, *u)
        return factor, loc_point

class Geometry_Spherical(Geometry):
    # Radius of "spherical" earth
    EARTH_RADIUS = 6378137.0

    COORD_TO_METERS = 1.113195e5

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
        # Coordinate offsets in radians
        lat = north / self.EARTH_RADIUS
        lon = east / (self.EARTH_RADIUS * math.cos(original_location.lat * math.pi/180))

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
        location1, location2 = self.equalize(location1, location2)
        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        d = math.sqrt((dlat*dlat) + (dlon*dlon)) * self.COORD_TO_METERS
        return math.sqrt((d*d) + (dalt*dalt))

    def diff_location_meters(self, location1, location2):
        dlat, dlon, dalt = super(Geometry_Spherical, self).diff_location_meters(location1, location2)

        dlat = dlat * self.EARTH_RADIUS * math.pi/180
        dlon = dlon * self.EARTH_RADIUS * math.cos(location1.lat * math.pi/180) * math.pi/180
        return dlat, dlon, dalt
