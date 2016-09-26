from ..location.Line_Follower import Line_Follower_Direction
from Waypoint import Waypoint, Waypoint_Type

class Waypoint_Home(Waypoint):
    """
    A waypoint that changes the home location of the vehicle.
    """

    def __init__(self, vehicle_id, geometry, location, home_direction=0,
                 **kwargs):
        super(Waypoint_Home, self).__init__(vehicle_id, geometry, location)

        self._home_direction = Line_Follower_Direction(home_direction)

    @property
    def name(self):
        return Waypoint_Type.HOME

    @property
    def home_direction(self):
        return self._home_direction

    def get_points(self):
        # The home location is not a waypoint.
        return []

    def update_vehicle(self, vehicle):
        super(Waypoint_Home, self).update_vehicle(vehicle)

        # Update the home location and home direction yaw of the vehicle.
        vehicle.set_home_state(self._location, yaw=self._home_direction.yaw)
