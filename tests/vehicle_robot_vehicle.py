import math
from dronekit import LocationLocal, LocationGlobal, LocationGlobalRelative, VehicleMode
from mock import patch, MagicMock
from ..bench.Method_Coverage import covers
from ..core.Threadable import Threadable
from ..core.WiringPi import WiringPi
from ..geometry.Geometry_Spherical import Geometry_Spherical
from ..location.Line_Follower import Line_Follower_Direction, Line_Follower_State
from ..location.Line_Follower_Arduino import Line_Follower_Arduino
from ..trajectory.Servo import Servo, Interval
from ..vehicle.Robot_Vehicle import Robot_State, Robot_Vehicle
from core_wiringpi import WiringPiTestCase
from vehicle import VehicleTestCase

class RobotVehicleTestCase(VehicleTestCase, WiringPiTestCase):
    def setUp(self):
        self._line_follower_patcher = patch.object(Robot_Vehicle,
                                                   "_setup_line_follower")
        self._setup_line_follower_mock = self._line_follower_patcher.start()

        super(RobotVehicleTestCase, self).setUp()

        if self._setup_line_follower_mock.called:
            self._line_follower = MagicMock()
            self.vehicle._line_follower = self._line_follower

    def tearDown(self):
        super(RobotVehicleTestCase, self).tearDown()
        self._line_follower_patcher.stop()

class TestVehicleRobotVehicle(RobotVehicleTestCase):
    def setUp(self):
        self.set_arguments([
            "--home-location", "0", "0", "--home-direction", "0",
            "--diverged-speed", "0.5", "--rotate-speed", "0.2"
        ], vehicle_class="Robot_Vehicle")
        super(TestVehicleRobotVehicle, self).setUp()

    def test_initialization(self):
        self.assertEqual(self.vehicle.arguments, self.arguments)
        self.assertEqual(self.vehicle._home_location, (0, 0))
        self.assertEqual(self.vehicle._direction, Line_Follower_Direction.UP)
        self.assertIsInstance(self.vehicle._state, Robot_State)
        self.assertEqual(self.vehicle._state.name, "intersection")
        self._setup_line_follower_mock.assert_called_once_with(self.import_manager,
                                                               self.thread_manager,
                                                               self.usb_manager)

    def test_set_speeds(self):
        with self.assertRaises(NotImplementedError):
            self.vehicle.set_speeds(0.1, 0.2,
                                    left_forward=False, right_forward=True)

    def test_use_simulation(self):
        self.assertFalse(self.vehicle.use_simulation)

    def test_home_location(self):
        self.vehicle.home_location = LocationLocal(1.0, 2.0, 4.0)
        self.assertEqual(self.vehicle._home_location, (1, 2))
        self.assertEqual(self.vehicle.home_location,
                         LocationLocal(1.0, 2.0, 0.0))

    def test_home_location_global(self):
        with patch.object(self.vehicle, "_geometry", new=Geometry_Spherical()):
            self.vehicle.home_location = LocationGlobal(3.0, 6.0, 1.2)
            self.assertEqual(self.vehicle._home_location, (3, 6))
            self.assertEqual(self.vehicle.home_location,
                             LocationGlobalRelative(3.0, 6.0, 0.0))

            self.vehicle.add_waypoint(LocationGlobal(4.0, 8.0, 6.4))
            self.assertEqual(self.vehicle._waypoints, [(4, 8)])

    def test_setup(self):
        self.vehicle.setup()
        self.assertIsInstance(self.vehicle._wiringpi, WiringPi)

    def test_setup_line_follower(self):
        self._line_follower_patcher.stop()

        with self.assertRaises(NotImplementedError):
            self.vehicle._setup_line_follower(self.import_manager,
                                              self.thread_manager,
                                              self.usb_manager)

        self.vehicle._line_follower_class = "AStar"
        with self.assertRaises(TypeError):
            self.vehicle._setup_line_follower(self.import_manager,
                                              self.thread_manager,
                                              self.usb_manager)

        self.vehicle._line_follower_class = "Line_Follower_Arduino"
        self.vehicle._setup_line_follower(self.import_manager,
                                          self.thread_manager,
                                          self.usb_manager)
        self.assertIsInstance(self.vehicle._line_follower,
                              Line_Follower_Arduino)

        # Restart the patcher because it cannot be stopped twice.
        self._line_follower_patcher.start()

    @patch('thread.start_new_thread')
    def test_activate(self, thread_mock):
        # Activating arms the vehicle and starts the threads.
        self.vehicle.activate()
        self.assertTrue(self.vehicle.armed)
        self._line_follower.activate.assert_called_once_with()
        thread_mock.assert_called_once_with(self.vehicle._state_loop, ())

        self._line_follower.activate.reset_mock()
        thread_mock.reset_mock()

        # Activating a vehicle when it is armed does not activate it again.
        self.vehicle.activate()
        self._line_follower.activate.assert_not_called()
        thread_mock.assert_not_called()

    @patch('thread.start_new_thread')
    def test_deactivate(self, thread_mock):
        self.vehicle.activate()
        self.vehicle.deactivate()
        self._line_follower.deactivate.assert_called_once_with()
        self.assertFalse(self.vehicle.armed)

        # Deactivating a vehicle when it is not armed does not do anything.
        self._line_follower.deactivate.reset_mock()
        self.vehicle.deactivate()
        self._line_follower.deactivate.assert_not_called()

    @patch('thread.start_new_thread')
    def test_mode(self, thread_mock):
        self.vehicle.activate()
        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")

        self.vehicle.mode = VehicleMode("RTL")
        self.assertEqual(self.vehicle.mode.name, "RTL")
        self.assertEqual(self.vehicle._waypoints, [(0, 0)])

        self.vehicle.mode = VehicleMode("HALT")
        self.assertEqual(self.vehicle.mode.name, "HALT")
        self.assertFalse(self.vehicle.armed)

        self.vehicle.mode = VehicleMode("AUTO")
        self.assertEqual(self.vehicle.mode.name, "AUTO")
        self.assertTrue(self.vehicle.armed)

    @patch('thread.start_new_thread')
    def test_pause(self, thread_mock):
        self.vehicle.activate()
        self.vehicle.mode = VehicleMode("AUTO")

        self.vehicle.pause()
        self.assertEqual(self.vehicle.mode.name, "HALT")
        self.assertFalse(self.vehicle.armed)

        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.assertTrue(self.vehicle.armed)

    @patch('thread.start_new_thread')
    def test_unpause(self, thread_mock):
        self.vehicle.activate()
        self.vehicle.mode = VehicleMode("AUTO")

        self.vehicle.pause()
        self.vehicle.unpause()

        self.assertEqual(self.vehicle.mode.name, "AUTO")
        self.assertTrue(self.vehicle.armed)

        # Changing the mode unpauses automatically.
        self.vehicle.pause()
        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.assertTrue(self.vehicle.armed)

        # We cannot unpause a vehicle twice.
        with self.assertRaises(RuntimeError):
            self.vehicle.unpause()

    @patch('thread.start_new_thread')
    def test_state_loop(self, thread_mock):
        self.vehicle.activate()

        with patch.object(Threadable, 'interrupt') as interrupt_mock:
            with patch.object(Robot_Vehicle, '_check_state') as state_mock:
                state_mock.configure_mock(side_effect=RuntimeError)

                self.vehicle._state_loop()
                state_mock.assert_called_once_with()
                interrupt_mock.assert_called_once_with()

                interrupt_mock.reset_mock()
                state_mock.reset_mock()
                state_mock.configure_mock(side_effect=self.vehicle.deactivate)

                self.vehicle._state_loop()
                self.assertTrue(state_mock.call_count > 0)
                interrupt_mock.assert_not_called()

                self.assertFalse(self.vehicle.armed)
                self._line_follower.deactivate.assert_called_once_with()

    @patch.object(Robot_Vehicle, 'set_speeds')
    @covers("is_current_location_valid")
    def test_check_state_default(self, set_speeds_mock):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.speed = 0.3

        # Test default state: No changes
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, -1)
        self.assertEqual(self.vehicle._waypoints, [])
        self.assertFalse(self.vehicle.is_current_location_valid())
        self.assertEqual(self.vehicle.attitude.yaw, 0.0)

    @patch.object(Robot_Vehicle, 'set_speeds')
    @covers(["is_current_location_valid", "line_follower_callback", "location"])
    def test_check_state_diverge(self, set_speeds_mock):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.speed = 0.3
        self.vehicle._armed = True

        # Test adding a waypoint and moving to it.
        waypoint = LocationLocal(1.0, 0.0, 0.0)
        self.vehicle.add_waypoint(waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(1, 0)])
        self.assertEqual(self.vehicle.get_waypoint(), waypoint)
        self.assertEqual(self.vehicle._state.name, "move")
        set_speeds_mock.assert_called_once_with(0.3, 0.3)
        self.assertTrue(self.vehicle._is_moving())
        self.assertFalse(self.vehicle.is_current_location_valid())

        # Test diverged state
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("diverged", "left")
        self.assertIsNotNone(self.vehicle._last_diverged_time)
        set_speeds_mock.assert_called_once_with(0.5 * 0.3, 0.3 + 0.5 * 0.3)

        # Done diverging
        set_speeds_mock.reset_mock()
        self.vehicle._last_diverged_time = 0
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0.3, 0.3)

        # Change speed
        set_speeds_mock.reset_mock()
        self.vehicle.speed = 0.4
        set_speeds_mock.assert_called_once_with(0.4, 0.4,
                                                left_forward=True,
                                                right_forward=True)

        # Reached the waypoint intersection
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("intersection", (0, 1))
        self.assertTrue(self.vehicle._at_current_waypoint())
        self.assertEqual(self.vehicle._state.name, "intersection")
        self.assertEqual(self.vehicle.location, waypoint)
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0, 0)
        self.assertTrue(self.vehicle.is_current_location_valid())

        # AUTO mode keeps standing still.
        self.vehicle.mode = VehicleMode("AUTO")
        set_speeds_mock.reset_mock()
        self.vehicle._check_state()
        set_speeds_mock.assert_called_once_with(0, 0)

    @patch.object(Robot_Vehicle, 'set_speeds')
    @covers(["is_current_location_valid", "line_follower_callback"])
    def test_check_state_turn(self, set_speeds_mock):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.speed = 0.3

        # Start turning at an intersection
        set_speeds_mock.reset_mock()
        new_waypoint = LocationLocal(0.0, 1.0, 0.0)
        self.vehicle.simple_goto(new_waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "rotate")
        self.assertEqual(self.vehicle._state.current_direction,
                         Line_Follower_Direction.UP)
        self.assertEqual(self.vehicle._state.target_direction,
                         Line_Follower_Direction.RIGHT)
        self.assertEqual(self.vehicle._state.rotate_direction, 1)
        set_speeds_mock.assert_called_once_with(0.2, 0.2,
                                                left_forward=True,
                                                right_forward=False)
        self.assertFalse(self.vehicle.is_current_location_valid())
        self.assertEqual(self.vehicle.attitude.yaw, 0.0)

        # Finish turning at an intersection. When the line follower detects 
        # that we are diverging during rotation at the same side as the 
        # rotation direction, then it means we detected another line.
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("diverged", "right")
        current_state = Line_Follower_State.AT_INTERSECTION
        direction = Line_Follower_Direction.RIGHT
        self._line_follower.set_state.assert_called_with(current_state)
        self.assertEqual(self.vehicle._state.current_direction, direction)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "intersection")
        set_speeds_mock.assert_called_once_with(0, 0)
        self.assertEqual(self.vehicle._direction, direction)
        self._line_follower.set_direction.assert_called_once_with(direction)
        self.assertEqual(self.vehicle.attitude.yaw, 0.5 * math.pi)

        # Moving to next intersection
        set_speeds_mock.reset_mock()
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.assertEqual(self.vehicle._waypoints, [(0, 1)])
        self.assertEqual(self.vehicle.get_waypoint(), new_waypoint)
        self.assertEqual(self.vehicle._state.name, "move")
        set_speeds_mock.assert_called_once_with(0.3, 0.3)

    @patch('thread.start_new_thread')
    def test_armed(self, thread_mock):
        self.assertFalse(self.vehicle.armed)

        self.vehicle.armed = True
        self.vehicle.armed = True
        self.assertTrue(self.vehicle.armed)
        # The thread is only started once.
        self.assertEqual(thread_mock.call_count, 1)

        self.vehicle.armed = False
        self.assertFalse(self.vehicle.armed)

    def test_add_waypoint(self):
        self.vehicle.add_waypoint(LocationLocal(4.0, 5.0, 0.0))
        self.assertEqual(self.vehicle._waypoints, [(4, 5)])

    def test_add_wait(self):
        self.vehicle.add_wait()
        self.assertEqual(self.vehicle._waypoints, [None])
        self.assertTrue(self.vehicle._is_waypoint(0))
        self.assertEqual(self.vehicle.count_waypoints(), 1)
        self.assertIsNone(self.vehicle.get_waypoint())

    def test_is_wait(self):
        self.vehicle.add_waypoint(LocationLocal(4.0, 5.0, 0.0))
        self.vehicle.set_next_waypoint()
        self.assertFalse(self.vehicle.is_wait())

        self.vehicle.add_wait()
        self.vehicle.set_next_waypoint()
        self.assertTrue(self.vehicle.is_wait())

    def test_clear_waypoints(self):
        self.vehicle.add_waypoint(LocationLocal(4.0, 5.0, 0.0))
        self.vehicle.add_wait()
        self.vehicle.clear_waypoints()
        self.assertEqual(self.vehicle._waypoints, [])

    def test_get_waypoint(self):
        loc = LocationLocal(4.0, 5.0, 0.0)
        self.vehicle.add_waypoint(loc)
        self.vehicle.set_next_waypoint()
        self.assertTrue(self.vehicle._is_waypoint(0))
        self.assertEqual(self.vehicle.get_waypoint(), loc)
        self.assertEqual(self.vehicle.get_waypoint(0), loc)
        self.assertIsNone(self.vehicle.get_waypoint(1))

    def test_count_waypoints(self):
        self.vehicle.add_waypoint(LocationLocal(4.0, 5.0, 0.0))
        self.vehicle.add_wait()
        self.assertEqual(self.vehicle.count_waypoints(), 2)

    def test_get_next_waypoint(self):
        self.vehicle.set_next_waypoint()
        self.assertEqual(self.vehicle.get_next_waypoint(), 0)
        self.vehicle.set_next_waypoint()
        self.assertEqual(self.vehicle.get_next_waypoint(), 1)

    def test_set_next_waypoint(self):
        self.vehicle.set_next_waypoint()
        self.assertEqual(self.vehicle._current_waypoint, 0)
        self.vehicle.set_next_waypoint(waypoint=2)
        self.assertEqual(self.vehicle._current_waypoint, 2)

    def test_simple_goto(self):
        self.vehicle.simple_goto(LocationLocal(5.0, 6.0, 0.0))
        self.assertEqual(self.vehicle._waypoints, [(5, 6)])

    def test_speed(self):
        self.vehicle.speed = 0.2
        self.assertEqual(self.vehicle.speed, 0.2)

        # Negative speeds are converted.
        self.vehicle.speed = -0.4
        self.assertEqual(self.vehicle.speed, 0.4)

    def test_velocity(self):
        self.vehicle.speed = 0.3
        expected_velocities = {
            Line_Follower_Direction.UP: [0.3, 0, 0],
            Line_Follower_Direction.RIGHT: [0, 0.3, 0],
            Line_Follower_Direction.DOWN: [-0.3, 0, 0],
            Line_Follower_Direction.LEFT: [0, -0.3, 0]
        }
        for direction, velocity in expected_velocities.iteritems():
            self.vehicle._direction = direction
            self.assertEqual(self.vehicle.velocity, velocity)

        with self.assertRaises(ValueError):
            self.vehicle._direction = -1
            dummy = self.vehicle.velocity

        with self.assertRaises(ValueError):
            self.vehicle.velocity = [0.2, 0.25, 0]

        self.vehicle.velocity = [0, 0, 0]
        self.assertEqual(self.vehicle.speed, 0.0)

        self.vehicle.velocity = [0, 0.5, 0]
        self.assertEqual(self.vehicle.speed, 0.5)

    @patch.object(Robot_Vehicle, "_set_direction")
    def test_attitude(self, direction_mock):
        expected_yaws = {
            Line_Follower_Direction.UP: 0.0,
            Line_Follower_Direction.RIGHT: 0.5 * math.pi,
            Line_Follower_Direction.DOWN: math.pi,
            Line_Follower_Direction.LEFT: 1.5 * math.pi
        }
        for direction, yaw in expected_yaws.iteritems():
            self.vehicle._direction = direction
            self.assertEqual(self.vehicle.attitude.yaw, yaw)

        with self.assertRaises(ValueError):
            self.vehicle._direction = -1
            dummy = self.vehicle.attitude.yaw

    @patch.object(Robot_Vehicle, "_set_direction")
    def test_set_yaw(self, direction_mock):
        expected_yaws = {
            Line_Follower_Direction.UP: 0.0,
            Line_Follower_Direction.RIGHT: 0.5 * math.pi,
            Line_Follower_Direction.DOWN: math.pi,
            Line_Follower_Direction.LEFT: 1.5 * math.pi
        }
        for direction, yaw in expected_yaws.iteritems():
            direction_mock.reset_mock()
            self.vehicle.set_yaw(yaw)
            direction_mock.assert_called_once_with(direction, 1)

        # Handle extra arguments for `relative` and `direction`.
        direction_mock.reset_mock()
        self.vehicle._direction = Line_Follower_Direction.DOWN
        self.vehicle.set_yaw(0.5 * math.pi, relative=True, direction=-1)
        direction_mock.assert_called_once_with(Line_Follower_Direction.LEFT, -1)

        # Ignore yaw changes while moving.
        direction_mock.reset_mock()
        self.vehicle._state = Robot_State("move")
        self.vehicle.set_yaw(1.5 * math.pi)
        direction_mock.assert_not_called()

    @patch.object(Robot_Vehicle, "set_rotate")
    def test_set_direction(self, set_rotate_mock):
        current_direction = Line_Follower_Direction.UP
        target_direction = Line_Follower_Direction.LEFT
        expected_state = Line_Follower_State.AT_INTERSECTION

        self.vehicle._direction = current_direction
        self.vehicle._set_direction(current_direction)
        self.assertEqual(self.vehicle._state.name, "intersection")
        set_rotate_mock.assert_not_called()

        self.vehicle._set_direction(target_direction)
        self.assertEqual(self.vehicle._state.name, "rotate")
        self.assertEqual(self.vehicle._state.current_direction, current_direction)
        self.assertEqual(self.vehicle._state.target_direction, target_direction)
        self.assertEqual(self.vehicle._state.rotate_direction, -1)
        self._line_follower.set_state.assert_called_once_with(expected_state)
        set_rotate_mock.assert_called_once_with(-1)

    @patch.object(Robot_Vehicle, "set_speeds")
    def test_set_rotate(self, set_speeds_mock):
        self.vehicle.set_rotate(1)
        set_speeds_mock.assert_called_once_with(0.2, 0.2, left_forward=True,
                                                right_forward=False)

        set_speeds_mock.reset_mock()
        self.vehicle.set_rotate(-1)
        set_speeds_mock.assert_called_once_with(0.2, 0.2, left_forward=False,
                                                right_forward=True)
        
    def test_next_direction(self):
        self.vehicle._direction = Line_Follower_Direction.UP
        expected_directions = {
            (0, 0): Line_Follower_Direction.UP,
            (1, 0): Line_Follower_Direction.UP,
            (-1, 0): Line_Follower_Direction.DOWN,
            (0, 1): Line_Follower_Direction.RIGHT,
            (0, -1): Line_Follower_Direction.LEFT,
            (1, 1): Line_Follower_Direction.UP,
            (-1, -1): Line_Follower_Direction.LEFT
        }
        for waypoint, direction in expected_directions.iteritems():
            self.assertEqual(self.vehicle._next_direction(waypoint), direction)

        self.vehicle._direction = Line_Follower_Direction.RIGHT
        self.assertEqual(self.vehicle._next_direction((1, 1)),
                         Line_Follower_Direction.RIGHT)
        self.assertEqual(self.vehicle._next_direction((1, 0)),
                         Line_Follower_Direction.UP)

    def test_set_servo(self):
        self.vehicle.setup()

        servo_mock = MagicMock(spec=Servo, pin=7, pwm=Interval(0, 2000))
        wiringpi_mock = MagicMock()
        wiringpi = {
            'is_raspberry_pi': True,
            'module': wiringpi_mock,
        }
        self.vehicle._wiringpi = MagicMock(spec=WiringPi, **wiringpi)

        self.vehicle.set_servo(servo_mock, 1000)
        self.assertIn(7, self.vehicle._servo_pins)
        wiringpi_mock.softPwmCreate.assert_called_once_with(7, 1000, 2000)
        wiringpi_mock.softPwmWrite.assert_called_once_with(7, 1000)
        servo_mock.set_current_pwm.assert_called_once_with(1000)
