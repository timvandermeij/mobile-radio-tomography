from Environment import Environment
from VRMLLoader import VRMLLoader
from ..distance.Distance_Sensor_Simulator import Distance_Sensor_Simulator
from ..trajectory.MockVehicle import MockVehicle

class Environment_Simulator(Environment):
    """
    Simulated environment including objects around the vehicle and potentially the vehicle itself.
    This allows us to simulate a mission without many dependencies on ArduPilot.
    """

    _sensor_class = Distance_Sensor_Simulator

    def __init__(self, vehicle, geometry, arguments):
        super(Environment_Simulator, self).__init__(vehicle, geometry, arguments)
        scenefile = self.settings.get("scenefile")
        translation = self.settings.get("translation")
        if isinstance(self.vehicle, MockVehicle):
            self.vehicle.home_location = self.get_location(*translation)
            self.geometry.set_home_location(self.vehicle.home_location)
            if scenefile is not None and self.settings.get("location_check"):
                self.vehicle.set_location_callback(self.check_location)

        if scenefile is not None:
            loader = VRMLLoader(self, scenefile, translation)
            self.objects = loader.get_objects()
            return

        # Use hardcoded objects for testing
        l1 = self.get_location(100, 0, 10)
        l2 = self.get_location(0, 100, 10)
        l3 = self.get_location(-100, 0, 10)
        l4 = self.get_location(0, -100, 10)

        # Simplify function call
        get_location_meters = self.geometry.get_location_meters
        self.objects = [
            {
                'center': get_location_meters(self.vehicle.location, 40, -10),
                'radius': 2.5,
            },
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

    def get_objects(self):
        return self.objects

    def check_location(self, location, new_location):
        for obj in self.objects:
            if isinstance(obj, list):
                for face in obj:
                    factor, loc_point = self.geometry.get_plane_intersection(face, location, new_location)
                    if 0 <= factor <= 1:
                        raise RuntimeError("Flew through an object")
