import sys
import itertools
import math
import numpy as np
from droneapi.lib import Location
from Distance_Sensor import Distance_Sensor
from ..settings import Settings

class Distance_Sensor_Simulator(Distance_Sensor):
    """
    Virtual sensor class that detects collision distances to simulated objects
    """

    def __init__(self, arguments, environment, angle=0):
        self.environment = environment
        self.geometry = self.environment.get_geometry()
        self.angle = angle
        self.settings = arguments.get_settings("distance_sensor_simulator")
        # Margin in meters at which an object is still visible
        self.altitude_margin = self.settings.get("altitude_margin")
        # Maximum distance in meters that the sensor returns
        self.maximum_distance = self.settings.get("maximum_distance")

        # Tracking the relevant edge that the sensor detected
        self.current_edge = None

    def point_inside_polygon(self, location, points):
        """
        Detect objectively whether the vehicle has flown into an object.
        """
        # Simplification: if the point is above the mean altitude of all the 
        # points, then do not consider it to be inside the polygon. We could 
        # also perform interesting calculations here, but we won't have that 
        # many objects of differing altitude anyway.
        avg_alt = float(sum([point.alt for point in points]))/len(points)
        if avg_alt < location.alt - self.altitude_margin:
            return False

        edges = self.geometry.get_point_edges(points)
        inside = False
        for e in edges:
            if self.geometry.ray_intersects_segment(location, e[0], e[1]):
                inside = not inside

        return inside

    def get_edge_distance(self, edge, location, angle):
        """
        Calculate the distance in meters to the `edge` from a given `location` and `angle`.
        The `edge` is a tuple of Location points defining a (sloped) edge.
        """

        # Based on ray casting calculations from 
        # http://archive.gamedev.net/archive/reference/articles/article872.html 
        # except that the coordinate system there is assumed to revolve around 
        # the vehicle, which is strange. Instead, use a fixed origin and thus 
        # the edge's b1 is fixed, and calculate b2 instead.

        m2 = math.tan(angle)
        b2 = location.lat - m2 * location.lon

        if edge[1].lon == edge[0].lon:
            # Prevent division by zero
            # This should usually become inf, but since m2 is calculated with 
            # math.tan as well we should use the maximal value that this 
            # function reaches.
            m1 = math.tan(math.pi/2)
            b1 = 0.0
            x = edge[0].lon
            y = m2 * x + b2
        else:
            m1 = (edge[1].lat - edge[0].lat) / (edge[1].lon - edge[0].lon)
            if edge[1].lat < edge[0].lat:
                b1 = edge[1].lat - m1 * edge[1].lon
            else:
                b1 = edge[0].lat - m1 * edge[0].lon

            if m2 == m1:
                x = float('inf')
            else:
                x = (b1 - b2) / (m2 - m1)
            y = m1 * x + b1

        loc_point = Location(y, x, location.alt, location.is_relative)

        edge_dist = self.geometry.get_distance_meters(edge[0], edge[1])
        dists = [self.geometry.get_distance_meters(edge[i], loc_point) for i in (0,1)]
        if max(dists) > edge_dist:
            # Point is not actually on the edge, but on the line extending from 
            # it. This edge case is possible even after skipping object 
            # detection based on quadrants and angles, since it may be on one 
            # edge but not the other. This point is actually not detected.
            return sys.float_info.max

        # Get altitude of the point by basing off edge slope
        alt = edge[1].alt + ((edge[0].alt - edge[1].alt) / edge_dist) * dists[1]

        if alt < location.alt - self.altitude_margin:
            return sys.float_info.max

        d = self.geometry.get_distance_meters(location, loc_point)

        return d

    def get_face_distance(self, face, location, angle):
        """
        Get the direction distance to a plane `face` given as a polygon in a list of points from the `location` with `angle`.
        Returns the distance as well as the edge that was closest to the location, if there is any.
        """
        # Check if angle is within at least one quadrant of the angles to the 
        # object bounds, and also within the object bounds themselves. Both 
        # requirements have to be met, otherwise angles that are around the 
        # 0 degree mark can confuse the latter check.
        angles = []
        quadrants = []
        q2 = int(angle / (0.5*math.pi))
        for point in face:
            ang = self.geometry.get_angle(location, point)

            # Try to put the angles "around" the object in case we are around 
            # 0 = 360 degrees.
            q1 = int(ang / (0.5*math.pi))
            if q1 == 0 and q2 == 3:
                ang = ang + 2*math.pi
            elif q1 == 3 and q2 == 0:
                ang = ang - 2*math.pi

            angles.append(ang)
            quadrants.append(q1)

        if q2 in quadrants and min(angles) < angle < max(angles):
            dists = []
            edges = self.geometry.get_point_edges(face)
            for edge in edges:
                dists.append(self.get_edge_distance(edge, location, angle))

            d_min = min(dists)
            e_min = dists.index(d_min)
            return (d_min, edges[e_min])

        return (sys.float_info.max, None)

    def get_projected_location(self, p, ignore_index):
        if ignore_index == 0:
            return Location(p.lon, p.alt, 0)
        elif ignore_index == 1:
            return Location(p.lat, p.alt, 0)
        else:
            # No need to ignore altitude here since it's ignored by default
            return p

    def get_plane_distance(self, face, location, angle):
        if len(face) < 3:
            print("Face incomplete")
            return (sys.float_info.max, None)

        epsilon = 0.0001
        # TODO: Split up/move parts to Geometry

        # Calculate plane equation from points on face
        # Based on http://stackoverflow.com/a/24540938 expect with less typos 
        # (see http://stackoverflow.com/a/25809052) and more numpy strength

        # Point on a plane
        p = face[0]
        # Vectors from point that define plane direction
        v1 = [face[1].lat - p.lat, face[1].lon - p.lon, face[1].alt - p.alt]
        v2 = [face[2].lat - p.lat, face[2].lon - p.lon, face[2].alt - p.alt]
        cp = np.cross(v1, v2)
        # Normalized plane coordinates
        d = -(cp[0] * p.lat + cp[1] * p.lon + cp[2] * p.alt) / np.dot(cp, cp)
        p_co = cp * d

        # 3D intersection point
        # Based on http://stackoverflow.com/a/18543221

        # Point at location
        p0 = np.array([location.lat, location.lon, location.alt])
        # Slope of the line
        m = math.tan(angle)
        # Another point on the line. Assume for now that the vehicle's pitch is 
        # zero, i.e. it looks straight ahead on the ground plane.
        p1 = np.array([p0[0] + 0.1, p0[1] + (p0[0] + 0.1) * m, p0[1]])
        u = p1 - p0
        dot = np.dot(p_co, u)
        if abs(dot) <= epsilon:
            print("Dot product not good enough: {}".format(dot))
            return (sys.float_info.max, None)

        w = p0 - p_co
        factor = -np.dot(p_co, w) / dot
        u = u * factor
        intersection = p0 + u

        # Point inside 3D polygon check
        # http://geomalgorithms.com/a03-_inclusion.html#3D-Polygons
        # Move the "least relevant coordinate" into the altitude value since 
        # that's ignored for 2D point inside polygon and this creates the 
        # largest projection of the plane.
        ignore_index = np.argmax(np.absolute(p_co))

        ignores = itertools.repeat(ignore_index, len(face))
        projected_face = map(self.get_projected_location, face, ignores)

        loc_point = Location(intersection[0], intersection[1], intersection[2])
        projected_loc = self.get_projected_location(loc_point, ignore_index)
        if self.point_inside_polygon(projected_loc, projected_face):
            d = self.geometry.get_distance_meters(location, loc_point)
            return (d, None)

        return (sys.float_info.max, None)

    def get_circle_distance(self, obj, location, angle):
        if obj['center'].alt >= location.alt - self.altitude_margin:
            # Find directional angle to the object's center.
            # The "object angle" should point "away" from the vehicle location, 
            # so that it matches up with the yaw if the vehicle is pointing 
            # toward the point.
            a2 = self.geometry.get_angle(location, obj['center'])
            diff = self.geometry.diff_angle(a2, angle)
            if abs(diff) < 5.0 * math.pi/180:
                d = self.geometry.get_distance_meters(location, obj['center'])
                return d - obj['radius']

        return sys.float_info.max

    def get_obj_distance(self, obj, location, angle):
        if isinstance(obj, list):
            # List of faces.
            dists = []
            for face in obj:
                dist, edge = self.get_plane_distance(face, location, angle)
                dists.append(dist)

            return (min(dists), None)
        elif isinstance(obj, tuple):
            # Single face with edges that are always perpendicular to our line 
            # of sight, from the ground up.
            if self.point_inside_polygon(location, obj):
                return (0, None)

            return self.get_face_distance(obj, location, angle)
        elif 'center' in obj:
            # Cone object.
            return (self.get_circle_distance(obj, location, angle), obj['center'])

        return (self.maximum_distance, None)

    def get_distance(self, location=None, angle=None):
        """
        Get the distance in meters to the collision object from the current `location` (a Location object).
        """

        self.current_edge = None
        if location is None:
            location = self.environment.get_location()
        angle = self.get_angle(angle)

        distance = self.maximum_distance
        for obj in self.environment.objects:
            dist, edge = self.get_obj_distance(obj, location, angle)
            if dist < distance:
                distance = dist
                self.current_edge = edge

        return distance

    def get_angle(self, angle=None):
        """
        Convert a bearing angle to an angle that the distance sensor uses.
        """
        if angle is None:
            # Offset for the yaw being increasing clockwise and starting at 
            # 0 degrees when facing north rather than facing east.
            angle = self.geometry.bearing_to_angle(self.environment.get_yaw())

        # Add the the fixed angle of the sensor itself.
        # Ensure angle is always in the range [0, 2pi).
        return (angle + self.angle*math.pi/180) % (2*math.pi)
    
    def draw_current_edge(self, plt, memory_map, color="red"):
        """
        Draw the edge that was detected during the previous distance sensor measurement, if any.
        The edge is drawn to the matplotlib plot object `plt` using the index offsets from the Memory_Map `map`. Additionally the `color` of the edge can be given.
        """
        if self.current_edge is not None:
            options = {
                "arrowstyle": "-",
                "color": color,
                "linewidth": 2,
                "alpha": 0.5
            }
            if isinstance(self.current_edge, tuple):
                e0 = memory_map.get_xy_index(self.current_edge[0])
                e1 = memory_map.get_xy_index(self.current_edge[1])
            else:
                e0 = memory_map.get_xy_index(self.current_edge)
                e1 = e0

            plt.annotate("", e0, e1, arrowprops=options)
