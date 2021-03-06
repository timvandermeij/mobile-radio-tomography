import numpy as np
from ..environment.Location_Proxy import Location_Proxy
from ..location.AStar import AStar
from ..trajectory.Memory_Map import Memory_Map

class Collision_Type(object):
    ROUTE = 1
    VEHICLE = 2
    NETWORK = 3

class Collision_Avoidance(Location_Proxy):
    """
    An algorithm that detects and attempts to solve potential problems with
    vehicles crossing each other's routes in between waypoints.
    """

    def __init__(self, arguments, geometry):
        super(Collision_Avoidance, self).__init__(geometry)

        self._settings = arguments.get_settings("planning_collision_avoidance")
        self._enabled = self._settings.get("collision_avoidance")
        self._network_size = self._settings.get("network_size")
        self._network_padding = self._settings.get("network_padding")
        self._unsafe_path_cost = self._settings.get("unsafe_path_cost")
        self._assign_safe_path = self._settings.get("assign_safe_path")

        self._vehicles = set()
        self._vehicle_syncs = {}
        self._vehicle_routes = {}
        self._vehicle_distances = np.empty(0)
        self._current_vehicle = 0

        center = (max(self._network_size) + 1)/2.0
        self._center = self._geometry.make_location(center, center)
        self._memory_map = Memory_Map(self, max(self._network_size) + 1)
        self._astar = AStar(self._geometry, self._memory_map,
                            allow_at_bounds=True, use_indices=True)
        self.reset()

    def reset(self):
        self._memory_map.clear()

        self._vehicles = set()
        self._vehicle_syncs = {}
        self._vehicle_routes = {}
        self._vehicle_distances = np.empty(0)
        self._current_vehicle = 0

        min_y = self._network_padding[0] + 1
        min_x = self._network_padding[1] + 1
        max_y = self._network_size[0] - self._network_padding[0]
        max_x = self._network_size[1] - self._network_padding[1]
        for i in xrange(min_y, max_y):
            self._memory_map.set((i, min_x), Collision_Type.NETWORK)
            self._memory_map.set((i, max_x - 1), Collision_Type.NETWORK)
        for i in xrange(min_x, max_x):
            self._memory_map.set((min_y, i), Collision_Type.NETWORK)
            self._memory_map.set((max_y - 1, i), Collision_Type.NETWORK)

    @property
    def location(self):
        if self._current_vehicle in self._vehicle_routes:
            current_point = self._vehicle_routes[self._current_vehicle][-1]
            return self._geometry.make_location(*current_point)

        return self._center

    @property
    def distance(self):
        """
        Retrieve the distance of the route between the current waypoint and
        the previous one for the vehicle that was previously updated.
        """

        if self._current_vehicle in self._vehicle_distances:
            return self._vehicle_distances[self._current_vehicle]

        return 0.0

    def _update_route(self, route, value):
        self._memory_map.set_multi(route[:-1], value)

        if value != 0:
            self._memory_map.set(route[-1], Collision_Type.VEHICLE)

    def _is_synchronized(self, other_vehicle):
        if self._current_vehicle == other_vehicle:
            return True

        if other_vehicle not in self._vehicle_syncs[self._current_vehicle]:
            return False

        return self._current_vehicle in self._vehicle_syncs[other_vehicle]

    def update(self, home_locations, new_position, vehicle, other_vehicle,
               norm_distance, direction=None, turning_cost=0.0):
        """
        Update the collision avoidance and find a safe path to a new position.

        The vehicles are tracked by their indices in the `home_locations` list,
        which are coordinate tuples. `new_position` is a coordinate tuple of the
        goal location for the current vehicle with ID `vehicle`. This waypoint
        will synchronize by waiting for the vehicle with ID `other_vehicle`.
        The `norm_distance` is an indication of the distance between the
        previous waypoint and the new waypoint.

        The collision avoidance algorithm attempts to find a path from
        the previous waypoint to the current waypoint crosses any concurrent
        paths, including those of vehicles that do not synchronize with the
        current vehicle before this point. It then replaces the current path
        with another the safe one, and updates it internal state as well as
        the vehicle's location and distance. If there is no safe path, then
        the distance becomes the `norm_distance` plus the unsafe path cost,
        which is `np.inf` by default.
        """

        if not self._enabled:
            return [], None

        if not self._vehicle_routes:
            number_of_vehicles = len(home_locations)

            self._vehicles = set(range(1, number_of_vehicles + 1))
            self._vehicle_distances = dict([
                (i, np.inf) for i in self._vehicles
            ])
            self._vehicle_syncs = dict([(i, set([i])) for i in self._vehicles])

            for i, home in enumerate(home_locations):
                home = (int(home[0]), int(home[1]))
                home = tuple(np.clip(home, (0, 0), self._network_size))
                self._vehicle_routes[i+1] = [home]
                self._memory_map.set(home, Collision_Type.VEHICLE)

        self._current_vehicle = vehicle

        # Update the memory map with possibly conflicting routes.
        # Remove the old route of the current vehicle from the memory map, 
        # since it can never intersect with its own route.
        # Also ignore vehicles who have synchronized with this vehicle.
        # Keep the most recent location of other vehicles as unsafe location.
        for v, route in self._vehicle_routes.iteritems():
            if self._is_synchronized(v):
                self._update_route(route, 0)

        # Determine a conflict-free (and thus safe) path from the current 
        # position to the new position, and unpack the results.
        start_index = self._vehicle_routes[self._current_vehicle][-1]
        goal_index = tuple(new_position)

        route, trend, distance, new_direction = \
            self._astar.assign(start_index, goal_index, 1.0,
                               direction=direction, turning_cost=turning_cost)

        # If we could not find a route, then there is no safe route. This is 
        # made known through the distance, which becomes the cost of traveling 
        # an unsafe route, but to keep this method functional, consider the 
        # route to go to the next point immediately.
        if not route:
            route = [goal_index]
            distance = norm_distance + self._unsafe_path_cost

        if len(route) > 1 or start_index != goal_index:
            # Only add the new route to the old one if we changed our location 
            # due to it. If we stay at the same location, then this would 
            # conflict with our route erasing.
            self._vehicle_routes[vehicle].extend(route)

        self._vehicle_distances[vehicle] = distance
        self._vehicle_syncs[vehicle].add(other_vehicle)

        for v, sync in self._vehicle_syncs.iteritems():
            if self._is_synchronized(v):
                route = self._vehicle_routes[v]
                if vehicle != v and sync == self._vehicles:
                    # A fully synchronized vehicle no longer has a route that 
                    # other vehicles could conflict with. Thus remove the route 
                    # except for the vehicle's current location, and reset its 
                    # synchronization. Since the `other_vehicle` might need to 
                    # synchronize with it after this call, we do not yet 
                    # consider the current vehicle for this check.
                    sync.clear()
                    sync.add(v)
                    self._update_route(route, 0)
                    del self._vehicle_routes[v][:-1]
                else:
                    # Place the route back after we temporarily removed it for 
                    # the current vehicle which could cross the path, or extend 
                    # the current vehicle's route with the new one.
                    self._update_route(route, Collision_Type.ROUTE)

        path = trend[:-1] if self._assign_safe_path else []
        return path, new_direction
