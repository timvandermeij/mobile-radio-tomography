from Robot_Vehicle_Arduino import Robot_Vehicle_Arduino
from ..location.Line_Follower import Line_Follower_Direction
import time

class Robot_Vehicle_Arduino_Full(Robot_Vehicle_Arduino):
    """
    Robot vehicle that follows grid lines via a serial interface to an Arduino.

    To be used with the "zumo_grid" Arduino program.

    The Arduino sends status updates that the `Robot_Vehicle_Arduino_Full` keeps
    track of. We send grid positions to which we want to go to, and the Arduino
    handles the complete set of line following and determining how to reach the
    grid position.
    """

    def _setup_line_follower(self, thread_manager, usb_manager):
        # This class does not use the line follower.
        pass

    def activate(self):
        self._serial_connection.dtr = False
        time.sleep(0.022)
        super(Robot_Vehicle_Arduino_Full, self).activate()

    def _reset(self):
        # Send a DTR signal to reset the Arduino. According to a forum post at 
        # http://forum.arduino.cc/index.php?topic=38981.msg287027#msg287027 we 
        # need to send a low DTR for at least 22 ms to get a reset through.
        self._serial_connection.dtr = False
        time.sleep(0.022)
        self._serial_connection.dtr = True

    def _get_direction(self, zumo_direction):
        if zumo_direction == 'N':
            return Line_Follower_Direction.UP
        if zumo_direction == 'E':
            return Line_Follower_Direction.RIGHT
        if zumo_direction == 'S':
            return Line_Follower_Direction.DOWN
        if zumo_direction == 'W':
            return Line_Follower_Direction.LEFT

        raise ValueError("Invalid Zumo program direction: {}".format(zumo_direction))

    def _get_zumo_direction(self, direction):
        if direction == Line_Follower_Direction.UP:
            return 'N'
        if direction == Line_Follower_Direction.RIGHT:
            return 'E'
        if direction == Line_Follower_Direction.DOWN:
            return 'S'
        if direction == Line_Follower_Direction.LEFT:
            return 'W'

        raise ValueError("Invalid direction: {}".format(direction))

    def _check_state(self):
        # Use the state loop for direct serial connection handling.
        line = self._serial_connection.readline()
        parts = line.lstrip('\0').rstrip().split(' ')

        try:
            if parts[0] == "LOCA": # At grid intersection location
                self._location = (int(parts[1]), int(parts[2]))
                self._direction = self._get_direction(parts[3])
                self._state = Robot_State("intersection")
            elif parts[0] == "GDIR": # Direction update
                self._direction = self._get_direction(parts[1])
            elif parts[0] == "ACKG": # "GOTO" acknowledgement
                self._state = Robot_State("move")
        except IndexError:
            # Ignore incomplete messages.
            return

        print("Arduino: {}".format(' '.join(parts)))

        self._check_intersection()

    def _set_direction(self, target_direction, rotate_direction=0):
        # Format as a command "set direction"
        self._serial_connection.write("DIRS {} {}\n".format(self._get_zumo_direction(target_direction), rotate_direction))

    def _goto_waypoint(self, next_waypoint):
        # Format a "GOTO" command for the waypoint.
        self._serial_connection.write("GOTO {} {}\n".format(next_waypoint[0], next_waypoint[1]))

        # Until we receive the ACKG message, assume we are not yet moving but 
        # also do not check for intersections and waypoints again.
        self._state = Robot_State("wait")
        return True

    def _format_speeds(self, left_speed, right_speed, left_forward, right_forward):
        # Although we currently do not support changing speeds in the program, 
        # we can at least not completely break the command for now.
        output = super(Robot_Vehicle_Arduino_Full, self)._format_speeds(left_speed, right_speed, left_forward, right_forward)
        # Format as a command "set speeds".
        return "SPDS {}".format(output)
