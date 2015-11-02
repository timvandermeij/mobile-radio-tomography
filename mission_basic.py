"""
mission_basic.py: Basic mission operations for creating and monitoring missions.

Documentation is provided at http://python.dronekit.io/examples/mission_basic.html
"""

import sys
import os
import time
import math
import traceback

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from matplotlib.collections import PatchCollection

# Package imports
# Ensure that we can import from the current directory as a package since 
# running this via pymavproxy makes it not have this in the path, and running 
# scripts in general does not define the correct package
sys.path.insert(0, os.getcwd())
from __init__ import __package__
from settings import Arguments
from trajectory import Mission, Environment, Environment_Simulator
from trajectory.MockVehicle import MockAPI, MockVehicle
from trajectory.Viewer import Viewer_Vehicle
from geometry import Geometry

class Plot(object):
    """
    Plotter that can display an environment memory map.
    """
    def __init__(self, environment, memory_map):
        self.environment = environment
        self.memory_map = memory_map
        self._setup()

    def _create_patch(self, obj):
        if isinstance(obj, tuple):
            return Polygon([self.memory_map.get_xy_index(loc) for loc in obj])
        elif 'center' in obj:
            idx = self.memory_map.get_xy_index(obj['center'])
            return Circle(idx, radius=obj['radius'])

        return None

    def _setup(self):
        # "Cheat" to see 2d map of collision data
        patches = []
        if isinstance(self.environment, Environment_Simulator):
            for obj in self.environment.get_objects():
                patch = self._create_patch(obj)
                if patch is not None:
                    patches.append(patch)

        p = None
        if len(patches) > 0:
            p = PatchCollection(patches, cmap=matplotlib.cm.jet, alpha=0.4)
            patch_colors = 50*np.ones(len(patches))
            p.set_array(np.array(patch_colors))

        self.plot_polygons = p
        self.plt = plt
        self.fig, self.ax = self.plt.subplots()

        # Set up interactive drawing of the memory map. This makes the 
        # dronekit/mavproxy fairly annoyed since it creates additional 
        # threads/windows. One might have to press Ctrl-C and normal keys to 
        # make the program stop.
        self.plt.gca().set_aspect("equal", adjustable="box")
        self.plt.ion()
        self.plt.show()

    def get_plot(self):
        return self.plt

    def display(self):
        if self.plot_polygons is not None:
            self.ax.add_collection(self.plot_polygons)

        self._plot_vehicle_angle()

        self.plt.imshow(self.memory_map.get_map(), origin='lower')
        self.plt.pause(sys.float_info.epsilon)
        self.plt.cla()

    def _plot_vehicle_angle(self):
        options = {
            "arrowstyle": "->",
            "color": "red",
            "linewidth": 2,
            "alpha": 0.5
        }
        vehicle_idx = self.memory_map.get_xy_index(self.environment.get_location())
        angle = self.environment.get_angle()
        arrow_length = 10.0
        if angle == 0.5*math.pi:
            angle_idx = (vehicle_idx[0], vehicle_idx[1] + arrow_length)
        elif angle == 1.5*math.pi:
            angle_idx = (vehicle_idx[0], vehicle_idx[1] - arrow_length)
        else:
            angle_idx = (vehicle_idx[0] + math.cos(angle) * arrow_length, vehicle_idx[1] + math.sin(angle) * arrow_length)

        self.plt.annotate("", angle_idx, vehicle_idx, arrowprops=options)

    def close(self):
        self.plt.close()
        self.plt = None

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
        self.loop_delay = self.settings.get("loop_delay")

        self.sensors = self.environment.get_distance_sensors()

        self.colors = ["red", "purple", "black"]

        self.memory_map = None
        self.plot = None

    def get_delay(self):
        return self.loop_delay

    def use_viewer(self):
        return self.settings.get("viewer")

    def setup(self):
        self.memory_map = self.mission.get_memory_map()

        if self.settings.get("plot"):
            # Setup memory map plot
            self.plot = Plot(self.environment, self.memory_map)

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

                print("=== [!] Distance to object: {} m (yaw {}, pitch {}) ===".format(sensor_distance, yaw, pitch))

            i = i + 1

        # Display the current memory map interactively.
        if self.plot:
            self.plot.display()

        if not self.mission.check_waypoint():
            return False

        # Remove the vehicle from the current location. We set it to "safe" 
        # since there is no object here.
        self.memory_map.set(vehicle_idx, 0)

        return True

    def stop(self):
        if self.plot:
            self.plot.close()

# Main mission program
def main(argv):
    arguments = Arguments("settings.json", argv)
    mission_settings = arguments.get_settings("mission")

    geometry_class = mission_settings.get("geometry_class")
    geometry = Geometry.__dict__[geometry_class]()

    simulation = mission_settings.get("vehicle_simulation")
    if __name__ == "__main__":
        # Directly running the file means we use our own simulation
        if not simulation:
            raise ValueError("Mock vehicle can only be used in simulation")

        api = MockAPI()
        vehicle = MockVehicle(geometry)
    else:
        # We're running via builtins execfile or some other module, so assume 
        # we use ArduPilot simulation/actual MAVProxy link to the vehicle's 
        # flight controller.
        if not isinstance(geometry, Geometry.Geometry_Spherical):
            raise ValueError("Dronekit only works with spherical geometry")

        # Connect to API provider and get vehicle object
        api = local_connect()
        vehicle = api.get_vehicles()[0]

    if simulation:
        environment = Environment_Simulator(vehicle, geometry, arguments)
    else:
        environment = Environment(vehicle, geometry, arguments)

    mission_class = mission_settings.get("mission_class")
    mission = Mission.__dict__[mission_class](api, environment, mission_settings)

    monitor = Monitor(api, mission, environment)

    arguments.check_help()

    print("Setting up mission")
    mission.setup()
    mission.display()

    # As of ArduCopter 3.3 it is possible to take off using a mission item.
    mission.arm_and_takeoff()

    print("Starting mission")
    mission.start()

    # Monitor mission
    monitor.setup()

    try:
        if monitor.use_viewer():
            viewer = Viewer_Vehicle(environment, monitor)
            viewer.start()
        else:
            ok = True
            while ok:
                ok = monitor.step()
                if ok:
                    time.sleep(monitor.get_delay())
    except Exception, e:
        # Handle exceptions gracefully by attempting to stop the program 
        # ourselves. Unfortunately KeyboardInterrupts are not passed to us when 
        # we run under pymavlink.
        traceback.print_exc()

    monitor.stop()
    mission.return_to_launch()

# The 'api start' command of pymavlink executes the script using the builtin 
# function `execfile`, which makes the module name __builtin__, so allow this 
# as well as directly executing the file. Ensure MAVProxy arguments do not 
# conflict with our own arguments.
if __name__ == "__main__":
    main(sys.argv[1:])
elif __name__ == "__builtin__":
    main([])
