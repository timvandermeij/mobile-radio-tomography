from Mission_Auto import Mission_Auto

class Mission_Forward(Mission_Auto):
    """
    Simple mission that only goes one meter forward.
    """

    def get_points(self):
        points = []
        points.append(self.environment.get_location(1.0, 0))
        return points
