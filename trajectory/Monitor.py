import thread
import time
from droneapi.lib import Location
from ..zigbee.XBee_Packet import XBee_Packet

class Monitor(object):
    """
    Mission monitor class.

    Tracks sensors and mission actions in a stepwise fashion.
    """

    def __init__(self, api, mission, environment):
        self.api = api
        self.mission = mission

        self.environment = environment
        arguments = self.environment.get_arguments()
        self.settings = arguments.get_settings("mission_monitor")

        # Seconds to wait before monitoring again
        self.step_delay = self.settings.get("step_delay")

        self.sensors = self.environment.get_distance_sensors()

        self.colors = ["red", "purple", "black"]

        self.memory_map = None
        self.plot = None

        self.stopped = False

    def get_delay(self):
        return self.step_delay

    def use_viewer(self):
        return self.settings.get("viewer")

    def setup(self):
        self.environment.add_packet_action("memory_map_chunk", self.add_memory_map)
        self.memory_map = self.mission.get_memory_map()

        if self.settings.get("plot"):
            # Setup memory map plot
            from Plot import Plot
            self.plot = Plot(self.environment, self.memory_map)

        if self.environment.get_xbee_sensor():
            thread.start_new_thread(self.xbee_sensor_loop, ())

    def step(self, add_point=None):
        """
        Perform one step of a monitoring loop.

        `add_point` can be a callback function that accepts a Location object for a detected point from the distance sensors.

        Returns `Fase` if the loop should be halted.
        """

        if self.api.exit:
            return False

        # Put our current location on the map for visualization. Of course, 
        # this location is also "safe" since we are flying there.
        vehicle_idx = self.memory_map.get_index(self.environment.get_location())
        self.memory_map.set(vehicle_idx, -1)

        self.mission.step()

        xbee_sensor = self.environment.get_xbee_sensor()

        i = 0
        for sensor in self.sensors:
            yaw = sensor.get_angle()
            pitch = sensor.get_pitch()
            sensor_distance = sensor.get_distance()

            if self.mission.check_sensor_distance(sensor_distance, yaw, pitch):
                location = self.memory_map.handle_sensor(sensor_distance, yaw)
                if add_point is not None:
                    add_point(location)
                if self.plot:
                    # Display the edge of the simulated object that is 
                    # responsible for the measured distance, and consequently 
                    # the point itself. This should be the closest "wall" in 
                    # the angle's direction. This is again a "cheat" for 
                    # checking if walls get visualized correctly.
                    sensor.draw_current_edge(self.plot.get_plot(), self.memory_map, self.colors[i % len(self.colors)])
                if xbee_sensor:
                    home_location = self.mission.get_home_location()
                    packet = XBee_Packet()
                    packet.set("specification", "memory_map_chunk")
                    packet.set("latitude", home_location.lat + location.lat)
                    packet.set("longitude", home_location.lon + location.lon)
                    xbee_sensor.enqueue(packet)

                print("=== [!] Distance to object: {} m (yaw {}, pitch {}) ===".format(sensor_distance, yaw, pitch))

            i = i + 1

        if xbee_sensor:
            xbee_sensor.activate()

        # Display the current memory map interactively.
        if self.plot:
            self.plot.plot_lines(self.mission.get_waypoints())
            self.plot.display()

        if not self.mission.check_waypoint():
            return False

        # Remove the vehicle from the current location. We set it to "safe" 
        # since there is no object here.
        self.memory_map.set(vehicle_idx, 0)

        return True

    def xbee_sensor_loop(self):
        xbee_sensor = self.environment.get_xbee_sensor()
        loop_delay = xbee_sensor.settings.get("loop_delay")
        while not self.stopped:
            xbee_sensor.activate()
            time.sleep(loop_delay)

    def sleep(self):
        time.sleep(self.step_delay)

    def add_memory_map(self, packet):
        loc = Location(packet.get("latitude"), packet.get("longitude"), 0.0, is_relative=False)
        idx = self.memory_map.get_index(loc)
        print(loc.lat, loc.lon, idx)
        try:
            self.memory_map.set(idx, 1)
        except KeyError:
            pass

    def stop(self):
        self.stopped = True
        xbee_sensor = self.environment.get_xbee_sensor()
        if xbee_sensor:
            xbee_sensor.deactivate()

        if self.plot:
            self.plot.close()
