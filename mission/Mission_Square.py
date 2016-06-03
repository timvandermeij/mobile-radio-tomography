from Mission_Auto import Mission_Auto

class Mission_Square(Mission_Auto):
    """
    A mission that uses the autopilot to move to four waypoints in a square.
    """

    def get_points(self):
        """
        Define the four waypoint locations of a square mission.

        The waypoints are positioned to form a square of side length `2 * size`
        around a given center location, which is the home location.

        This method returns the points relative to the current location at the
        same altitude.
        """

        points = []

        points.append(self.environment.get_location(self.size/2, -self.size/2))
        points.append(self.environment.get_location(self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, self.size/2))
        points.append(self.environment.get_location(-self.size/2, -self.size/2))
        points.append(points[0])

        return points

    def check_waypoint(self):
        if not super(Mission_Square, self).check_waypoint():
            return False

        next_waypoint = self.vehicle.get_next_waypoint()
        num_commands = self.vehicle.count_waypoints()
        if next_waypoint >= num_commands - 1:
            print("Exit 'standard' mission when heading for final waypoint ({})".format(num_commands))
            return False

        return True
