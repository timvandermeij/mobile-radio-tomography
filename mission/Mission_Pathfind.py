import math
import numpy as np
from Mission_Browse import Mission_Browse
from Mission_Square import Mission_Square

class Mission_Pathfind(Mission_Browse, Mission_Square):
    def add_commands(self):
        pass

    def check_waypoint(self):
        return True

    def start(self):
        super(Mission_Pathfind, self).start()
        self.points = self.get_points()
        self.current_point = -1
        self.next_waypoint = 0
        self.browsing = False
        self.rotating = False
        self.start_yaw = self.yaw
        self.padding = self.settings.get("padding")
        self.sensor_dist = sys.float_info.max

    def get_waypoints(self):
        return self.points

    def distance_to_point(self):
        if self.current_point < 0:
            return 0

        point = self.points[self.current_point]
        return self.environment.get_distance(point)

    def step(self):
        if self.current_point >= len(self.points):
            return

        if self.browsing:
            super(Mission_Pathfind, self).step()
            if self.geometry.check_angle(self.start_yaw, self.yaw, self.yaw_angle_step * math.pi/180):
                self.browsing = False

                points = self.astar(self.vehicle.location.global_relative_frame, self.points[self.next_waypoint])
                if not points:
                    raise RuntimeError("Could not find a suitable path to the next waypoint.")

                self.points[self.current_point:self.next_waypoint] = points
                self.next_waypoint = self.current_point + len(points)
                self.vehicle.speed = self.speed
                self.vehicle.simple_goto(self.points[self.current_point])
                self.rotating = True
                self.start_yaw = self.vehicle.attitude.yaw
        elif self.rotating:
            # Keep track of whether we are rotating because of a goto command.
            if self.geometry.check_angle(self.start_yaw, self.vehicle.attitude.yaw, self.yaw_angle_step * math.pi/180):
                self.rotating = False
                if self.check_scan():
                    return
            else:
                self.start_yaw = self.vehicle.attitude.yaw

        distance = self.distance_to_point()
        print("Distance to current point ({}): {} m".format(self.current_point, distance))
        if self.current_point < 0 or distance <= self.closeness:
            if self.current_point == self.next_waypoint:
                print("Waypoint reached.")
                self.next_waypoint = self.next_waypoint + 1

            self.current_point = self.current_point + 1
            if self.current_point >= len(self.points):
                print("Reached final point.")
                return

            print("Next point ({}): {}".format(self.current_point, self.points[self.current_point]))

            self.vehicle.simple_goto(self.points[self.current_point])

    def check_sensor_distance(self, sensor_distance, yaw, pitch):
        close = super(Mission_Pathfind, self).check_sensor_distance(sensor_distance, yaw, pitch)
        # Do not start scanning if we already are or if we are rotating because 
        # of a goto command.
        self.sensor_dist = sensor_distance
        if not self.browsing and not self.rotating:
            self.check_scan()

        return close

    def check_scan(self):
        if self.sensor_dist < 2 * self.padding + self.closeness:
            print("Start scanning due to closeness.")
            self.send_global_velocity(0,0,0)
            self.browsing = True
            self.start_yaw = self.yaw = self.vehicle.attitude.yaw
            return True

        return False

    def astar(self, start, goal):
        closeness = min(self.sensor_dist - self.padding, self.padding + self.closeness)
        resolution = float(self.memory_map.get_resolution())
        size = self.memory_map.get_size()
        start_idx = self.memory_map.get_index(start)
        goal_idx = self.memory_map.get_index(goal)
        nonzero = self.memory_map.get_nonzero()

        evaluated = set()
        open_nodes = set([start_idx])
        came_from = {}

        # Cost along best known path
        g = np.full((size,size), np.inf)
        g[start_idx] = 0.0

        # Estimated total cost from start to goal when passing through 
        # a specific index.
        f = np.full((size,size), np.inf)
        f[start_idx] = self.cost(start, goal)

        while open_nodes:
            # Get the node in open_nodes with the lowest f score
            open_idx = [idx for idx in open_nodes]
            min_idx = np.argmin(f[[idx[0] for idx in open_idx], [idx[1] for idx in open_idx]])
            current_idx = open_idx[min_idx]
            if current_idx == goal_idx:
                return self.reconstruct(came_from, goal_idx)

            open_nodes.remove(current_idx)
            evaluated.add(current_idx)
            current = self.memory_map.get_location(*current_idx)
            for neighbor_idx in self.neighbors(current_idx):
                if neighbor_idx in evaluated:
                    continue

                try:
                    if self.memory_map.get(neighbor_idx) == 1:
                        continue
                except KeyError:
                    break

                if self.too_close(neighbor_idx, nonzero, closeness, resolution):
                    continue

                neighbor = self.memory_map.get_location(*neighbor_idx)
                tentative_g = g[current_idx] + self.geometry.get_distance_meters(current, neighbor)
                open_nodes.add(neighbor_idx)
                if tentative_g >= g[neighbor_idx]:
                    # Not a better path
                    continue

                came_from[neighbor_idx] = current_idx
                g[neighbor_idx] = tentative_g
                f[neighbor_idx] = tentative_g + self.cost(neighbor, goal)

        return []

    def reconstruct(self, came_from, current):
        # The path from goal point `current` to the start (in reversed form) 
        # containing waypoints that should be followed to get to the goal point
        total_path = []
        previous = current

        # The current trend of the differences between the points
        trend = None
        while current in came_from:
            current = came_from.pop(current)

            # Track the current trend of the point differences. If it is the 
            # same kind of difference, then we may be able to skip this point 
            # in our list of waypoints.
            d = tuple(np.sign(current[i] - previous[i]) for i in [0,1])
            if trend is None or (trend[0] != 0 and d[0] != trend[0]) or (trend[1] != 0 and d[1] != trend[1]):
                trend = d
                total_path.append(self.memory_map.get_location(*previous))
            else:
                trend = d

            previous = current

        return list(reversed(total_path))

    def neighbors(self, current):
        y, x = current
        return [(y-1, x-1), (y-1, x), (y-1, x+1),
                (y, x-1),             (y, x+1),
                (y+1, x-1), (y+1, x), (y+1, x+1)]

    def too_close(self, current, nonzero, closeness, resolution):
        for idx in nonzero:
            dist = math.sqrt(((current[0] - idx[0])/resolution)**2 + ((current[1] - idx[1])/resolution)**2)
            if dist < closeness:
                return True

        return False

    def cost(self, start, goal):
        return self.geometry.get_distance_meters(start, goal)
