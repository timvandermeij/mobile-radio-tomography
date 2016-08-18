# Core imports
import copy

# Library imports
from dronekit import VehicleMode, LocationLocal, LocationGlobal, LocationGlobalRelative

# Package imports
from ..core.Threadable import Threadable
from ..geometry.Geometry_Spherical import Geometry_Spherical

class Vehicle(Threadable):
    """
    Vehicle interface specification.
    """

    @classmethod
    def create(cls, arguments, geometry, import_manager, thread_manager, usb_manager):
        """
        Create a `Vehicle` object from one of the subclass types.

        `arguments` is an `Arguments` object that Vehicle subclasses can use to
        deduce settings from. `geometry` is a Geometry object of the space that
        the vehicle operates in. `import_manager` is an `Import_Manager` for
        deducing the location of the vehicle module. The `thread_manager` allows
        any worker threads to be registered in the `Thread_Manager`. Finally,
        the `usb_manager` argument is an instance of `USB_Manager` where certain
        peripherals can be loaded, e.g. for communicating with an external motor
        controller attached via a TTL device.

        Returns an initialized object that is a subclass of `Vehicle`.
        """

        settings = arguments.get_settings("vehicle")
        vehicle_class_name = settings.get("vehicle_class")

        vehicle_class = import_manager.load_class(vehicle_class_name,
                                                  relative_module="vehicle")
        return vehicle_class(arguments, geometry, import_manager,
                             thread_manager, usb_manager)

    def __init__(self, arguments, geometry, import_manager, thread_manager, usb_manager):
        """
        Initialize the vehicle.
        """

        super(Vehicle, self).__init__("vehicle", thread_manager)

        self._geometry = geometry
        self._home_location = None
        self._mode = VehicleMode("PLACEHOLDER")
        self._armed = False
        self._servos = {}
        self._attribute_listeners = {}

    def setup(self):
        """
        Set up preliminary backend requirements for the vehicle.
        """

        pass

    @property
    def use_simulation(self):
        """
        Check whether we want to use a simulated environment for this vehicle.
        This can depend on settings or the Vehicle class itself.
        """

        raise NotImplementedError("Subclasses must implement `use_simulation` property")

    @property
    def home_location(self):
        """
        Retrieve the home location object.

        This property returns a fresh `Location` object. The location type can
        depend on the vehicle type and the vehicle's geometry.
        """

        raise NotImplementedError("Subclasses must implement `home_location` property")

    @home_location.setter
    def home_location(self, position):
        """
        Change the home location to another `Location` object.

        The location `position` need not be a `LocationGlobal` object, but exact
        handling of other types may depend on the vehicle type and the vehicle's
        geometry.

        An updated location also results in a notification to the attribute
        listeners with a fresh `Location` object.
        """

        self._home_location = copy.copy(position)
        self.notify_attribute_listeners('home_location', self._home_location)

    @property
    def mode(self):
        """
        Get the vehicle mode.

        The mode is returned as a `VehicleMode` object with a `name` property.
        """

        return self._mode

    @mode.setter
    def mode(self, value):
        """
        Set the vehicle mode.

        The mode must be a `VehicleMode` object.
        """

        self._mode = value

    @property
    def armed(self):
        """
        Check whether the vehicle is armed.

        An armed vehicle is ready to move around or is currently moving.
        """

        return self._armed

    @armed.setter
    def armed(self, value):
        """
        Arm or disarm the vehicle by setting a boolean `value` to its state.
        """

        self._armed = value

    def pause(self):
        """
        Stop the vehicle such that it attempts to remain in place.

        The vehicle should stop any actions fairly quickly upon a pause.
        Mission objectives such as moving to waypoints are frozen, i.e., they
        are not actively sought after. The vehicle may be unpaused by changing
        its vehicle mode to a new mode. The vehicle may automatically disarm
        itself during its paused state, but this should not endanger itself or
        make it impossible to continue later on.
        """

        raise NotImplementedError("Subclasses must implement `pause()`")

    def update_mission(self):
        """
        Propagate any updates to mission attributes, such as waypoints and
        home location, to backend vehicle control, internal properties and
        listeners.

        This method can also print any information about mission attributes.
        """

        pass

    def add_takeoff(self, altitude):
        """
        Add a command to take off to a certain `altitude` in the mission.

        If the Vehicle backend does not support takeoff commands, this method
        is a no-op and should return `False` to indicate no command was added
        to the list of waypoints.
        """

        return False

    def add_waypoint(self, location):
        """
        Add a waypoint to move to a specified `location` in the mission.

        The waypoints added are supposed to be followed in order of the calls
        to this method. The use of the waypoints depends of the vehicle mode.

        The `location` is a Location object.
        """

        raise NotImplementedError("Subclasses must implement `add_waypoint(location)`")

    def add_wait(self):
        """
        Add a command to wait after reaching a previous waypoint command.

        The vehicle waits indefinitely after reaching this location, unless
        the waypoint is manually adjusted using `set_next_waypoint`.
        """

        raise NotImplementedError("Subclasses must implement `add_wait()`")

    def clear_waypoints(self):
        """
        Clear any waypoints and other mission commands to the vehicle.
        """

        raise NotImplementedError("Subclasses must implement `clear_waypoints()`")

    def is_wait(self):
        """
        Check if the current waypoint is a wait command added via `add_wait`.

        If the `Vehicle` does not support waypoints, or if the given `waypoint`
        index number is incorrect, or the waypoint itself is invalid, e.g., it
        was retrieved from a non-wait command, then the method must return
        `False`.
        """
        
        raise NotImplementedError("Subclasses must implement `is_wait()`")

    def get_waypoint(self, waypoint=-1):
        """
        Retrieve a waypoint from the list of vehicle waypoint commands.

        The given `waypoint` is an index of the waypoint list.
        If `waypoint` is `-1`, then return the waypoint that the vehicle should
        reach "next" in the mission.

        If the `Vehicle` does not support waypoints, or if the given `waypoint`
        index number is incorrect, then this method must return `None`. If the
        waypoint itself is invalid, e.g., it was retrieved from a non-waypoint
        command, then the method may return `None` or some other value.
        """

        raise NotImplementedError("Subclasses must implement `get_waypoint(waypoint)`")

    def get_next_waypoint(self):
        """
        Get the current waypoint number.
        """

        raise NotImplementedError("Subclasses must implement `get_next_waypoint()`")

    def set_next_waypoint(self, waypoint=-1):
        """
        Set the current waypoint that we wish to reach.

        The given `waypoint` is an index of the waypoint list.
        If `waypoint` is `-1`, then set the waypoint index to the waypoint
        after the current waypoint.
        """

        raise NotImplementedError("Subclasses must implement `set_next_waypoint(waypoint)`")

    def count_waypoints(self):
        """
        Return the number of waypoints in the mission.
        """

        raise NotImplementedError("Subclasses must implement `count_waypoints()`")

    def check_arming(self):
        """
        Perform final setup checks and make the vehicle ready to move.

        This can wait for final backend instantiation, perform necessary checks
        and finally arm the motors and put the vehicle in a controlled state.
        """

        return True

    def simple_takeoff(self, altitude):
        """
        Take off to a certain relative altitude in meters.

        If the Vehicle backend does not support taking off, this method
        is a no-op and should return `False` to indicate that it is not taking
        off. Otherwise, return `True` so that the caller can check whether it
        reached the specified altitude.
        """

        return False

    def simple_goto(self, location):
        """
        Set the target `location` of the vehicle to the given `Location` object.
        """

        raise NotImplementedError("Subclasses must implement `simple_goto(location)`")

    def is_location_valid(self, location):
        """
        Check whether a given `location` is valid, i.e. it is populated with
        a somewhat correct location. The default implementation checks whether
        none of the fields is populated with `None`, which is what dronekit
        does when it has no location information yet.

        Returns a boolean indicating whether the `location` is useable.
        If an invalid location type is given, then a `TypeError` is raised.
        """

        if isinstance(location, LocationLocal):
            # Only need to check one field
            return location.north is not None
        if isinstance(location, LocationGlobalRelative) or isinstance(location, LocationGlobal):
            # Check for a coordinate field and altitude field as per dronekit.
            return location.lat is not None and location.alt is not None

        raise TypeError("Invalid type for location object")

    def is_current_location_valid(self):
        """
        Check whether the current vehicle location is valid.
        """

        return self.is_location_valid(self.location)

    @property
    def location(self):
        """
        Retrieve the current location of the vehicle.

        This property returns the location as a `Locations` object with any
        number of valid frames, or one of the `LocationLocal`,
        `LocationGlobalRelative` or `LocationGlobal` objects.
        """

        raise NotImplementedError("Subclasses must implement `location` property")

    @property
    def speed(self):
        """
        Get the speed of the vehicle in m/s relative to its current attitude.

        If the speed cannot be retrieved, raise a `NotImplementedError`.
        """

        raise NotImplementedError("Subclass does not implement `speed` property")

    @speed.setter
    def speed(self, value):
        """
        Set the speed of the vehicle in m/s relative to its current attitude.

        If the speed cannot be set or if the current vehicle mode does not
        support setting the speed in this way, ignore the value.
        """

        pass

    @property
    def velocity(self):
        """
        Get the velocity in m/s spread out over components of the current frame.

        The frame will almost always be north, east and down (NED).
        If the velocity cannot be retrieved, raise a `NotImplementedError`.
        """

        raise NotImplementedError("Subclass does not implement `velocity` property")

    @velocity.setter
    def velocity(self, value):
        """
        Set the velocity in m/s spread out over components of the current frame.

        If the velocity cannot be set or if the current vehicle mode does not
        velocity setting the speed in this way, ignore the value.
        """

        pass

    @property
    def attitude(self):
        """
        Get the current attitude information of the vehicle.

        This property is an Attitude object with `pitch`, `yaw` and `roll`
        property fields which are bearings in radians.
        If the attitude cannot be retrieved, raise a `NotImplementedError`.
        """

        raise NotImplementedError("Subclass does not implement `attitude` property")

    def set_yaw(self, heading, relative=False, direction=1):
        """
        Set the bearing `heading` of the vehicle in degrees.
        This becomes the yaw of the vehicle, the direction in which it is facing
        relative to the surface plane.
        The `heading` is a bearing, meaning that north is zero degrees/radians,
        and the bearings increase counterclockwise.

        If `relative` is false, `heading` is the number of degrees off from
        northward direction, counterclockwise.
        If `relative` is true, the `heading` is still given as a bearing,
        but respective to the vehicle's current yaw.
        The `direction` gives the direction in which we should rotate:
        `1` means clockwise and `-1` is counterclockwise. Other values may be
        supported by certain vehicles, and `-1` may be unsupported in certain
        modes, such as absolute headings.

        If the yaw cannot be changed, ignore the value.
        """

        pass

    def set_servo(self, servo, pwm):
        """
        Set the PWM value of a given `servo` to the given `pwm`.

        The `servo` is a `Servo` object with the correct pin number.
        The `pwm` must be within the Servo's PWM dety range.

        If the vehicle does not support servos, raise a `NotImplementedError`.
        """

        raise NotImplementedError("Subclass does not implement `set_servo(servo, pwm)`")

    def add_attribute_listener(self, attribute, listener):
        """
        Add a listener for when a certain vehicle attribute changes.
        """

        if attribute not in self._attribute_listeners:
            self._attribute_listeners[attribute] = []
        if listener not in self._attribute_listeners:
            self._attribute_listeners[attribute].append(listener)

    def remove_attribute_listener(self, attribute, listener):
        """
        Remove a listener for a certain vehicle attribute.

        Raises a `KeyError` if the attribute has no listeners.
        Raises `ValueError` if the specific `listener` is registered.
        """

        listeners = self._attribute_listeners.get(attribute)
        if listeners is None:
            raise KeyError("Attribute '{}' has no listeners".format(attribute))

        listeners.remove(listener)
        if len(listeners) == 0:
            del self._attribute_listeners[attribute]

    def notify_attribute_listeners(self, attribute, value):
        """
        Notify all listeners for a specific attribute.
        """

        for fn in self._attribute_listeners.get(attribute, []):
            fn(self, attribute, value)

    def _set_servos(self, servo_pwms):
        """
        Set updated PWM values of servos.

        Vehicle subclasses must call this method with a dictionary with servo
        pin numbers and current PWM values whenever they update servos that are
        relevant to the listeners. For example, an update of motor servos may
        be left out of updates in case the listeners have no need for them, but
        any servos used for distance sensors should be in the dictionary.
        """
        self._servos.update(servo_pwms)
        self.notify_attribute_listeners('servos', self._servos)

    def _make_global_location(self, value):
        """
        Convert a `Location` object to a global location.
        """

        if isinstance(value, LocationGlobal):
            value = LocationGlobal(value.lat, value.lon, value.alt)
        elif isinstance(value, LocationLocal):
            home_location = self._home_location
            if home_location is None:
                value = LocationGlobal(value.north, value.east, -value.down)
            elif isinstance(self._geometry, Geometry_Spherical):
                value = self._geometry.get_location_meters(home_location,
                                                           value.north,
                                                           value.east,
                                                           -value.down)
            else:
                value = LocationGlobal(home_location.lat + value.north,
                                       home_location.lon + value.east,
                                       home_location.alt - value.down)
        elif isinstance(value, LocationGlobalRelative):
            home_location = self._home_location
            if home_location is not None:
                alt = home_location.alt
            else:
                alt = 0.0

            value = LocationGlobal(value.lat, value.lon, alt + value.alt)

        return value
