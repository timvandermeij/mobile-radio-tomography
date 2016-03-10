import sys
import math
from Distance_Sensor import Distance_Sensor

class Distance_Sensor_Simulator(Distance_Sensor):
    """
    Virtual sensor class that detects collision distances to simulated objects
    """

    def __init__(self, environment, id, angle=0):
        super(Distance_Sensor_Simulator, self).__init__(environment, id, angle)
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
                dists.append(self.geometry.get_edge_distance(edge, location, yaw_angle, pitch_angle, altitude_margin=self.altitude_margin))

            d_min = min(dists)
            e_min = dists.index(d_min)
            return (d_min, edges[e_min])

        return (sys.float_info.max, None)

    def get_plane_distance(self, face, location, yaw_angle, pitch_angle, verbose=False):
        # Another point on the line.
        p1 = self.geometry.get_location_angle(location, 1.0, yaw_angle, pitch_angle)
        return self.geometry.get_plane_distance(face, location, p1, verbose)

    def get_circle_distance(self, obj, location, yaw_angle):
        center = self.geometry.get_location_local(obj['center'])
        location = self.geometry.get_location_local(location)
        if location.down > center.down - self.altitude_margin:
            # Find directional angle to the object's center.
            # The "object angle" should point "away" from the vehicle location, 
            # so that it matches up with the yaw if the vehicle is pointing 
            # toward the point.
            a2 = self.geometry.get_angle(location, center)
            if self.geometry.check_angle(a2, yaw_angle, self.angle_margin):
                d = self.geometry.get_distance_meters(location, center)
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
        Get the distance in meters to the collision object from the current `location`.
        """

        self.current_edge = None

        if location is None:
            location = self.environment.get_location()
        if yaw is None:
            yaw = self.environment.get_sensor_yaw(self.id)
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
