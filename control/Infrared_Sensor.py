# TODO: documentation
# TODO: configuration
# TODO: hardware and unit tests

import lirc
import thread
import time
from ..settings import Arguments, Settings

class Infrared_Sensor(object):
    def __init__(self, settings):
        """
        Initialize the infrared sensor object.
        """

        if isinstance(settings, Arguments):
            settings = settings.get_settings("infrared_sensor")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._program = settings.get("program")
        self._buttons = settings.get("buttons")
        self._wait_delay = settings.get("wait_delay")

        self._active = False
        self._event_listeners = {}

    def register(self, button, callback):
        """
        Register an event listener for the infrared sensor. If the button is
        pressed on the remote control, the callback will be called.
        """

        if button not in self._buttons:
            raise KeyError("Unknown button provided: '{}'".format(button))

        if not hasattr(callback, "__call__"):
            raise ValueError("Invalid callback provided for the '{}' button".format(button))

        self._event_listeners[button] = callback

    def activate(self):
        """
        Activate the infrared sensor.
        """

        self.active = True
        lirc.init(self._program, blocking=False)
        thread.start_new_thread(self._loop, ())

    def _loop(self):
        """
        Execute the sensor loop. This runs in a separate thread.
        """

        while self.active:
            data = lirc.nextcode()
            if len(data) == 1:
                button = data[0]
                if button in self._event_listeners:
                    callback = self._event_listeners[button]
                    callback()

            time.sleep(self._wait_delay)

    def deactivate(self):
        """
        Deactivate the infrared sensor.
        """

        self._active = False
        lirc.deinit()
