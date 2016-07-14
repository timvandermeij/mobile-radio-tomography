from enum import IntEnum

class Waypoint_Type(IntEnum):
    HOME = 1
    PASS = 2
    WAIT = 3

class Waypoint(object):
    """
    An object that generates waypoints. This can be used when creating certain
    missions.
    """

    def __init__(self, vehicle_id):
        """
        Create a waypoint object. The `vehicle_id` is an integer identifier for
        the vehicle who should run the mission in which the waypoints are added.
        """

        self._vehicle_id = vehicle_id

    @property
    def name(self):
        """
        Retrieve the name of the waypoint object.

        This should be a `Waypoint_Type` enum value.
        """

        raise NotImplementedError("Subclasses must implement `name`")

    @property
    def vehicle_id(self):
        return self._vehicle_id

    def get_points(self):
        """
        Retrieve the waypoints that can be registered in a vehicle.

        This is a list of various values. Supported values are dronekit's
        Location objects and `None`, which means we wait at the waypoint for
        an indetermined amount of time.
        """

        raise NotImplementedError("Subclasses must implement `get_points`")
