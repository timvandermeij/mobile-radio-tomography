try:
    import RPi.GPIO as GPIO
    import wiringpi
except (ImportError, RuntimeError):
    GPIO = None

class WiringPi(object):
    """
    Wrapper singleton for the wiringpi module.

    This is required because the setup function of wiringPi can only be called
    once. This class also ensures that the wiringpi functions can only be used
    when run on a Raspberry Pi device.
    """

    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            if GPIO is not None:
                wiringpi.wiringPiSetupPhys()

            cls.singleton = super(WiringPi, cls).__new__(cls)

        return cls.singleton

    def __init__(self):
        self._is_raspberry_pi = GPIO is not None

    @property
    def is_raspberry_pi(self):
        return self._is_raspberry_pi

    @property
    def module(self):
        if self._is_raspberry_pi:
            return wiringpi

        return None
