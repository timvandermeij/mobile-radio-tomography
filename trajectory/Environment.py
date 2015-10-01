from ..utils.Geometry import *

class Environment(object):
    """
    Simulated environment including objects around the vehicle and potentially the vehicle itself.
    This allows us to simulate a mission without many dependencies on DroneKit.
    """

    def __init__(self, vehicle):
        self.vehicle = vehicle
        # TODO: Replace hardcoded objects with some sort of polygon database 
        # and move them out of the sensor simulator
        l1 = get_location_meters(self.vehicle.location, 100, 0, 10)
        l2 = get_location_meters(self.vehicle.location, 0, 100, 10)
        l3 = get_location_meters(self.vehicle.location, -100, 0, 10)
        l4 = get_location_meters(self.vehicle.location, 0, -100, 10)
        #l3 = get_location_meters(self.vehicle.location, 52.5, 22.5, 10)

        self.objects = [
            #{
            #    'center': get_location_meters(self.vehicle.location, 40, -10),
            #    'radius': 2.5,
            #},
            (get_location_meters(l1, 40, -40), get_location_meters(l1, 40, 40),
             get_location_meters(l1, -40, 40), get_location_meters(l1, -40, -40)),
            (get_location_meters(l2, 40, -40), get_location_meters(l2, 40, 40),
             get_location_meters(l2, -40, 40), get_location_meters(l2, -40, -40)),
            (get_location_meters(l3, 40, -40), get_location_meters(l3, 40, 40),
             get_location_meters(l3, -40, 40), get_location_meters(l3, -40, -40)),
            (get_location_meters(l4, 40, -40), get_location_meters(l4, 40, 40),
             get_location_meters(l4, -40, 40), get_location_meters(l4, -40, -40))
        ]

    def get_location(self):
        return self.vehicle.location

    def get_yaw(self):
        return self.vehicle.attitude.yaw
