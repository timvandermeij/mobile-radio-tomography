import dronekit
from MAVLink_Vehicle import MAVLink_Vehicle

class Dronekit_Vehicle(dronekit.Vehicle, MAVLink_Vehicle):
    """
    A vehicle that connects to a backend using MAVLink and the Dronekit library.
    """

    pass
