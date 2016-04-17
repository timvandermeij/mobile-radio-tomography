import sys
import math
import itertools
import numpy as np
from dronekit import Locations, LocationLocal, LocationGlobal, LocationGlobalRelative

__all__ = ["Geometry", "Geometry_Spherical"]

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
        self.home_location = LocationLocal(0.0, 0.0, 0.0)

    def set_home_location(self, home_location):
        """
        Change the home location of the geometry.

        This is useful for comparing local locations to a known point, and it
        may have different type and semantics in extending classes.
        """

        self.home_location = self.get_location_local(home_location)

    def equalize(self, location1, location2):
        """
        Ensure that two location objects are of the same class.

        The base class only accepts `LocationLocal` objects.
        Extending classes can support `LocationGlobal` and
        `LocationGlobalRelative` classes and use this method to ensure that two
        objects are comparable.

        Returns the converted location objects.
        """

        location1 = self.get_location_local(location1)
        location2 = self.get_location_local(location2)

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

    def get_location_local(self, location):
        """
        Convert a `location` object to a `LocationLocal` object.

        The base class does not accept any `location` that is not already local,
        but extending classes may apply conversions.
        Returns the converted location.
        """

        if isinstance(location, Locations):
            return location.local_frame
        if isinstance(location, LocationLocal):
            return location

        raise TypeError("Base geometry can handle only local coordinates")

    def get_location_meters(self, original_location, north, east, alt=0):
        """
        Get another location offset from a given `original_location`.

        Returns a Location object containing the latitude/longitude `north` and
        `east` (floating point) meters from the specified `original_location`,
        and optionally `alt` meters above the `original_location`.

        Returns a location object of the same type as the original location.
        """

        original_location = self.get_location_local(original_location)

        # New position in meters
        newnorth = original_location.north + north
        neweast = original_location.east + east
        newdown = original_location.down - alt
        return LocationLocal(newnorth, neweast, newdown)

    def get_distance_meters(self, location1, location2):
        """
        Get the distance in meters between two location objects.

        The base class uses standard Euclidean distance. Extending classes may
        provide distance measurements with other norms and metrics.
        """

        location1, location2 = self.equalize(location1, location2)
        diff = self._diff_location(location1, location2)
        return math.sqrt((diff.north**2) + (diff.east**2) + (diff.down**2))

    def _diff_location(self, location1, location2):
        dnorth = location2.north - location1.north
        deast = location2.east - location1.east
        ddown = location2.down - location1.down
        return LocationLocal(dnorth, deast, ddown)

    def diff_location_meters(self, location1, location2):
        """
        Get the distance in meters for each axis between two Location objects.
        """

        location1, location2 = self.equalize(location1, location2)
        diff = self._diff_location(location1, location2)
        return diff.north, diff.east, -diff.down

    def get_location_angle(self, location, distance, yaw, pitch=0):
        """
        Get a location object that is `distance` meters away from the given
        `location` when following a line with angles `yaw` and `pitch` from
        the `location`, both in radians.

        Does not take curvature of the Earth into account.
        """

        dlon = math.cos(yaw) * distance
        dist = math.sin(yaw) * distance # distance for latitude calculation

        dalt = math.sin(pitch) * distance
        dlat = math.cos(pitch) * dist
        return self.get_location_meters(location, dlat, dlon, dalt)

    def get_angle(self, location1, location2):
        """
        Get the 2D angle in radians for the segment between locations
        `location1` and `location2` compared to the cardinal north and east
        (latitude and longitude) directions.

        Does not take curvature of earth in account, and should thus be used
        only for close locations. Only gives the yaw angle, under the assumption
        that the two locations are at the same level, and thus should not be
        used for locations at different altitudes.
        """

        dnorth, deast, ddown = self.diff_location_meters(location1, location2)
        angle = math.atan2(dnorth, deast)

        return (angle + 2*math.pi) % (2*math.pi)

    def diff_angle(self, a1, a2):
        """
        Given two angles `a1` and `a2`, get the angle difference between the
        two angles, ignoring periodicity.

        The returned difference may have a sign. The sign is negative if the
        second angle is closest to the first angle when increasing from the
        first angle counterclockwise. The sign is positive if the second angle
        is clockwise closest to the first angle.

        The sign should therefore not be regarded as an indication of which
        angle is smaller than the other. Use `abs` to ensure the difference is
        non-negative so that it can be compared to difference thresholds, or
        make use of `check_angle` or `get_direction` for higher-level purposes.
        """

        # Based on http://stackoverflow.com/a/7869457 but for radial angles
        return (a1 - a2 + math.pi) % (2*math.pi) - math.pi

    def check_angle(self, a1, a2, diff=0.0):
        """
        Check whether two angles `a1` and `a2` are the same or differ at most by
        an angle `diff`, in radians. The difference `diff` must be nonnegative.

        The returned boolean is `True` when the difference between the angles
        is at most `diff`.
        """

        return abs(self.diff_angle(a1, a2)) <= diff

    def get_direction(self, a1, a2):
        """
        Given two angles `a1` and `a2`, get the direction in which the first
        angle `a1` should increase to reach the second angle `a2` the quickest.

        Returns `1` if clockwise rotation brings `a1` to `a2` in less than half
        a turn (180 degrees) or `-1` if counterclockwise rotation brings `a1`
        to `a2` in the same fashion. This function never returns `0`.
        """

        diff = self.diff_angle(a1, a2)
        return int(math.copysign(1, diff))

    def ray_intersects_segment(self, P, start, end, verbose=False):
        """
        Given a location point `P` and an edge of two endpoint location objects
        `start` and `end` of a line segment, returns boolean whether the ray
        starting from the point eastward intersects the edge.

        This algorithm only checks 2D coordinate values, so ensure these
        coordinates are filled with the correct values or project the locations
        to the first two coordinates.
        """

        # Based on http://rosettacode.org/wiki/Ray-casting_algorithm#Python but 
        # cleaned up logic and clarified somewhat
        P = self.get_location_local(P)
        start = self.get_location_local(start)
        end = self.get_location_local(end)
        if start.north > end.north:
            # Swap start and end of segment
            start,end = end,start
        if P.north == start.north or P.north == end.north:
            # Move point off of the line
            P = LocationLocal(P.north + self.EPSILON, P.east, P.down)

        if P.north < start.north or P.north > end.north:
            if verbose:
                print("north")
            return False
        if P.east > max(start.east, end.east):
            if verbose:
                print("east")
            return False
        if P.east < min(start.east, end.east):
            return True

        if abs(start.east - end.east) > self.EPSILON:
            ang_out = (end.north - start.north) / (end.east - start.east)
        else:
            ang_out = sys.float_info.max

        if abs(start.east - P.east) > self.EPSILON:
            ang_in = (P.north - start.north) / (P.east - start.east)
        else:
            ang_in = sys.float_info.max

        if ang_in < ang_out:
            if verbose:
                print("Angles: {}/{}".format(ang_in, ang_out))
            return False

        return True

    def get_point_edges(self, points):
        """
        From a given list of `points` in a polygon (sorted on edge positions),
        generate a list of edges.
        
        The returned list has tuples of two points of the line segment that are
        next to each other, as well as the last and the first points.

        The returned edges thus describe the edges of a polygon defined by the
        given `points`.
        """

        if not points:
            return []

        return zip(points, list(points[1:]) + [points[0]])

    def point_inside_polygon(self, location, points, alt=True, altitude_margin=0, verbose=False):
        """
        Detect objectively whether a `location` is inside an object polygon
        with points `points`. If `alt` is True, then the points are considered
        to be upper points of a three-dimensional object extending up to it.
        """

        # Ensure all points are local, which the base Geometry rather likes and 
        # speeds up the ray intersection conversions.
        points = map(self.get_location_local, points)
        location = self.get_location_local(location)

        # Simplification: if the point is above the mean altitude of all the 
        # points, then do not consider it to be inside the polygon. We could 
        # also perform interesting calculations here, but we won't have that 
        # many objects of differing altitude anyway.
        if alt:
            avg = float(sum([point.down for point in points]))/len(points)
            if location.down < avg - altitude_margin:
                if verbose:
                    print("Altitude too high: {} m".format(avg))
                return False

        edges = self.get_point_edges(points)
        inside = False
        for e in edges:
            if self.ray_intersects_segment(location, e[0], e[1], verbose=verbose):
                inside = not inside

        return inside

    def get_edge_distance(self, edge, location, yaw_angle, pitch_angle, altitude_margin=0.0):
        """
        Calculate the distance to a point on an `edge` that a ray from a given
        `location` with yaw and pitch radian angles given by `yaw_angle` and
        `pitch_angle` would intersect at.

        The `edge` is a tuple of location points defining a (sloped) edge.

        Returns the distance in meters to the intersection point. If no such
        location is found, then the maximum float number is returned.
        """

        start = self.get_location_local(edge[0])
        end = self.get_location_local(edge[1])
        location = self.get_location_local(location)

        # Based on ray casting calculations from 
        # http://archive.gamedev.net/archive/reference/articles/article872.html 
        # except that the coordinate system there is assumed to revolve around 
        # the vehicle, which is strange. Instead, use a fixed origin and thus 
        # the edge's b1 is fixed, and calculate b2 instead.

        m2 = math.tan(yaw_angle)
        b2 = location.north - m2 * location.east

        if end.east == start.east:
            # Prevent division by zero
            # This should usually become inf, but since m2 is calculated with 
            # math.tan as well we should use the maximal value that this 
            # function reaches.
            m1 = math.tan(math.pi/2)
            b1 = 0.0
            x = start.east
            y = m2 * x + b2
        else:
            m1 = (end.north - start.north) / (end.east - start.east)
            if end.north < start.north:
                b1 = end.north - m1 * end.east
            else:
                b1 = start.north - m1 * start.east

            if m2 == m1:
                x = float('inf')
            else:
                x = (b1 - b2) / (m2 - m1)
            y = m1 * x + b1

        # Distance on same altitude
        d = math.sqrt(abs(y - location.north)**2 + abs(x - location.east)**2)
        z = math.tan(pitch_angle) * d - location.down

        loc_point = LocationLocal(y, x, -z)

        edge_dist = self.get_distance_meters(edge[0], edge[1])
        dists = [self.get_distance_meters(edge[i], loc_point) for i in (0,1)]
        if max(dists) > edge_dist:
            # Point is not actually on the edge, but on the line extending from 
            # it. This edge case is possible even after skipping object 
            # detection based on quadrants and angles, since it may be on one 
            # edge but not the other. This point is actually not detected.
            return sys.float_info.max

        # Get altitude of the point by basing off edge slope
        down = end.down + ((start.down - end.down) / edge_dist) * dists[1]

        if loc_point.down > 0 or loc_point.down < down - altitude_margin:
            return sys.float_info.max

        d = self.get_distance_meters(location, loc_point)

        return d


    def get_plane_vector(self, points, verbose=False):
        """
        Calculate the plane equation from the given `points` that define a face
        on the plane.
        """

        # Based on http://stackoverflow.com/a/24540938 expect with less typos 
        # (see http://stackoverflow.com/a/25809052) and more numpy strength

        # Point on the plane
        p = self.get_location_local(points[0])
        # Vectors from point that define plane direction
        v1 = self.diff_location_meters(p, points[1])
        v2 = self.diff_location_meters(p, points[2])
        if verbose:
            print(str(p), v1, v2)

        # Plane equation values. This is the normal vector of the plane.
        # http://geomalgorithms.com/a04-_planes.html#Normal-Implicit-Equation
        cp = np.cross(v1, v2)
        d = -(cp[0] * p.north + cp[1] * p.east + cp[2] * -p.down)

        return cp, d

    def check_dot(self, dot):
        """
        Check whether a dot product `dot` is large enough to be noticeable.

        This is useful to check whether an intersection between vectors exists.
        """

        return abs(dot) > self.EPSILON

    def get_intersection(self, face, cp, location, u, dot):
        """
        Finish calculating the intersection point of a line `u` from a given
        `location` and a plane `face`.

        The plane has a vector `cp`, and the line has a dot product with the
        plane vector `dot`.

        The returned values are the `factor`, which is positive if and only if
        there is a positive ray intersection, and the intersection location
        object `loc_point`.
        """

        # http://geomalgorithms.com/a05-_intersect-1.html#Line-Plane-Intersection
        w = self.diff_location_meters(face[0], location)
        nw_dot = np.dot(cp, w)
        factor = -nw_dot / dot
        u = u * factor
        loc_point = self.get_location_meters(location, *u)
        return factor, loc_point

    def get_projected_location(self, p, ignore_index):
        """
        Given a location `p`, project it to the first two 2D coordinates by
        ignoring the coordinate `ignore_index`.

        For best results, `ignore_index` should be the least relevant coordinate
        for the purposes of the location in its 3D model. The returned location
        object may or may not have an altitude which is to be ignored.
        """

        p = self.get_location_local(p)
        if ignore_index == 0:
            return LocationLocal(p.east, -p.down, 0)
        elif ignore_index == 1:
            return LocationLocal(p.north, -p.down, 0)
        else:
            # No need to ignore altitude here since it's ignored by default
            return p

    def point_inside_plane(self, face, cp, location, verbose=False):
        """
        Check whether a given `location` is inside a 3D plane defined by the
        location point objects in a list `face`, and its associated place
        coordinated `cp`.

        Returns a boolean whether the given point is within the plane, at least
        after projection.
        """

        # Point inside 3D polygon check
        # http://geomalgorithms.com/a03-_inclusion.html#3D-Polygons
        # Ignore the "least relevant coordinate" by moving the relevant 
        # coordinates into lat and lon, since those are used by the 2D point 
        # inside polygon algorithm, and this creates the largest projection of 
        # the plane.
        ignore_index = np.argmax(np.absolute(cp))

        ignores = itertools.repeat(ignore_index, len(face))
        projected_face = map(self.get_projected_location, face, ignores)

        projected_loc = self.get_projected_location(location, ignore_index)
        if verbose:
            print([(p.north, p.east) for p in projected_face])
            print(projected_loc)

        return self.point_inside_polygon(projected_loc, projected_face,
                                         alt=False, verbose=verbose)

    def get_plane_intersection(self, face, location1, location2, verbose=False):
        """
        Check whether a 3D line segment between location objects `location1` and
        `location2` intersects with the 3D plane defined by the location point
        objects in a list `face`.

        Returns a tuple of a factor, the which is positive if and only if there
        is a positive ray intersection, and the intersection location object.
        """

        if len(face) < 3:
            if verbose:
                print("Face incomplete")

            # Face incomplete
            return (None, None)

        cp, d = self.get_plane_vector(face, verbose=verbose)

        # 3D intersection point
        # Based on http://stackoverflow.com/a/18543221

        # Equation of the line
        u = np.array(self.diff_location_meters(location1, location2))
        # Dot product between the line and the plane vector
        nu_dot = np.dot(cp, u)
        if not self.check_dot(nu_dot):
            if verbose:
                print("Dot product not good enough, no intersection: dot={}, u={}.".format(nu_dot, u))

            # Dot product not good enough, usually caused by line and plane not 
            # actually intersecting (line parallel to plane)
            return (None, None)

        # Calculate the intersection point
        factor, loc_point = self.get_intersection(face, cp, location1, u,
                                                  nu_dot)

        if not self.point_inside_plane(face, cp, loc_point, verbose=verbose):
            # The intersection point is not actually inside the polygon, but on 
            # the plane extending from it. Thus there is no intersection.
            if verbose:
                print("Point not actually inside polygon")
                print(loc_point)
                print(cp)
                print([str(f) for f in face])

            return (None, None)

        return (factor, loc_point)

    def get_plane_distance(self, face, location1, location2, verbose=False):
        """
        Get the distance from a location object `location1` to a 3D plane
        defined by the location point objects in a list `face`, at least when
        following the line segment to `location2`.

        The returned tuple contains the distance or the maximum float value
        if there is no intersection, and the intersection location object.
        """

        factor, loc_point = self.get_plane_intersection(face, location1,
                                                        location2, verbose)
        if factor is None:
            return (sys.float_info.max, None)
        elif factor <= 0:
            if verbose:
                print("Factor too small: {}".format(factor))

            # The factor is too small, which means that the intersection point 
            # is on the line extending in the other direction, which we need to 
            # ignore as well.
            return (sys.float_info.max, None)
        else:
            dist = self.get_distance_meters(location1, loc_point)
            return (dist, loc_point)

class Geometry_Spherical(Geometry):
    # Radius of "spherical" earth
    EARTH_RADIUS = 6378137.0

    COORD_TO_METERS = 1.113195e5

    def __init__(self):
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

        if type(location1) == type(location2):
            return location1, location2

        if isinstance(location1, LocationLocal):
            location1 = self.get_location_meters(self.home_location,
                location1.north, location1.east, -location1.down)
        elif isinstance(location2, LocationLocal):
            location2 = self.get_location_meters(self.home_location,
                location2.north, location2.east, -location2.down)

        if type(location1) == type(location2):
            return location1, location2

        if isinstance(location2, LocationGlobal):
            location2 = LocationGlobalRelative(
                location2.lat, location2.lon,
                location2.alt - self.home_location.alt)
        elif isinstance(location2, LocationGlobalRelative):
            location2 = LocationGlobal(
                location2.lat, location2.lon,
                location2.alt + self.home_location.alt)

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
        if isinstance(location1, LocationLocal):
            return super(Geometry_Spherical, self)._diff_location(location1, location2)

        dlat = location2.lat - location1.lat
        dlon = location2.lon - location1.lon
        dalt = location2.alt - location1.alt
        return location1.__class__(dlat, dlon, dalt)

    def diff_location_meters(self, location1, location2):
        location1, location2 = self.equalize(location1, location2)
        if isinstance(location1, LocationLocal):
            return super(Geometry_Spherical, self).diff_location_meters(location1, location2)

        diff = self._diff_location(location1, location2)
        dlat = diff.lat * self.EARTH_RADIUS * math.pi/180
        dlon = diff.lon * self.EARTH_RADIUS * math.cos(location1.lat * math.pi/180) * math.pi/180
        return dlat, dlon, diff.alt
