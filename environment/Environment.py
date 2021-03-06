# Core imports
import math

# Package imports
from Location_Proxy import Location_Proxy
from ..core.Import_Manager import Import_Manager
from ..core.Thread_Manager import Thread_Manager
from ..core.USB_Manager import USB_Manager
from ..trajectory.Servo import Servo
from ..vehicle.Vehicle import Vehicle
from ..zigbee.Settings_Receiver import Settings_Receiver

class Environment(Location_Proxy):
    """
    Environment class for interfacing the vehicle with various sensors and
    positioning information.
    """

    # The distance sensor class name, i.e., "Distance_Sensor_Physical" or 
    # "Distance_Sensor_Simulator", depending on Environment type.
    _sensor_class = None

    @classmethod
    def setup(cls, arguments, geometry_class=None, vehicle=None,
              thread_manager=None, usb_manager=None, simulated=None):
        """
        Create an Environment object or simulated environment.

        The returned object is an `Enviromnent` object or a subclass,
        loaded with the given `arguments` object.
        Optionally, one can specify which `geometry_class` to use and what
        `vehicle` object to use. By default, this depends on the settings for
        `"geometry_class"` and `"vehicle_class"` in the `environment` and
        `vehicle` components, respectively. If a `vehicle` is passed, then its
        `thread_manager` must be passed as well, otherwise a `ValueError` is
        raised. Note that passing a `vehicle` means that the `geometry_class`
        may differ from the vehicle's geometry.

        Finally, to use an environment with physical distance sensors,
        set `simulated` to `False`. This is required if the vehicle does not
        support simulation, which might depend on vehicle-specific settings and
        external configuration. For more control over simulated environment
        setup, use the normal constructors instead, with fewer guarantees.
        """

        if geometry_class is None:
            settings = arguments.get_settings("environment")
            geometry_class = settings.get("geometry_class")

        import_manager = Import_Manager()

        geometry_type = import_manager.load_class(geometry_class,
                                                  relative_module="geometry")
        geometry = geometry_type()

        if usb_manager is None:
            usb_manager = USB_Manager()
        
        usb_manager.index()
        if vehicle is None:
            thread_manager = Thread_Manager()
            vehicle = Vehicle.create(arguments, geometry, import_manager,
                                     thread_manager, usb_manager)
        elif thread_manager is None:
            raise ValueError("If a `vehicle` is provided then its `thread_manager` must be provided as well")

        vehicle.setup()

        if simulated is None:
            simulated = vehicle.use_simulation

        if simulated:
            if not vehicle.use_simulation:
                raise ValueError("Vehicle '{}' does not support environment simulation, check vehicle type and settings".format(vehicle.__class__.__name__))

            environment_class_name = "Environment_Simulator"
        else:
            environment_class_name = "Environment_Physical"

        environment = import_manager.load_class(environment_class_name,
                                                relative_module="environment")

        return environment(vehicle, geometry, arguments,
                           import_manager, thread_manager, usb_manager)

    def __init__(self, vehicle, geometry, arguments,
                 import_manager, thread_manager, usb_manager):
        super(Environment, self).__init__(geometry)

        self.vehicle = vehicle

        self.arguments = arguments
        self.settings = self.arguments.get_settings("environment")

        self.import_manager = import_manager
        self.thread_manager = thread_manager
        self.usb_manager = usb_manager

        # A lazily loaded list of distance sensors
        self._distance_sensors = None

        # Servo pins of the flight controller for distance sensor rotation
        self._servos = []
        for servo in self.settings.get("servo_pins"):
            pwm = servo["pwm"] if "pwm" in servo else None
            self._servos.append(Servo(servo["pin"], servo["angles"], pwm))

        # Set up the RF sensor and packet callback handler for distributing 
        # ZigBee packets to certain receivers according to the specification.
        self._rf_sensor = None
        self._packet_callbacks = {}
        self._setup_rf_sensor()

        self._settings_receiver = Settings_Receiver(self)

        # Set up the measurement validation that keeps track of the current 
        # location and wait waypoint IDs of the vehicles with sensors in the 
        # network, ensuring that we wait for enough measurements between the 
        # required sensors.
        self._valid_waypoints = {}
        self._valid_pairs = {}
        self._valid_locations = {}
        self._is_measurement_valid = False
        self._required_sensors = set()
        self._own_waypoint_valid = False
        self._own_waypoint_index = -1
        self._wait_waypoint_index = -1
        self.invalidate_measurement()

        # Set up the infrared sensor for direct control of missions, etc.
        if self.settings.get("infrared_sensor"):
            from ..control.Infrared_Sensor import Infrared_Sensor
            self._infrared_sensor = Infrared_Sensor(arguments, thread_manager)
        else:
            self._infrared_sensor = None

        # Set up vehicle attribute listeners to keep track of changes that 
        # affect the environment.
        self.vehicle.add_attribute_listener('home_location', self.on_home_location)
        self.vehicle.add_attribute_listener('servos', self.on_servos)

    def on_servos(self, vehicle, attribute, servo_pwms):
        for servo in self._servos:
            pin = servo.get_pin()
            if pin in servo_pwms:
                servo.set_current_pwm(servo_pwms[pin])

    def on_home_location(self, vehicle, attribute, home_location):
        self.geometry.set_home_location(home_location)

    def _setup_rf_sensor(self):
        rf_sensor_class = self.settings.get("rf_sensor_class")
        if rf_sensor_class == "":
            return

        rf_sensor_type = self.import_manager.load_class(rf_sensor_class,
                                                        relative_module="zigbee")
        self._rf_sensor = rf_sensor_type(self.arguments, self.thread_manager,
                                         self.get_raw_location, self.receive_packet,
                                         self.location_valid, usb_manager=self.usb_manager)

    def get_vehicle(self):
        return self.vehicle

    def get_arguments(self):
        return self.arguments

    def get_import_manager(self):
        return self.import_manager

    def get_thread_manager(self):
        return self.thread_manager

    def get_usb_manager(self):
        return self.usb_manager

    def get_distance_sensors(self):
        """
        Retrieve the list of `Distance_Sensor` objects.

        This method lazily initializes the distance sensors.
        """

        if self._distance_sensors is None:
            if self._sensor_class is None:
                raise NotImplementedError("Subclasses must provide a `_sensor_class` for the distance sensor")

            sensor = self.import_manager.load_class(self._sensor_class,
                                                    relative_module="distance")
            angles = list(self.settings.get("distance_sensors"))
            self._distance_sensors = [
                sensor(self, i, angles[i]) for i in range(len(angles))
            ]

        return self._distance_sensors

    def get_servos(self):
        """
        Return the list of `Servo` objects created by the Environment.

        If not empty, the first `Servo` elements of this list are reserved for
        rotating the same number of distance sensors, in the same order.
        """

        return self._servos

    def get_rf_sensor(self):
        """
        Return the `RF_Sensor` created by the Environment.

        This method returns `None` if the RF sensor class is not defined
        during the Environment setup.
        """

        return self._rf_sensor

    def get_infrared_sensor(self):
        """
        Return the `Infrared_Sensor` created by the Environment.

        This method returns `None` if the "infrared_sensor" setting is false
        during the Environment setup.
        """

        return self._infrared_sensor

    def add_packet_action(self, action, callback):
        """
        Register a `callback` for a given packet specification `action`.

        The `action` must not already have a callback registered for it.
        When a packet with the specification `action` is received, then the
        given `callback` is called.
        """

        if not hasattr(callback, "__call__"):
            raise TypeError("The provided callback is not callable.")

        if action in self._packet_callbacks:
            raise KeyError("Action '{}' already has a registered callback.".format(action))

        self._packet_callbacks[action] = callback

    def receive_packet(self, packet):
        """
        Callback method for the receive callback of the `RF_Sensor`.

        The given `packet` is a `Packet` object that may have a specification
        registered in `add_packet_action`.
        """

        specification = packet.get("specification")
        if specification in self._packet_callbacks:
            callback = self._packet_callbacks[specification]
            callback(packet)

    def get_objects(self):
        """
        Retrieve a list of simulated objects.

        Only used for `Environment_Simulator`.
        """

        return []

    @property
    def location(self):
        return self.vehicle.location

    def get_raw_location(self):
        """
        Callback method for the location callback of the `RF_Sensor`.

        The returned values are a tuple of coordinate values for the current
        location of the vehicle (excluding the altitude component), and the
        current waypoint index.
        """

        coords = self.geometry.get_coordinates(self.vehicle.location)[:2]
        return coords, self._own_waypoint_index

    def location_valid(self, request):
        """
        Callback method for the valid callback of the `RF_Sensor`.

        The `request` contains information about the packet that is to be sent
        and the other vehicle involved in this measurement.

        This is used to determine whether the measurement is valid on both ends
        of a synchronized pair of vehicles, and whether the mission can move to
        another waypoint already.

        The returned value is a tuple, where the first value indicates whether
        the vehicle's location is valid, namely whether it has reached the
        necessary waypoint index and that the location is stable according to
        the vehicle. The second value indicates whether the vehicle has received
        a measurement that is valid for both vehicles involved.
        """

        own_index = self._own_waypoint_index
        own_valid = self._own_waypoint_valid
        if not self.vehicle.is_current_location_valid():
            own_valid = False

        if request.is_broadcast:
            self._check_broadcast_validity(own_index, own_valid, request)
        else:
            self._check_ground_station_validity(own_index, own_valid, request)

        return own_valid, own_valid and self._valid_locations[request.other_id]

    def _check_broadcast_validity(self, own_index, own_valid, request):
        # We are going to send an RSSI broadcast packet, so we update whether 
        # the current vehicle's location is valid.
        if self._rf_sensor is not None and own_valid:
            self._valid_waypoints[self._rf_sensor.id] = own_index
            self._valid_locations[self._rf_sensor.id] = True
            self._valid_pairs[self._rf_sensor.id] = True

        if self._is_valid(self._rf_sensor.id, own_index):
            self._is_measurement_valid = all(
                self._is_valid(id, self._wait_waypoint_index)
                for id in self._required_sensors
            )
        else:
            self._is_measurement_valid = False

    def _check_ground_station_validity(self, own_index, own_valid, request):
        # We are going to send a ground station packet. This packet can only be 
        # complete if we have had measurements from all required sensors, but 
        # we also want to ensure we have sent enough valid measurements to the 
        # other vehicles as well. Only then can we consider the entire 
        # measurement to be valid.
        if request.other_valid:
            self._valid_waypoints[request.other_id] = request.other_index
            if request.other_index >= self._wait_waypoint_index and own_valid:
                self._valid_locations[request.other_id] = request.other_valid
            else:
                self._valid_locations[request.other_id] = False

            if request.other_valid_pair:
                self._valid_pairs[request.other_id] = request.other_valid_pair

    def _is_valid(self, rf_sensor_id, index):
        if rf_sensor_id not in self._valid_waypoints:
            return False

        if self._valid_waypoints[rf_sensor_id] < index:
            return False
        if self._valid_waypoints[rf_sensor_id] > index:
            return True

        return self._valid_pairs[rf_sensor_id]

    def is_measurement_valid(self):
        """
        Check whether the measurement at the current location was valid.

        Only returns `True` if both the current vehicle's location and the
        other RF sensor's sent location were valid.
        """

        return self._is_measurement_valid

    def set_waypoint_valid(self, valid=True):
        """
        Change the validity of the wait waypoint for the current vehicle.

        This enables
        """

        self._own_waypoint_valid = valid

    def invalidate_measurement(self, required_sensors=None, own_waypoint=-1,
                               wait_waypoint=-1):
        """
        Consider the current measurement to be invalid.

        The measurement will only be valid again the locations and waypoints of
        the current vehicle as well as each vehicle given in by their sensor ID
        in `required_sensors` become valid. If `required_sensors` is not given,
        then it falls back to the list of other vehicle sensors in the network.
        Regardless of the list of required sensors, the location and waypoint of
        the current vehicle must always be valid for a measurement to be
        complete. `own_waypoint` specifies the waypoint ID that this vehicle
        is attempting to reach, which is communicated to the other vehicles.
        `wait_waypoint` is the waypoint ID that we expect the other vehicles
        from `required_sensors` to reach.
        """

        self._valid_waypoints = {}
        self._valid_pairs = {}
        self._valid_locations = {}
        self._is_measurement_valid = False
        self._own_waypoint_valid = False
        self._own_waypoint_index = own_waypoint
        self._wait_waypoint_index = wait_waypoint

        if self._rf_sensor is None:
            self._required_sensors = set()
            return

        all_sensors = range(1, self._rf_sensor.number_of_sensors + 1)
        if required_sensors is None:
            required_sensors = all_sensors

        self._required_sensors = set(required_sensors)
        self._required_sensors.discard(self._rf_sensor.id)

        for rf_sensor_id in all_sensors:
            self._valid_pairs[rf_sensor_id] = False
            self._valid_locations[rf_sensor_id] = False

        self._valid_pairs[self._rf_sensor.id] = True

    def get_yaw(self):
        """
        Get the yaw bearing of the vehicle.
        """

        return self.vehicle.attitude.yaw

    def get_sensor_yaw(self, id=0):
        """
        Get the relative yaw of the given sensor.

        In case servos are used, this calculates the current angle of the servo
        corresponding to the given `id` index.

        This method is meant to be used by `Distance_Sensor` objects only,
        and does not include the fixed (starting) angle of the sensor itself.
        The angle may not be within a constrained range.
        """

        yaw = self.get_yaw()
        if id < len(self._servos):
            yaw = yaw + self._servos[id].get_value() * math.pi/180

        return yaw

    def get_angle(self):
        """
        Helper function to get the yaw angle to the vehicle.

        This performs conversion from bearing to angle, but still returns
        the angle in radians.
        """

        return self.geometry.bearing_to_angle(self.get_yaw())

    def get_pitch(self):
        """
        Get the pitch bearing of the vehicle.
        """

        return self.vehicle.attitude.pitch
