import copy
from dronekit import VehicleMode

class Vehicle(object):
    """
    Vehicle interface specification.
    """

    @classmethod
    def create(self, arguments):
        """
        Create a Vehicle object from one of the subclass types.

        `arguments` is an Arguments object that Vehicle subclasses can use to
        deduce settings from.
        """

        raise ValueError("Unable to find appropriate Vehicle object")

    def __init__(self, arguments):
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

        raise NotImplementedError

    @property
    def home_location(self):
        """
        Retrieve the home location object.

        This property returns a fresh `Location` object.
        Depending on the vehicle, the frame of the location may differ.
        """

        return None

    @home_location.setter
    def home_location(self, position):
        """
        Change the home location to another `Location` object.
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
        return self._armed

    @armed.setter
    def armed(self, value):
        self._armed = value

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
        is a no-op.
        """

        pass

    def add_waypoint(self, location):
        """
        Add a waypoint to move to a specified `location` in the mission.

        The waypoints added are supposed to be followed in order of the calls
        to this method. The use of the waypoints depends of the vehicle mode.

        The `location` is a Location object.
        """

        pass

    def clear_waypoints(self):
        """
        Clear any waypoints and other mission commands to the vehicle.
        """

        pass

    def get_waypoint(self, waypoint=-1):
        """
        Retrieve a waypoint from the list of vehicle waypoint commands.

        The given `waypoint` is an index of the waypoint list.
        If `waypoint` is `-1`, then return the waypoint that the vehicle should
        reach "next" in the mission.

        If the Vehicle does not support waypoints, or if the given `waypoint`
        index number is incorrect, or if the waypoint itself is invalid, this
        method can return `None`.
        """

        return None

    def get_next_waypoint(self):
        """
        Get the current waypoint number.
        """

        return 0

    def set_next_waypoint(self, waypoint=-1):
        """
        Set the current waypoint that we wish to reach.

        The given `waypoint` is an index of the waypoint list.
        If `waypoint` is `-1`, then set the waypoint index to the waypoint
        after the current waypoint.
        """

        pass

    def count_waypoints(self):
        """
        Return the number of waypoints in the mission.
        """

        return 0

    def arm_and_takeoff(self, altitude, speed):
        """
        Perform final setup checks and make the vehicle ready to move.

        This can wait for final backend instantiation, perform necessary checks
        and finally arm the motors and put the vehicle in a controlled state.

        If the vehicle can fly and has a certain operating altitude, this method
        should let the vehicle take off to that `altitude` at the given `speed`.
        Otherwise, the Vehicle object can ignore the parameters and end early.
        """

        self._armed = True

    def simple_goto(self, location):
        """
        Set the target `location` of the vehicle to the given `Location` object.
        """

        raise NotImplementedError

    @property
    def location(self):
        """
        Retrieve the current location of the vehicle.

        This property returns the location as a `Location` object.
        """

        raise NotImplementedError

    @property
    def speed(self):
        """
        Get the speed of the vehicle in m/s relative to its current attitude.

        If the speed cannot be retrieved, raise a `NotImplementedError`.
        """

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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
