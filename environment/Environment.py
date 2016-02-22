import math
from ..geometry import Geometry
from ..trajectory.Servo import Servo
from ..vehicle.Vehicle import Vehicle
from ..zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

from dronekit import LocationLocal

class Environment(object):
    """
    Environment class for interfacing the vehicle with various sensors and positioning information.
    """

    _sensor_class = None

    @classmethod
    def setup(self, arguments, geometry_class=None, vehicle=None, simulated=None):
        """
        Create an Environment object or simulated environment.

        The returned object is an Enviromnent object or a subclass,
        loaded with the given `arguments` object.
        Optionally, one can specify which `geometry_class` to use and what
        `vehicle` object to use. By default this depends on the settings for
        `geometry_class` and `vehicle_class` in the `environment` and `vehicle`
        components, respectively.
        Finally, to use an environment with physical distance sensors,
        set `simulated` to `False`. This is required if the vehicle does not
        support simulation, which might depend on vehicle-specific settings.
        For more control over simulated environment setup,
        use the normal constructors instead, although those do not ensure that
        the vehicle has the same geometry.
        """

        if geometry_class is None:
            settings = arguments.get_settings("environment")
            geometry_class = settings.get("geometry_class")

        geometry = Geometry.__dict__[geometry_class]()
        if vehicle is None:
            vehicle = Vehicle.create(arguments, geometry)

        vehicle.setup()

        if simulated is None:
            simulated = vehicle.use_simulation

        if simulated:
            if not vehicle.use_simulation:
                raise ValueError("Vehicle '{}' does not support environment simulation, check vehicle type and settings".format(vehicle.__class__.__name__))

            from Environment_Simulator import Environment_Simulator
            return Environment_Simulator(vehicle, geometry, arguments)

        from Environment_Physical import Environment_Physical
        return Environment_Physical(vehicle, geometry, arguments)

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

        self._xbee_sensor = None
        self.packet_callbacks = {}
        self._setup_xbee_sensor()

        self.vehicle.add_attribute_listener('home_location', self.on_home_location)

    def on_home_location(self, vehicle, attribute, home_location):
        self.geometry.set_home_location(home_location)

    def _setup_xbee_sensor(self):
        xbee_type = self.settings.get("xbee_type")
        if xbee_type == "simulator":
            xbee_class = XBee_Sensor_Simulator
        elif xbee_type == "physical":
            xbee_class = XBee_Sensor_Physical
        else:
            return

        self._xbee_sensor = xbee_class(self.arguments, self.get_raw_location,
                                       self.receive_packet)

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
                angles = list(self.settings.get("distance_sensors"))
                self._distance_sensors = [
                    self._sensor_class(self, i, angles[i]) for i in range(len(angles))
                ]

        return self._distance_sensors

    def get_servos(self):
        return self._servos

    def get_xbee_sensor(self):
        return self._xbee_sensor

    def add_packet_action(self, action, callback):
        self.packet_callbacks[action] = callback

    def receive_packet(self, packet):
        specification = packet.get("specification")
        if specification in self.packet_callbacks:
            callback = self.packet_callbacks[specification]
            callback(packet)

    def get_objects(self):
        return []

    def get_location(self, north=0, east=0, alt=0):
        """
        Retrieve the location of the vehicle, or a point relative to the location of the vehicle given in meters.
        """

        return self.geometry.get_location_meters(self.vehicle.location, north, east, alt)

    def get_raw_location(self):
        location = self.get_location()
        if isinstance(location, LocationLocal):
            return (location.north, location.east)
        else:
            return (location.lat, location.lon)

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

    def get_angle(self):
        """
        Helper function to get the yaw angle to the vehicle.

        This performs conversion from bearing to angle, but still returns the angle in radians.
        """
        return self.geometry.bearing_to_angle(self.get_yaw())

    def get_pitch(self):
        """
        Get the pitch bearing of the vehicle.
        """
        return self.vehicle.attitude.pitch
