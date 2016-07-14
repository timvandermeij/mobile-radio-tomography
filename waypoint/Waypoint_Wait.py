from Waypoint import Waypoint, Waypoint_Type

class Waypoint_Wait(Waypoint):
    def __init__(self, vehicle_id, geometry, location, previous_location=None,
                 wait_id=0, wait_count=1, **kwargs):
        super(Waypoint_Wait, self).__init__(vehicle_id, geometry, location)

        if previous_location is None:
            self._previous_location = self._geometry.home_location
        else:
            self._previous_location = previous_location

        self._wait_id = wait_id
        self._wait_count = wait_count

    @property
    def name(self):
        return Waypoint_Type.WAIT

    def get_points(self):
        return self._geometry.get_location_range(self._previous_location,
                                                 self._location,
                                                 count=self._wait_count)

    def get_required_sensors(self):
        return [self._wait_id] if self._wait_id > 0 else None
