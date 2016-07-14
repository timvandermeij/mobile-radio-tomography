from Waypoint import Waypoint, Waypoint_Type

class Waypoint_Home(Waypoint):
    """
    A waypoint that changes the home location of the vehicle.
    """

    @property
    def name(self):
        return Waypoint_Type.HOME

    def get_points(self):
        # The home location is not a waypoint.
        return []

    def update_vehicle(self, vehicle):
        super(Waypoint_Home, self).update_vehicle(vehicle)

        vehicle.home_location = self._location
