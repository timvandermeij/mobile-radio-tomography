from ..utils.Geometry import *
from VRMLLoader import VRMLLoader

class Environment(object):
    """
    Simulated environment including objects around the vehicle and potentially the vehicle itself.
    This allows us to simulate a mission without many dependencies on DroneKit.
    """

    def __init__(self, vehicle, scenefile=None):
        self.vehicle = vehicle

        if scenefile is not None:
            loader = VRMLLoader(self, scenefile)
            self.objects = loader.get_objects()
            print(len(self.objects))
            return

        # TODO: Remove hardcoded objects
        l1 = self.get_location((100, 0, 10))
        l2 = self.get_location((0, 100, 10))
        l3 = self.get_location((-100, 0, 10))
        l4 = self.get_location((0, -100, 10))
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

    def get_location(self, point=None):
        """
        Retrieve the location of the vehicle, or a `point` relative to the location of the vehicle.
        """

        if point is not None:
            return get_location_meters(self.vehicle.location, *point)

        return self.vehicle.location

    def get_yaw(self):
        return self.vehicle.attitude.yaw
