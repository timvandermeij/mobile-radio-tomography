import RPIO
import RPi.GPIO
from Robot_Vehicle import Robot_Vehicle
from ..location.Line_Follower_Raspberry_Pi import Line_Follower_Raspberry_Pi

class Robot_Vehicle_Raspberry_Pi(Robot_Vehicle):
    """
    Robot vehicle that is directly connected to a Raspberry Pi.
    """

    _line_follower_class = Line_Follower_Raspberry_Pi

    def __init__(self, arguments, geometry):
        super(Robot_Vehicle_Raspberry_Pi, self).__init__(arguments, geometry)

        self.settings = arguments.get_settings("vehicle_robot_raspberry_pi")

        # Motor direction pins (LOW = forward, HIGH = backward)
        self._direction_pins = self.settings.get("direction_pins")
        # Motor speed pins (PWM values)
        self._speed_pins = self.settings.get("speed_pins")

        # PWM range for both motors (minimum and maximum values)
        self._speed_pwms = self.settings.get("speed_pwms")
        # Speed range for both motors in m/s
        self._speeds = self.settings.get("speeds")

        # Servo objects corresponding to the speed PWM pins of both motors.
        # First item is left motor, second item is right motor.
        self._speed_servos = []

    def setup(self):
        # Initialize the RPi.GPIO module. Doing it this way instead of using
        # an alias during import allows unit tests to access it too.
        self.gpio = RPi.GPIO

        # Disable warnings about pins being in use.
        self.gpio.setwarnings(False)

        # Use board numbering which corresponds to the pin numbers on the
        # P1 header of the board.
        self.gpio.setmode(self.gpio.BOARD)

        for pin in self._direction_pins:
            self.gpio.setup(pin, self.gpio.OUT)

        self._speed_servos = [Servo(pin, self._speeds, self._speed_pwms) for pin in self._speed_pins]

    def set_speeds(left_speed, right_speed, left_forward=True, right_forward=True):
        for i, speed in [(0, left_speed), (1, right_speed)]:
            pwm = self._speed_servos[i].get_pwm(speed)
            self.set_servo(self._speed_servos[i], pwm)

        for i, forward in [(0, left_forward), (1, right_forward)]:
            # LOW value is forward, HIGH is backward.
            self.gpio.output(self._direction_pins[i], not forward)

    @property
    def speed(self):
        # Take the maximum speed for now; in any event that they are different, 
        # we would not have any accurate speed ratings for now.
        return max(servo.get_value() for servo in self._speed_servos)

    @speed.setter
    def speed(self, value):
        if self._running:
            for servo in self._speed_servos:
                pwm = servo.get_pwm(value)
                self.set_servo(servo, pwm)

    # TODO: Implement velocity. This would need to be based on the current 
    # direction/attitude and the speeds of both motors...

    def set_servo(self, servo, pwm):
        RPIO.PWM.set_servo(servo.pin, pwm)
        servo.set_current_pwm(pwm)
