from enum import IntEnum
from ..vehicle.Vehicle import Vehicle

class Waypoint_Type(IntEnum):
    HOME = 1
    PASS = 2
    WAIT = 3

class Waypoint(object):
    """
    An object that generates waypoints. This can be used when creating certain
    missions.
    """

    @classmethod
    def create(cls, import_manager, waypoint_type, vehicle_id, geometry,
               location, **kwargs):
        """
        Create a `Waypoint` object.

        The given `import_manager` should be an `Import_Manager` that allows us
        to import the waypoint classes. The `waypoint_type` is a value from the
        `Waypoint_Type` enum that specifies the type of the waypoint. The other
        arguments are passed on to the initialization of the `Waypoint`.
        """

        waypoint_class_name = "Waypoint_{}".format(waypoint_type.name.title())
        waypoint_class = import_manager.load_class(waypoint_class_name,
                                                   relative_module="waypoint")

        return waypoint_class(vehicle_id, geometry, location, **kwargs)

    def __init__(self, vehicle_id, geometry, location, **kwargs):
        """
        Create a waypoint object. The `vehicle_id` is an integer identifier for
        the vehicle who should run the mission in which the waypoints are added.

        The `location` is a Location object, as a reference for the waypoint.
        Most likely, the waypoint takes place here, but `Waypoint` subclasses
        may also do something else with it, e.g., create a range of waypoints,
        or it may ignore it. Additional arguments may be provided for certain
        `Waypoint` subclasses; other classes must ignore them.
        """

        self._vehicle_id = vehicle_id
        self._geometry = geometry
        self._location = location

    @property
    def name(self):
        """
        Retrieve the name of the waypoint object.

        This should be a `Waypoint_Type` enum value.
        """

        raise NotImplementedError("Subclasses must implement `name`")

    @property
    def vehicle_id(self):
        """
        Retrieve the vehicle identifier.
        """

        return self._vehicle_id

    @property
    def location(self):
        """
        Retrieve the waypoint location.
        """

        return self._location

    def get_points(self):
        """
        Retrieve the waypoints that can be registered in a vehicle.

        This is a list of various values. Supported values are dronekit's
        Location objects and `None`, which means we wait at the waypoint for
        an indetermined amount of time.
        """

        raise NotImplementedError("Subclasses must implement `get_points`")

    def get_required_sensors(self):
        """
        Retrieve the list of required sensors that we should wait for when we
        go to the requested waypoints. Returns `None` if the waypoint requires
        all sensors (at least when this is enabled), and raises a `RuntimeError`
        if waiting is not supported by this waypoint.
        """

        raise RuntimeError("Waypoint does not support waiting for required sensors")

    def update_vehicle(self, vehicle):
        """
        Update the state of the given `vehicle`, a `Vehicle` object.

        The waypoint need not add itself to the vehicle's waypoint commands;
        we assume that this has already done. If any additional state changes
        are necessary, then we can do them here.
        """

        if not isinstance(vehicle, Vehicle):
            raise TypeError("`vehicle` must be a `Vehicle` object")
