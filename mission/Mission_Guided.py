from dronekit import VehicleMode
from Mission import Mission

class Mission_Guided(Mission):
    """
    A mission that uses the GUIDED mode to move on the fly.

    This allows the mission to react to unknown situations determined using
    sensors.
    """

    def start(self):
        # Set mode to GUIDED. In fact the arming should already have done this, 
        # but it is good to do it here as well.
        self.vehicle.mode = VehicleMode("GUIDED")
