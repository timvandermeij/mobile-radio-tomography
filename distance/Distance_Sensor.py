import math

class Distance_Sensor(object):
    def __init__(self, environment, id, angle=0):
        self.environment = environment
        self.geometry = self.environment.geometry
        self.id = id
        self.angle = angle

    def get_distance(self, **kwargs):
        raise NotImplementedError("Subclasses must override get_distance()")

    def get_angle(self, bearing=None):
        """
        Convert a bearing angle given in `bearing` to a mathematical angle that
        the distance sensor can use.

        The bearing is an angle that is zero degrees when facing north, and it
        increases clockwise rather than counterclockwise. The `bearing` must
        be given in radians. If `bearing` is not given, then the current yaw
        of the given distance sensor, depending on servo and environment setup,
        is used instead.

        The angle is returned in radians.
        """

        if bearing is None:
            bearing = self.environment.get_sensor_yaw(self.id)

        # Offset for the yaw being increasing clockwise and starting at 
        # 0 degrees when facing north rather than facing east.
        angle = self.geometry.bearing_to_angle(bearing)

        # Add the fixed angle of the sensor itself.
        # Ensure angle is always in the range [0, 2pi).
        return (angle + self.angle*math.pi/180) % (2*math.pi)

    def get_pitch(self, bearing=None):
        """
        Get the pitch of the distance sensor given the current pitch `bearing`
        of the vehicle.
        """

        if bearing is None:
            bearing = self.environment.get_pitch()

        return (2*math.pi - bearing) % (2*math.pi)
