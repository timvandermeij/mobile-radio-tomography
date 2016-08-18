import serial
from dronekit import LocationLocal
from mock import patch
from ..core.Threadable import Threadable
from ..location.Line_Follower import Line_Follower_Direction
from vehicle_robot_vehicle import RobotVehicleTestCase

class TestVehicleRobotVehicleArduinoFull(RobotVehicleTestCase):
    def setUp(self):
        self.set_arguments([
            "--motor-speed-pwms", "0", "2000", "--motor-speeds", "-0.6", "0.6",
            "--home-location", "3", "4", "--home-direction", "2",
            "--activate-delay", "0"
        ], vehicle_class="Robot_Vehicle_Arduino_Full")
        self.set_rpi_patch()
        super(TestVehicleRobotVehicleArduinoFull, self).setUp()

    def test_initialization(self):
        # The `Robot_Vehicle_Arduino_Full` class does not use a line follower.
        self.assertIsNone(self.vehicle._line_follower)

    @patch("thread.start_new_thread")
    def test_activate(self, thread_mock):
        with patch.object(Threadable, "activate"):
            self.vehicle.activate()
            self.assertEqual(self._ttl_device.readline(), "START\n")
            self.assertEqual(self._ttl_device.readline(), "HOME 3 4 S\n")
            thread_mock.assert_any_call(self.vehicle._serial_loop, ())

    @patch("thread.start_new_thread")
    def test_deactivate(self, thread_mock):
        # Activate the vehicle and ignore the startup commands, since we test 
        # them in another test.
        self.vehicle.activate()
        self._ttl_device.readline()
        self._ttl_device.readline()

        self.vehicle.deactivate()
        # Reset signal is at high level on the DTR line, and the connection is 
        # immediately closed.
        self.assertTrue(self.vehicle._serial_connection.dtr)
        self.assertFalse(self.vehicle._serial_connection.isOpen())

    @patch("thread.start_new_thread")
    def test_pause(self, thread_mock):
        # Activate the vehicle and ignore the startup commands, since we test 
        # them in another test.
        self.vehicle.activate()
        self._ttl_device.readline()
        self._ttl_device.readline()

        self.vehicle.pause()
        # An immediate pause command is sent over the connection, and it is not 
        # reset nor closed.
        self.assertEqual(self._ttl_device.read(1), "\x03")
        self.assertFalse(self.vehicle.armed)
        self.assertFalse(self.vehicle._serial_connection.dtr)
        self.assertTrue(self.vehicle._serial_connection.isOpen())

    @patch("thread.start_new_thread")
    def test_unpause(self, thread_mock):
        # Activate the vehicle and ignore the startup commands, since we test 
        # them in another test.
        self.vehicle.activate()
        self._ttl_device.readline()
        self._ttl_device.readline()

        self.vehicle.pause()
        self._ttl_device.read(1)
        self.vehicle.unpause()
        self.assertEqual(self._ttl_device.readline(), "CONT\n")

        with self.assertRaises(RuntimeError):
            self.vehicle.unpause()

    def test_home_location(self):
        loc = LocationLocal(5.0, 6.0, 0.0)
        self.vehicle.home_location = loc
        # We send a "set home location" message to the Arduino.
        self.assertEqual(self._ttl_device.readline(), "HOME 5 6 S\n")
        self.assertEqual(self.vehicle.home_location, loc)

    def test_get_direction(self):
        cases = [
            ('N', Line_Follower_Direction.UP),
            ('E', Line_Follower_Direction.RIGHT),
            ('S', Line_Follower_Direction.DOWN),
            ('W', Line_Follower_Direction.LEFT)
        ]
        for direction, expected in cases:
            self.assertEqual(self.vehicle._get_direction(direction), expected)

        with self.assertRaises(ValueError):
            self.vehicle._get_direction('X')

    def test_get_zumo_direction(self):
        cases = [
            (Line_Follower_Direction.UP, 'N'),
            (Line_Follower_Direction.RIGHT, 'E'),
            (Line_Follower_Direction.DOWN, 'S'),
            (Line_Follower_Direction.LEFT, 'W')
        ]
        for direction, expected in cases:
            self.assertEqual(self.vehicle._get_zumo_direction(direction),
                             expected)

        with self.assertRaises(ValueError):
            self.vehicle._get_zumo_direction(4)

    def test_get_next_location(self):
        cases = [
            (Line_Follower_Direction.UP, (4, 4)),
            (Line_Follower_Direction.RIGHT, (3, 5)),
            (Line_Follower_Direction.DOWN, (2, 4)),
            (Line_Follower_Direction.LEFT, (3, 3))
        ]
        for direction, expected in cases:
            self.vehicle._direction = direction
            self.assertEqual(self.vehicle._get_next_location(), expected)

        with self.assertRaises(ValueError):
            self.vehicle._direction = 4
            self.vehicle._get_next_location()

    def test_check_state(self):
        # `_check_state` always calls `Robot_Vehicle._check_intersection`.
        with patch.object(self.vehicle, "_check_intersection") as check_mock:
            self.vehicle._check_state()
            check_mock.assert_called_once_with()

    def test_serial_loop(self):
        with patch("thread.start_new_thread"):
            self.vehicle.activate()

        with patch.object(self.vehicle, "_read_serial_message") as serial_mock:
            with patch.object(Threadable, "interrupt") as interrupt_mock:
                serial_mock.configure_mock(side_effect=RuntimeError)

                self.vehicle._serial_loop()
                serial_mock.assert_called_once_with()
                interrupt_mock.assert_called_once_with()

                interrupt_mock.reset_mock()
                serial_mock.reset_mock()
                serial_mock.configure_mock(side_effect=self.vehicle.deactivate)

                self.vehicle._serial_loop()
                serial_mock.assert_any_call()
                interrupt_mock.assert_not_called()

                self.assertFalse(self.vehicle.armed)

    def test_read_serial_message(self):
        with patch("thread.start_new_thread"):
            self.vehicle.activate()

        with patch("sys.stdout"):
            # The location and direction states are updated based on the 
            # Arduino "location" message.
            self._ttl_device.write("LOCA 2 3 E\n")
            self.vehicle._read_serial_message()
            self.assertEqual(self.vehicle.location,
                             LocationLocal(2.0, 3.0, 0.0))
            self.assertEqual(self.vehicle._direction,
                             Line_Follower_Direction.RIGHT)
            self.assertEqual(self.vehicle._state.name, "intersection")

            # The direction is updated based on the Arduino "goto direction".
            self._ttl_device.write("GDIR N\n")
            self.vehicle._read_serial_message()
            self.assertEqual(self.vehicle._direction,
                             Line_Follower_Direction.UP)

            # The vehicle state is updated based on the Arduino 
            # "acknowledgement goto" message.
            self.vehicle.add_waypoint(LocationLocal(4.0, 3.0, 0.0))
            self.vehicle.set_next_waypoint()
            self._ttl_device.write("ACKG 4 3\n")
            self.vehicle._read_serial_message()
            self.assertEqual(self.vehicle._state.name, "move")

            # The current location is updated based on the Arduino 
            # "intersection passing" message.
            self._ttl_device.write("PASS 0\n")
            self.vehicle._read_serial_message()
            self.assertEqual(self.vehicle.location,
                             LocationLocal(3.0, 3.0, 0.0))
            self.assertFalse(self.vehicle.is_current_location_valid())

            # Check that the location updates for each "intersection passing" 
            # message, but only becomes valid when we get a "location" message 
            # from the Arduino.
            self._ttl_device.write("PASS 1\n")
            self.vehicle._read_serial_message()
            self.assertEqual(self.vehicle.location,
                             LocationLocal(4.0, 3.0, 0.0))
            self.assertFalse(self.vehicle.is_current_location_valid())

            self._ttl_device.write("LOCA 4 3 N\n")
            self.vehicle._read_serial_message()
            self.assertTrue(self.vehicle.is_current_location_valid())

            # Incomplete messages are ignored.
            self._ttl_device.write("LOCA 999\n")
            self.vehicle._read_serial_message()

    def test_set_direction(self):
        # We send a "set direction" message to the Arduino.
        self.vehicle._set_direction(Line_Follower_Direction.LEFT,
                                    rotate_direction=1)
        self.assertEqual(self._ttl_device.readline(), "DIRS W 1\n")

    def test_goto_waypoint(self):
        # Floating point waypoints are rounded in the "goto location" message 
        # to the Arduino.
        self.assertTrue(self.vehicle._goto_waypoint((4.2, 3.6)))
        self.assertEqual(self._ttl_device.readline(), "GOTO 4 3\n")
        self.assertEqual(self.vehicle._state.name, "wait")

    @patch.object(serial.Serial, "write")
    def test_goto_waypoint_wait(self, write_mock):
        # Wait waypoints are ignored.
        self.assertTrue(self.vehicle._goto_waypoint(None))
        write_mock.assert_not_called()

    def test_set_speeds(self):
        # We send a "set speeds" message with PWM values to the Arduino.
        self.vehicle.set_speeds(0.3, 0.15,
                                left_forward=False, right_forward=True)
        self.assertEqual(self.vehicle._current_speed, (0.3, 0.15, False, True))
        self.assertEqual(self._ttl_device.readline(), "SPDS 500 1250\n")
