class Interval(object):
    """
    Small interval range specification.
    """

    def __init__(self, minimum, maximum=None):
        if isinstance(minimum, (list,tuple)):
            if len(minimum) != 2:
                raise ValueError("Must be given an interval specification")
            if maximum is not None:
                raise ValueError("Cannot give both a sequence type and a maximum")

            minimum, maximum = minimum

        self.min = minimum
        self.max = maximum

    @property
    def diff(self):
        return self.max - self.min

class Servo(object):
    """
    Servo class that handles current measurements and performs calculations.
    """

    def __init__(self, pin, angles, pwm=None):
        self.pin = int(pin)
        self.angles = Interval(angles)

        if pwm is None:
            self.pwm = Interval(1000,2000)
        else:
            self.pwm = Interval(pwm)

        self.pwm_factor = self.pwm.diff / float(self.angles.diff)
        self.angle_factor = self.angles.diff / float(self.pwm.diff)

        self.current_pwm = self.pwm.min

    def check_angle(self, angle):
        """
        Check whether the given `angle` is within this servo's constraints.
        """
        if self.angles.min <= angle < self.angles.max:
            return True

        return False

    def get_pin(self):
        """
        Get the servo's pin number.
        """
        return self.pin

    def get_pwm(self, angle=None):
        """
        Get the PWM of a given `angle`, or the current PWM value if no angle is given.
        """
        if angle is None:
            return self.current_pwm

        return self.pwm.min + self.pwm_factor * (angle - self.angles.min)

    def set_current_pwm(self, pwm):
        """
        Store the given `pwm` as the current PWM value.
        """
        self.current_pwm = pwm

    def get_angle(self, pwm=None):
        """
        Calculate the angle belonging to a given `pwm`, or the current PWM if none is given.
        """
        if pwm is None:
            pwm = self.current_pwm

        return self.angles.min + self.angle_factor * (pwm - self.pwm.min)
