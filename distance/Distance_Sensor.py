import math

class Distance_Sensor(object):
    def __init__(self, environment, angle=0):
        self.environment = environment
        self.geometry = self.environment.get_geometry()
        self.angle = angle

    def get_distance(self):
        raise NotImplementedError("Subclasses must override get_distance()")

    def get_angle(self, bearing=None):
        """
        Convert a bearing angle given in `bearing` to an angle that the distance sensor uses.

        The angle is returned in radians.
        """

        if bearing is None:
            bearing = self.environment.get_yaw()

        # Offset for the yaw being increasing clockwise and starting at 
        # 0 degrees when facing north rather than facing east.
        angle = self.geometry.bearing_to_angle(bearing)

        # Add the fixed angle of the sensor itself.
        # Ensure angle is always in the range [0, 2pi).
        return (angle + self.angle*math.pi/180) % (2*math.pi)

    def get_pitch(self, bearing=None):
        if bearing is None:
            bearing = self.environment.get_pitch()

        # TODO: "Rotate" based on fixed sensor angle. Do we need a range?
        return 2*math.pi-bearing
