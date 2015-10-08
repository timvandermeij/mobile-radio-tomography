from VRMLLoader import VRMLLoader

class Environment(object):
    """
    Simulated environment including objects around the vehicle and potentially the vehicle itself.
    This allows us to simulate a mission without many dependencies on DroneKit.
    """

    def __init__(self, vehicle, geometry, simulation=None, scenefile=None):
        self.vehicle = vehicle
        self.geometry = geometry

        if not simulation:
            self.objects = []
            return

        if scenefile is not None:
            loader = VRMLLoader(self, scenefile)
            self.objects = loader.get_objects()
            return

        # TODO: Remove hardcoded objects
        l1 = self.get_location(100, 0, 10)
        l2 = self.get_location(0, 100, 10)
        l3 = self.get_location(-100, 0, 10)
        l4 = self.get_location(0, -100, 10)
        #l3 = get_location_meters(self.vehicle.location, 52.5, 22.5, 10)

        # Simplify function call
        get_location_meters = self.geometry.get_location_meters
        self.objects = [
            #{
            #    'center': get_location_meters(self.vehicle.location, 40, -10),
            #    'radius': 2.5,
            #},
            (get_location_meters(l1, 40, -40), get_location_meters(l1, 40, 40),
             get_location_meters(l1, -40, 40), get_location_meters(l1, -40, -40)
            ),
            (get_location_meters(l2, 40, -40), get_location_meters(l2, 40, 40),
             get_location_meters(l2, -40, 40), get_location_meters(l2, -40, -40)
            ),
            (get_location_meters(l3, 40, -40), get_location_meters(l3, 40, 40),
             get_location_meters(l3, -40, 40), get_location_meters(l3, -40, -40)
            ),
            (get_location_meters(l4, 40, -40), get_location_meters(l4, 40, 40),
             get_location_meters(l4, -40, 40), get_location_meters(l4, -40, -40)
            )
        ]

    def get_vehicle(self):
        return self.vehicle

    def get_geometry(self):
        return self.geometry

    def get_location(self, north=0, east=0, alt=0):
        """
        Retrieve the location of the vehicle, or a point relative to the location of the vehicle given in meters.
        """

        if north == 0 and east == 0 and alt == 0:
            return self.vehicle.location

        return self.geometry.get_location_meters(self.vehicle.location, north, east, alt)

    def get_distance(self, location):
        """
        Get the distance to the `location` from the vehicle's location.
        """
        return self.geometry.get_distance_meters(self.vehicle.location, location)

    def get_yaw(self):
        return self.vehicle.attitude.yaw
