import itertools
import math
import numpy as np
from ..location.Line_Follower import Line_Follower_Direction
from ..waypoint.Waypoint import Waypoint, Waypoint_Type
from Collision_Avoidance import Collision_Avoidance

class Greedy_Assignment(object):
    """
    Synchronized traveling salesmen's tasks assignment problem algorithm.

    We use a greedy strategy to appoint a number of vehicles to visit a number
    of waypoint pairs. It does not matter which vehicle visits which waypoint,
    but each waypoint within a pair must be visited by different vehicles at the
    same moment in time (or they have to wait for the other vehicle to arrive).
    We want to minimize the time loss due to this synchronization as well as
    the time needed to visit the waypoint pairs, which can be done in any order.

    The time is calculated using the Manhattan distance in this class. Other
    implementations could add in the time needed for turning and synchronization
    or use a different distance function.
    """

    def __init__(self, arguments, geometry, import_manager):
        self._settings = arguments.get_settings("planning_assignment")
        self._geometry = geometry
        self._import_manager = import_manager

        self._home_locations = self._settings.get("vehicle_home_locations")
        self._home_directions = self._settings.get("vehicle_home_directions")
        self._turning_cost = self._settings.get("turning_cost")

        self._number_of_vehicles = len(self._home_locations)

        self._vehicle_pairs = list(
            itertools.permutations(range(1, self._number_of_vehicles + 1), r=2)
        )
        self._collision_avoider = Collision_Avoidance(arguments, geometry)

        self._export = True

        self._assignment = None
        self._positions = None
        self._current_positions = None
        self._current_directions = None
        self._number_of_waits = None

    def _add_waypoint(self, vehicle, position, waypoint_type, wait_id=0,
                      wait_count=1, wait_waypoint=-1, home_direction=0):
        """
        Create a waypoint for the vehicle with sensor ID `vehicle`, based on
        the given coordinate tuple `position` and additional type-specific
        data, and add it to the assignment.

        The assignment can be altered to add different waypoint types using the
        `waypoint_type` keyword argument, which expects a `Waypoint_Type` enum
        value. For wait types, `wait_id`, `wait_count` and `wait_waypoint`
        integers are allowed, and for the home waypoint type, `home_direction`
        is allowed.
        """

        if self._export:
            # The wait ID and home direction share a "union" in a the exported 
            # waypoints lists.
            if waypoint_type == Waypoint_Type.HOME:
                wait_id = home_direction

            waypoint = list(position) + [
                0, waypoint_type, wait_id, wait_count, wait_waypoint
            ]
        else:
            location = self._geometry.make_location(*position)
            waypoint = Waypoint.create(self._import_manager, waypoint_type,
                                       vehicle, self._geometry, location,
                                       wait_id=wait_id, wait_count=wait_count,
                                       wait_waypoint=wait_waypoint,
                                       home_direction=home_direction)

        self._assignment[vehicle].append(waypoint)

    def _calculate_vehicle_distances(self):
        V = np.full((self._number_of_vehicles, 2, len(self._positions)), np.nan)
        for vehicle in range(self._number_of_vehicles):
            for i in range(2):
                # The traveling distance: Manhattan grid distance
                D = self._positions[:, i, :] - self._current_positions[vehicle]
                # Indications of whether we travel upward/downward/neutral and 
                # leftward/rightward/neutral.
                S = np.sign(D)

                # Determine how many turns the vehicle needs to make to get to 
                # the positions, so whether we need to turn left/right and then 
                # optionally turn in the same direction again, or turn around 
                # completely.
                cur = self._current_directions[vehicle]
                right = abs(S[:, (cur.axis + 1) % 2])
                straight = (2 - right) * (S[:, cur.axis] == -cur.sign)
                T = straight + right

                V[vehicle, i, :] = abs(D).sum(axis=1) + self._turning_cost * T

        return V

    def _get_new_direction(self, vehicle, new_position):
        up = new_position[0] - self._current_positions[vehicle-1][0]
        right = new_position[1] - self._current_positions[vehicle-1][1]

        cur = [self._current_directions[vehicle-1] == d for d in range(4)]
        if up == 0 or (up > 0 and cur[Line_Follower_Direction.UP]) or \
                      (up < 0 and cur[Line_Follower_Direction.DOWN]):
            if right > 0:
                return Line_Follower_Direction.RIGHT
            if right < 0:
                return Line_Follower_Direction.LEFT

            return self._current_directions[vehicle-1]

        if right == 0 or (right > 0 and cur[Line_Follower_Direction.RIGHT]) or \
                         (right < 0 and cur[Line_Follower_Direction.LEFT]):
            if up > 0:
                return Line_Follower_Direction.UP

            return Line_Follower_Direction.DOWN

        # up != 0, right != 0, and either up or right is in the wrong direction 
        # compared to the current direction. thus the next direction is the 
        # inverse of the current direction.
        return self._current_directions[vehicle-1].invert()

    def _get_closest_pair(self):
        V = self._calculate_vehicle_distances()
        distances = np.array([
            [
                V[vehicle-1, i, :] for i, vehicle in enumerate(vehicle_pair)
            ] for vehicle_pair in self._vehicle_pairs
        ])

        # Given that both vehicles operate at the same time and synchronize at 
        # the next waypoint, the time needed depends on the longest distance 
        # that either vehicle needs to move. Thus take the maximum.
        totals = distances.max(axis=1)

        # Determine the indices of the combination of vehicle and sensor pair 
        # that minimize the distances.
        indices = np.unravel_index(np.argmin(totals), totals.shape)
        return indices, totals[indices]

    def _assign_pair(self, vehicle_pair, closest_pair, distance):
        # Determine the synchronization (waits) between the two vehicles in the 
        # chosen vehicle pair. There are always two permutations here.
        syncs = list(itertools.permutations(self._vehicle_pairs[vehicle_pair]))
        waits = [
            self._number_of_waits[other_vehicle-1] for _, other_vehicle in syncs
        ]
        for i, sync_pair in enumerate(syncs):
            vehicle, other_vehicle = sync_pair
            wait_waypoint = waits[i]

            # The coordinates of the next position for the given vehicle, and 
            # the direction of the vehicle after moving to this position.
            new_position = list(self._positions[closest_pair, i, :])
            new_direction = self._get_new_direction(vehicle, new_position)

            # Check whether the new position is problematic according to the 
            # collision avoidance algorithm, i.e., it crosses other current 
            # routes.
            yaw_direction = self._current_directions[vehicle-1].yaw
            yaw_turning_cost = self._turning_cost / (math.pi/2)
            route, direction = \
                self._collision_avoider.update(self._home_locations,
                                               new_position, vehicle,
                                               other_vehicle, distance,
                                               direction=yaw_direction,
                                               turning_cost=yaw_turning_cost)

            if self._collision_avoider.distance > distance:
                distance = self._collision_avoider.distance
                if distance == np.inf:
                    return distance

            for point in route:
                self._add_waypoint(vehicle, point, Waypoint_Type.PASS)

            if direction is not None:
                new_direction = Line_Follower_Direction.from_yaw(direction)

            # Track the new position and direction
            self._current_positions[vehicle-1] = new_position
            self._current_directions[vehicle-1] = new_direction
            self._number_of_waits[vehicle-1] += 1

            # Assign the sensor waypoint, including the position and the other 
            # vehicle's wait ID.
            self._add_waypoint(vehicle, new_position, Waypoint_Type.WAIT,
                               wait_id=other_vehicle, wait_count=1,
                               wait_waypoint=wait_waypoint)

        return distance

    def assign(self, positions_pairs, export=True):
        """
        Assign the vehicles with current positions `home_positions` an ordering
        of the position pairs to be visited. `positions_pairs` must be a numpy
        array of size (Nx2x2), where N is the number of pairs, and the other
        dimensions encompass the pairs and the coordinates of each position,
        respectively.

        The returned values are the assignment, which is a dictionary with
        vehicle indexes and an ordered list of waypoints to visit, and the
        total distance needed for this assignment according to the algorithm.
        If `export` is `True`, then the waypoints are lists that can be exported
        as JSON. Set `export` to `False` to receive `Waypoint` objects instead.
        """

        self._export = export
        self._collision_avoider.reset()

        self._positions = np.array(positions_pairs, dtype=np.int)
        self._current_positions = list(self._home_locations)
        self._current_directions = [
            Line_Follower_Direction(d) for d in self._home_directions
        ]
        self._number_of_waits = dict([
            (i, 0) for i in range(self._number_of_vehicles)
        ])

        self._assignment = dict([
            (i, []) for i in range(1, self._number_of_vehicles + 1)
        ])
        for vehicle, home_location in enumerate(self._current_positions):
            self._add_waypoint(vehicle + 1, home_location, Waypoint_Type.HOME,
                               home_direction=self._current_directions[vehicle])

        total_distance = 0

        while len(self._positions) > 0:
            # The index of the distances matrix and the distance value itself.
            idx, distance = self._get_closest_pair()

            # The chosen vehicle pair and the chosen measurement positions pair
            vehicle_pair, closest_pair = idx

            distance = self._assign_pair(vehicle_pair, closest_pair, distance)

            if distance == np.inf:
                return {}, distance

            total_distance += distance

            self._positions = np.delete(self._positions, closest_pair, axis=0)

        return self._assignment, total_distance
