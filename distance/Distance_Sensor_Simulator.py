import sys
import math
import numpy as np
from droneapi.lib import Location
from Distance_Sensor import Distance_Sensor

class Distance_Sensor_Simulator(Distance_Sensor):
    """
    Virtual sensor class that detects collision distances to simulated objects
    """

    def __init__(self, environment, angle=0):
        super(Distance_Sensor_Simulator, self).__init__(environment, angle)
        arguments = self.environment.get_arguments()
        self.settings = arguments.get_settings("distance_sensor_simulator")
        # Margin in meters at which an object is still visible
        self.altitude_margin = self.settings.get("altitude_margin")
        # Margin (given in degrees, converted to radians) at which an object is 
        # still visible even though the angle is slightly different
        self.angle_margin = self.settings.get("angle_margin") * math.pi/180
        # Maximum distance in meters that the sensor returns
        self.maximum_distance = self.settings.get("maximum_distance")

        # Tracking the relevant edge that the sensor detected
        self.current_edge = None

        self.current_object = -1
        self.current_face = -1

    def get_edge_distance(self, edge, location, yaw_angle, pitch_angle):
        """
        Calculate the distance in meters to the `edge` from a given `location` with yaw and pitch angles given by `yaw_angle` and `pitch_angle`.
        The `edge` is a tuple of Location points defining a (sloped) edge.
        """

        # Based on ray casting calculations from 
        # http://archive.gamedev.net/archive/reference/articles/article872.html 
        # except that the coordinate system there is assumed to revolve around 
        # the vehicle, which is strange. Instead, use a fixed origin and thus 
        # the edge's b1 is fixed, and calculate b2 instead.

        m2 = math.tan(yaw_angle)
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

        # Distance on same altitude
        d = math.sqrt(abs(y - location.lat)**2 + abs(x - location.lon)**2)
        z = location.alt + math.tan(pitch_angle) * d

        loc_point = Location(y, x, z, location.is_relative)

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

        if loc_point.alt < 0 or alt < loc_point.alt - self.altitude_margin:
            return sys.float_info.max

        d = self.geometry.get_distance_meters(location, loc_point)

        return d

    def get_face_distance(self, face, location, yaw_angle, pitch_angle):
        """
        Get the direction distance to a plane `face` given as a polygon in a list of points from the `location` with yaw and pitch angles given by `yaw_angle` and `[itch_angle`.
        Returns the distance as well as the edge that was closest to the location, if there is any.
        """
        # Check if angle is within at least one quadrant of the angles to the 
        # object bounds, and also within the object bounds themselves. Both 
        # requirements have to be met, otherwise angles that are around the 
        # 0 degree mark can confuse the latter check.
        angles = []
        quadrants = []
        q2 = int(yaw_angle / (0.5*math.pi))
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

        if q2 in quadrants and min(angles) < yaw_angle < max(angles):
            dists = []
            edges = self.geometry.get_point_edges(face)
            for edge in edges:
                dists.append(self.get_edge_distance(edge, location, yaw_angle, pitch_angle))

            d_min = min(dists)
            e_min = dists.index(d_min)
            return (d_min, edges[e_min])

        return (sys.float_info.max, None)

    def get_plane_distance(self, face, location, yaw_angle, pitch_angle, verbose=False):
        # Another point on the line.
        p1 = self.geometry.get_location_angle(location, 1.0, yaw_angle, pitch_angle)
        return self.geometry.get_plane_distance(face, location, p1, verbose)

    def get_circle_distance(self, obj, location, yaw_angle):
        if obj['center'].alt >= location.alt - self.altitude_margin:
            # Find directional angle to the object's center.
            # The "object angle" should point "away" from the vehicle location, 
            # so that it matches up with the yaw if the vehicle is pointing 
            # toward the point.
            a2 = self.geometry.get_angle(location, obj['center'])
            if self.geometry.check_angle(a2, yaw_angle, self.angle_margin):
                d = self.geometry.get_distance_meters(location, obj['center'])
                return d - obj['radius']

        return sys.float_info.max

    def get_obj_distance(self, obj, location, yaw_angle, pitch_angle, verbose=False):
        if isinstance(obj, list):
            # List of faces.
            dists = []
            edges = []
            j = 0
            for face in obj:
                dist, edge = self.get_plane_distance(face, location, yaw_angle, pitch_angle, verbose and j == self.current_face)
                dists.append(dist)
                edges.append(edge)
                j = j + 1

            d_min = min(dists)
            e_min = dists.index(d_min)
            return (d_min, [e_min, edges[e_min]])
        elif isinstance(obj, tuple):
            # Single face with edges that are always perpendicular to our line 
            # of sight, from the ground up.
            if self.geometry.point_inside_polygon(location, obj, altitude_margin=self.altitude_margin):
                return (0, None)

            return self.get_face_distance(obj, location, yaw_angle, pitch_angle)
        elif 'center' in obj:
            # Cone object.
            dist = self.get_circle_distance(obj, location, yaw_angle)
            return (dist, obj['center'])

        return (self.maximum_distance, None)

    def get_distance(self, location=None, yaw=None, pitch=None):
        """
        Get the distance in meters to the collision object from the current `location` (a Location object).
        """

        self.current_edge = None

        if location is None:
            location = self.environment.get_location()
        if yaw is None:
            yaw = self.environment.get_yaw()
        if pitch is None:
            pitch = self.environment.get_pitch()

        yaw_angle = self.get_angle(yaw)
        pitch_angle = self.get_pitch(pitch)

        distance = self.maximum_distance
        i = 0
        for obj in self.environment.get_objects():
            dist, edge = self.get_obj_distance(obj, location, yaw_angle, pitch_angle, i == self.current_object)
            if dist < distance:
                distance = dist
                if isinstance(edge, list):
                    self.current_edge = [i] + edge
                else:
                    self.current_edge = edge

            i = i + 1

        return distance

    def get_current_edge(self):
        return self.current_edge

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
            elif isinstance(self.current_edge, list):
                e0 = memory_map.get_xy_index(self.current_edge[-1])
                e1 = e0
            else:
                e0 = memory_map.get_xy_index(self.current_edge)
                e1 = e0

            plt.annotate("D", e0, e1, arrowprops=options, horizontalalignment='center', verticalalignment='center')
