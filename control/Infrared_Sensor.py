# TODO: documentation
# TODO: hardware and unit tests

import os
import lirc
import shutil
import sys
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

        self._remote = settings.get("remote")
        self._program = settings.get("program")
        self._buttons = settings.get("buttons")
        self._wait_delay = settings.get("wait_delay")

        self._active = False
        self._event_listeners = {}

        self._configure()

    def _configure(self):
        """
        Configure LIRC to work with the remote specified in the settings file.
        """

        module = self.__class__.__module__
        base_path = os.path.dirname(sys.modules[module].__file__)

        # Check if LIRC is installed.
        if not os.path.isdir("/etc/lirc"):
            raise OSError("LIRC is not installed")

        # Check if the `lircd.conf` file already exists.
        remote_file = "{}.lircd.conf".format(self._remote)
        if os.path.isfile("/etc/lirc/lircd.conf.d/{}".format(remote_file)):
            return

        # Check if the `lircd.conf` file is available in our remotes folder.
        if not os.path.isfile("{}/remotes/{}".format(base_path, remote_file)):
            raise OSError("Remote file '{}' does not exist".format(remote_file))

        # Check if the `lircrc` file is available in our remotes folder.
        configuration_file = "{}.lircrc".format(self._remote)
        if not os.path.isfile("{}/remotes/{}".format(base_path, configuration_file)):
            raise OSError("Configuration file '{}' does not exist".format(configuration_file))

        # Copy the `lircd.conf` file for the remote to the LIRC directory.
        # This way it will be loaded automatically when LIRC is started.
        try:
            shutil.copyfile("{}/remotes/{}".format(base_path, remote_file),
                            "/etc/lirc/lircd.conf.d/{}".format(remote_file))
        except IOError:
            raise OSError("Configuration directory is not writable. Run this as root.")

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
        configuration_file = "remotes/{}.lircrc".format(self._remote)
        lirc.init(self._program, configuration_file, blocking=False)
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
