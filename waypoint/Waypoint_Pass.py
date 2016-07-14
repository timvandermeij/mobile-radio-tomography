from Waypoint import Waypoint, Waypoint_Type

class Waypoint_Pass(Waypoint):
    """
    A waypoint that passes through the given waypoint, with no inherent need to
    stop at that point unless this is necessary during the mission.
    """

    @property
    def name(self):
        return Waypoint_Type.PASS

    def get_points(self):
        return [self._location]
