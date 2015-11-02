import math

from Servo import Servo
from VRMLLoader import VRMLLoader
from ..distance.Distance_Sensor_Simulator import Distance_Sensor_Simulator

class Environment(object):
    """
    Environment class for interfacing the vehicle with various sensors and positioning information.
    """

    _sensor_class = None

    def __init__(self, vehicle, geometry, arguments):
        self.vehicle = vehicle
        self.geometry = geometry
        self.arguments = arguments
        self.settings = self.arguments.get_settings("environment")
        self._distance_sensors = None

        # Servo pins of the flight controller for distance sensor rotation
        self._servos = []
        for servo in self.settings.get("servo_pins"):
            pwm = servo["pwm"] if "pwm" in servo else None
            self._servos.append(Servo(servo["pin"], servo["angles"], pwm))

    def get_vehicle(self):
        return self.vehicle

    def get_geometry(self):
        return self.geometry

    def get_arguments(self):
        return self.arguments

    def get_distance_sensors(self):
        if self._distance_sensors is None:
            if self._sensor_class is None:
                self._distance_sensors = []
            else:
                angles = list(self.settings.get("sensors"))
                self._distance_sensors = [
                    self._sensor_class(self, i, angles[i]) for i in range(len(angles))
                ]

        return self._distance_sensors

    def get_servos(self):
        return self._servos

    def get_objects(self):
        return []

    def get_location(self, north=0, east=0, alt=0):
        """
        Retrieve the location of the vehicle, or a point relative to the location of the vehicle given in meters.
        """

        if north == 0 and east == 0 and alt == 0:
            return self.vehicle.location

        return self.geometry.get_location_meters(self.vehicle.location, north, east, alt)

    def get_distance(self, location):
        """
        Get the distance to the `location` from the vehicle's location.
        """
        return self.geometry.get_distance_meters(self.vehicle.location, location)

    def get_yaw(self):
        """
        Get the yaw bearing of the vehicle.
        """
        return self.vehicle.attitude.yaw

    def get_angle(self):
        """
        Helper function to get the yaw angle to the vehicle.

        This performs conversion from bearing to angle, but still returns the angle in radians.
        """
        return self.geometry.bearing_to_angle(self.get_yaw())

    def get_sensor_yaw(self, id=0):
        """
        Get the relative yaw of the given sensor.

        In case servos are used, this calculates the current servo angle.

        This method is meant to be used by `Distance_Sensor` objects only, and does not include the fixed (starting) angle of the sensor itself. The angle may not be within a constrained range.
        """
        yaw = self.get_yaw()
        if id < len(self._servos):
            yaw = yaw + self._servos[id].get_angle() * math.pi/180

        return yaw

    def get_pitch(self):
        """
        Get the pitch bearing of the vehicle.
        """
        return self.vehicle.attitude.pitch

class Environment_Simulator(Environment):
    """
    Simulated environment including objects around the vehicle and potentially the vehicle itself.
    This allows us to simulate a mission without many dependencies on ArduPilot.
    """

    _sensor_class = Distance_Sensor_Simulator

    def __init__(self, vehicle, geometry, arguments):
        super(Environment_Simulator, self).__init__(vehicle, geometry, arguments)
        scenefile = self.settings.get("scenefile")
        translation = self.settings.get("translation")
        if scenefile is not None:
            loader = VRMLLoader(self, scenefile, translation)
            self.objects = loader.get_objects()
            return

        # Use hardcoded objects for testing
        l1 = self.get_location(100, 0, 10)
        l2 = self.get_location(0, 100, 10)
        l3 = self.get_location(-100, 0, 10)
        l4 = self.get_location(0, -100, 10)

        # Simplify function call
        get_location_meters = self.geometry.get_location_meters
        self.objects = [
            {
                'center': get_location_meters(self.vehicle.location, 40, -10),
                'radius': 2.5,
            },
            (get_location_meters(l1, 40, -40), get_location_meters(l1, 40, 40),
             get_location_meters(l1, -40, 40), get_location_meters(l1, -40, -40)
            ),
            (get_location_meters(l2, 40, -40), get_location_meters(l2, 40, 40),
             get_location_meters(l2, -40, 40), get_location_meters(l2, -40, -40)
            ),
            (get_location_meters(l3, 40, -40), get_location_meters(l3, 40, 40),
             get_location_meters(l3, -40, 40), get_location_meters(l3, -40, -40)
            ),
            (get_location_meters(l4, 40, -40), get_location_meters(l4, 40, 40),
             get_location_meters(l4, -40, 40), get_location_meters(l4, -40, -40)
            )
        ]

    def get_objects(self):
        return self.objects
