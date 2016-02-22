import time
import dronekit
from MAVLink_Vehicle import MAVLink_Vehicle
from ..settings.Arguments import Arguments

class Dronekit_Vehicle(dronekit.Vehicle, MAVLink_Vehicle):
    """
    A vehicle that connects to a backend using MAVLink and the Dronekit library.
    """

    def __new__(cls, arguments, *a):
        if isinstance(arguments, Arguments):
            settings = arguments.get_settings("vehicle_dronekit")
            connect = settings.get("connect")
            baud_rate = settings.get("mavlink_baud_rate")
            vehicle = dronekit.connect(connect, baud=baud_rate, vehicle_class=cls)
            return vehicle
        else:
            return super(Dronekit_Vehicle, cls).__new__(cls, arguments, *a)

    def __init__(self, handler, geometry=None):
        if isinstance(handler, Arguments):
            self.settings = handler.get_settings("vehicle_dronekit")
            self._geometry = geometry
        else:
            super(Dronekit_Vehicle, self).__init__(handler)

            # Create home location listener
            @self.on_message(['WAYPOINT', 'MISSION_ITEM'])
            def listener(self, name, msg):
                if not self._wp_loaded and msg.seq == 0:
                    self.notify_attribute_listeners('home_location', self.home_location)

        self.wait = False

    def setup(self):
        # Whether to use GPS and thus also wait for a GPS fix before arming.
        self.use_gps = self.settings.get("gps")

        # Wait until location has been filled
        if self.use_gps:
            self.wait = True
            self.add_attribute_listener('location.global_relative_frame', self._listen)

            while self.wait:
                time.sleep(1.0)
                print('Waiting for location update...')

    def _listen(self, vehicle, attr_name, value):
        vehicle.remove_attribute_listener('location.global_relative_frame', self._listen)
        self.wait = False

    @property
    def use_simulation(self):
        return self.settings.get("vehicle_simulation")

    @dronekit.Vehicle.home_location.setter
    def home_location(self, pos):
        home_location = self._make_global_location(pos)
        dronekit.Vehicle.home_location.__set__(self, home_location)
        self.notify_attribute_listeners('home_location', home_location)
