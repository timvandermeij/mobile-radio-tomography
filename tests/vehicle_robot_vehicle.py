import math
from dronekit import LocationLocal, LocationGlobal, VehicleMode
from mock import patch, MagicMock
from ..core.Threadable import Threadable
from ..core.WiringPi import WiringPi
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
        self.vehicle._line_follower = MagicMock()

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

    def test_init(self):
        self.assertEqual(self.vehicle.arguments, self.arguments)
        self.assertEqual(self.vehicle._home_location, (0, 0))
        self.assertEqual(self.vehicle._direction, Line_Follower_Direction.UP)
        self.assertIsInstance(self.vehicle._state, Robot_State)
        self.assertEqual(self.vehicle._state.name, "intersection")
        self._setup_line_follower_mock.assert_called_once_with(self.thread_manager, self.usb_manager)

        self.assertFalse(self.vehicle.use_simulation)
        with self.assertRaises(NotImplementedError):
            self.vehicle.set_speeds(0.1, 0.2,
                                    left_forward=False, right_forward=True)

    def test_home_location(self):
        self.vehicle.home_location = LocationLocal(1.0, 2.0, 4.0)
        self.assertEqual(self.vehicle._home_location, (1, 2))

    def test_home_location_global(self):
        with patch('sys.stdout'):
            self.vehicle.home_location = LocationGlobal(3.0, 6.0, 1.2)
            self.assertEqual(self.vehicle._home_location, (3, 6))

            self.vehicle.add_waypoint(LocationGlobal(4.0, 8.0, 6.4))
            self.assertEqual(self.vehicle._waypoints, [(4, 8)])

    def test_setup(self):
        self.vehicle.setup()
        self.assertIsInstance(self.vehicle._wiringpi, WiringPi)

    def test_setup_line_follower(self):
        self._line_follower_patcher.stop()

        with self.assertRaises(NotImplementedError):
            self.vehicle._setup_line_follower(self.thread_manager,
                                              self.usb_manager)

        self.vehicle._line_follower_class = object
        with self.assertRaises(TypeError):
            self.vehicle._setup_line_follower(self.thread_manager,
                                              self.usb_manager)

        self.vehicle._line_follower_class = Line_Follower_Arduino
        self.vehicle._setup_line_follower(self.thread_manager,
                                          self.usb_manager)
        self.assertIsInstance(self.vehicle._line_follower,
                              Line_Follower_Arduino)

        # Restart the patcher because it cannot be stopped twice.
        self._line_follower_patcher.start()

    @patch('thread.start_new_thread')
    def test_loop(self, thread_mock):
        self.vehicle.activate()
        self.assertTrue(self.vehicle.armed)
        self.vehicle._line_follower.activate.assert_called_once_with()
        thread_mock.assert_called_once_with(self.vehicle._state_loop, ())

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
                state_mock.assert_called_once_with()
                interrupt_mock.assert_not_called()

                self.assertFalse(self.vehicle.armed)
                self.vehicle._line_follower.deactivate.assert_called_once_with()

    @patch.object(Robot_Vehicle, 'set_speeds')
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
        set_speeds_mock.assert_called_once_with(0.4, 0.4)

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
    def test_check_state_turn(self, set_speeds_mock):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.speed = 0.3

        # Start turning at an intersection
        set_speeds_mock.reset_mock()
        new_waypoint = LocationLocal(0.0, 1.0, 0.0)
        self.vehicle.simple_goto(new_waypoint)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "rotate")
        self.assertEqual(self.vehicle._state.current_direction, Line_Follower_Direction.UP)
        self.assertEqual(self.vehicle._state.target_direction, Line_Follower_Direction.RIGHT)
        self.assertEqual(self.vehicle._state.rotate_direction, 1)
        set_speeds_mock.assert_called_once_with(0.2, 0.2,
                                                left_forward=True,
                                                right_forward=False)
        self.assertFalse(self.vehicle.is_current_location_valid())
        self.assertEqual(self.vehicle.attitude.yaw, 0.0)

        # Finish turning at an intersection
        set_speeds_mock.reset_mock()
        self.vehicle.line_follower_callback("diverged", "right")
        self.vehicle._line_follower.set_state.assert_called_with(Line_Follower_State.AT_INTERSECTION)
        self.assertEqual(self.vehicle._state.current_direction, Line_Follower_Direction.RIGHT)
        self.vehicle._check_state()
        self.assertEqual(self.vehicle._state.name, "intersection")
        set_speeds_mock.assert_called_once_with(0, 0)
        self.assertEqual(self.vehicle._direction, Line_Follower_Direction.RIGHT)
        self.vehicle._line_follower.set_direction.assert_called_once_with(Line_Follower_Direction.RIGHT)
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
    def test_armed_mode(self, thread_mock):
        self.assertFalse(self.vehicle.armed)

        self.vehicle.armed = True
        self.vehicle.armed = True
        self.assertTrue(self.vehicle.armed)
        # The thread is only started once.
        self.assertEqual(thread_mock.call_count, 1)

        self.vehicle.mode = VehicleMode("GUIDED")
        self.assertEqual(self.vehicle.mode.name, "GUIDED")
        self.vehicle.mode = VehicleMode("RTL")
        self.assertEqual(self.vehicle.mode.name, "RTL")
        self.assertEqual(self.vehicle._waypoints, [(0, 0)])
        self.vehicle.mode = VehicleMode("HALT")
        self.assertFalse(self.vehicle.armed)

    @patch.object(Robot_Vehicle, '_set_direction')
    def test_yaw(self, direction_mock):
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

            self.vehicle._direction = direction
            self.assertEqual(self.vehicle.attitude.yaw, yaw)

        with self.assertRaises(ValueError):
            self.vehicle._direction = -1
            dummy = self.vehicle.attitude.yaw

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

    @patch.object(Robot_Vehicle, 'set_rotate')
    def test_direction(self, rotate_mock):
        self.vehicle._direction = Line_Follower_Direction.UP
        self.vehicle._set_direction(Line_Follower_Direction.UP)
        self.assertEqual(self.vehicle._state.name, "intersection")
        rotate_mock.assert_not_called()

        self.vehicle._set_direction(Line_Follower_Direction.LEFT)
        self.assertEqual(self.vehicle._state.name, "rotate")
        self.assertEqual(self.vehicle._state.current_direction, Line_Follower_Direction.UP)
        self.assertEqual(self.vehicle._state.target_direction, Line_Follower_Direction.LEFT)
        self.assertEqual(self.vehicle._state.rotate_direction, -1)
        self.vehicle._line_follower.set_state.assert_called_once_with(Line_Follower_State.AT_INTERSECTION)
        rotate_mock.assert_called_once_with(-1)

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
