import math
import numpy as np
from Mission_Browse import Mission_Browse

class Mission_Search(Mission_Browse):
    """
    Mission that moves around objects and avoids them while trying to stay as
    close as possible to the object of interest.
    """

    def setup(self):
        super(Mission_Search, self).setup()
        self.move_distance = 0
        self.start_location = self.environment.get_location()

        self.dists_size = 360 / self.yaw_angle_step
        self.dists = np.zeros(self.dists_size)
        self.dists_done = np.zeros(self.dists_size, dtype=bool)

        self.yaw_margin = 5.0 * math.pi/180

    def _get_yaw_safeness(self, current_location):
        dist = 0
        i = 0
        d_left = 0
        right = 0
        cycle_safe = 0
        safeness = np.zeros(self.dists_size)
        for d in self.dists:
            if d == 0:
                right = right + 1
            else:
                dist = d + self.padding + self.closeness
                angle = (i + right - 1) * self.yaw_angle_step * math.pi/180
                loc = self.geometry.get_location_angle(current_location,
                                                       dist, angle)
                if i == 0:
                    cycle_safe = right
                elif i == self.dists_size - 1:
                    break
                else:
                    safeness[i] = right + d_left

                if self.memory_map.location_in_bounds(loc):
                    d_left = d/float(self.farness)
                else:
                    d_left = -right

                safeness[(i + right - 1) % self.dists_size] = right + d_left

                i = i + right + 1
                right = 0

        safeness[i % self.dists_size] = right + cycle_safe + d_left
        return safeness

    def step(self):
        if self.move_distance > 0:
            moved = self.environment.get_distance(self.start_location)
            d = self.move_distance - moved
            if d <= 0:
                self.move_distance = 0

        if self.move_distance == 0:
            super(Mission_Search, self).step()

            if all(self.dists_done):
                start_location = self.environment.get_location()

                # Find safest "furthest" location (in one line) and move there
                safeness = self._get_yaw_safeness(start_location)

                a = np.argmax(self.dists + safeness)
                dist = self.dists[a] + self.padding + self.closeness

                angle_right = (a + 1) % self.dists_size
                angle_left = (a - 1) % self.dists_size
                if safeness[angle_right] > safeness[angle_left]:
                    a = a + 2
                else:
                    a = a - 2

                angle = a * self.yaw_angle_step * math.pi/180
                self.yaw = self.geometry.angle_to_bearing(angle)

                self.move_distance = dist
                self.start_location = start_location

                self.dists = np.zeros(self.dists_size)
                self.dists_done = np.zeros(self.dists_size, dtype=bool)

                self.set_yaw(self.yaw * 180/math.pi, relative=False)
                self.vehicle.speed = self.speed
                new_location = self.geometry.get_location_angle(start_location,
                                                                dist, angle)
                self.vehicle.simple_goto(new_location)

    def check_sensor_distance(self, sensor_distance, yaw, pitch):
        close = super(Mission_Search, self).check_sensor_distance(sensor_distance, yaw, pitch)

        angle_deg = yaw * 180/math.pi
        a = int(angle_deg / self.yaw_angle_step)
        self.dists_done[a] = True
        if sensor_distance < self.farness:
            self.dists[a] = sensor_distance

        if sensor_distance < self.padding + self.closeness:
            new_yaw = self.environment.get_yaw()
            if self.geometry.check_angle(self.yaw, new_yaw, self.yaw_margin):
                self.move_distance = 0

        return close
