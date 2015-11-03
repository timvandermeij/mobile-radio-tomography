from ..geometry import Geometry
from ..trajectory.MockVehicle import MockVehicle
from ..zigbee.XBee_Sensor_Physical import XBee_Sensor_Physical
from ..zigbee.XBee_Sensor_Simulator import XBee_Sensor_Simulator

class Environment(object):
    """
    Environment class for interfacing the vehicle with various sensors and positioning information.
    """

    _sensor_class = None

    @classmethod
    def setup(self, arguments, geometry_class="Geometry", vehicle=None, simulated=True):
        """
        Create an Environment object or simulated environment.

        The returned object is an Enviromnent object or a subclass, loaded with the given `arguments` object. Optionally one can specify which `geometry_class` to use and what `vehicle` object to use. To use an environment with physical distance sensors, set `simulated` to `False`.
        By default, the `vehicle` is a `MockVehicle`.
        For more control over simulated environment setup, use the normal constructors instead.
        """
        geometry = Geometry.__dict__[geometry_class]()
        if vehicle is None:
            vehicle = MockVehicle(geometry)

        if simulated:
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
        self._xbee_sensor = None
        self._setup_xbee_sensor()

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
                    self._sensor_class(self, angle) for angle in angles
                ]

        return self._distance_sensors

    def get_xbee_sensor(self):
        return self._xbee_sensor

    def receive_packet(self, packet):
        print("> Custom packet received: {}".format(packet.serialize()))

    def get_objects(self):
        return []

    def get_location(self, north=0, east=0, alt=0):
        """
        Retrieve the location of the vehicle, or a point relative to the location of the vehicle given in meters.
        """

        if north == 0 and east == 0 and alt == 0:
            return self.vehicle.location

        return self.geometry.get_location_meters(self.vehicle.location, north, east, alt)

    def get_raw_location(self):
        location = self.get_location()
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
