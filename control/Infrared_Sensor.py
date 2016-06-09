# Core imports
import os
import shutil
import sys
import thread
import time

# Library imports
import pylirc

# Package imports
from ..core.Threadable import Threadable
from ..settings import Arguments, Settings

class Infrared_Sensor(Threadable):
    def __init__(self, settings, thread_manager):
        """
        Initialize the infrared sensor object.
        """

        super(Infrared_Sensor, self).__init__("infrared_sensor", thread_manager)

        if isinstance(settings, Arguments):
            settings = settings.get_settings("infrared_sensor")
        elif not isinstance(settings, Settings):
            raise ValueError("'settings' must be an instance of Settings or Arguments")

        self._settings = settings
        self._remote = self._settings.get("remote")
        self._program = self._settings.get("program")
        self._buttons = self._settings.get("buttons")
        self._wait_delay = self._settings.get("wait_delay")

        module = self.__class__.__module__
        self._base_path = os.path.dirname(sys.modules[module].__file__)

        self._active = False
        self._event_listeners = {}
        self._release_listeners = {}
        self._previous_button = None

        self._configure()

    def _configure(self):
        """
        Configure LIRC to work with the remote specified in the settings file.
        """

        # Check if LIRC is installed.
        if not os.path.isdir("/etc/lirc"):
            raise OSError("LIRC is not installed")

        # Check if the `lircd.conf` file already exists.
        remote_file = "{}.lircd.conf".format(self._remote)
        if os.path.isfile("/etc/lirc/lircd.conf.d/{}".format(remote_file)):
            return

        # Check if the `lircd.conf` file is available in our remotes folder.
        if not os.path.isfile("{}/remotes/{}".format(self._base_path, remote_file)):
            raise OSError("Remote file '{}' does not exist".format(remote_file))

        # Check if the `lircrc` file is available in our remotes folder.
        configuration_file = "{}.lircrc".format(self._remote)
        if not os.path.isfile("{}/remotes/{}".format(self._base_path, configuration_file)):
            raise OSError("Configuration file '{}' does not exist".format(configuration_file))

        # Copy the `lircd.conf` file for the remote to the LIRC directory.
        # This way it will be loaded automatically when LIRC is started.
        try:
            shutil.copyfile("{}/remotes/{}".format(self._base_path, remote_file),
                            "/etc/lirc/lircd.conf.d/{}".format(remote_file))
        except IOError:
            raise OSError("Configuration directory is not writable. Run this as root.")

    def register(self, button, callback, release_callback=None):
        """
        Register an event listener for the infrared sensor. If the button
        configured to match with the given `button` name is pressed on the
        remote control, the `callback` will be called. When it is released
        (which is almost immediate unless the `repeat` configuration is used),
        the `release_callback` is called. The `release_callback` is optional,
        but all callbacks must be callable, otherwise a `ValueError` is raised.
        If a button not known to the settings is given, a `KeyError` is raised.
        """

        if button not in self._buttons:
            raise KeyError("Unknown button provided: '{}'".format(button))

        self._check_callback(button, callback)

        self._event_listeners[button] = callback
        if release_callback is not None:
            self._check_callback(button, release_callback)
            self._release_listeners[button] = release_callback

    def _check_callback(self, button, callback):
        if not hasattr(callback, "__call__"):
            raise ValueError("Invalid callback provided for the '{}' button".format(button))

    def activate(self):
        """
        Activate the infrared sensor.
        """

        super(Infrared_Sensor, self).activate()

        self._active = True
        configuration_file = "{}/remotes/{}.lircrc".format(self._base_path, self._remote)
        pylirc.init(self._program, configuration_file, False)
        thread.start_new_thread(self._loop, ())

    def _loop(self):
        """
        Execute the sensor loop. This runs in a separate thread.
        """

        try:
            while self._active:
                data = pylirc.nextcode()
                self._handle_lirc_code(data)
                time.sleep(self._wait_delay)
        except:
            super(Infrared_Sensor, self).interrupt()

    def _handle_lirc_code(self, data):
        if data is not None:
            button = data[0]
            self._previous_button = button
            if button in self._event_listeners:
                callback = self._event_listeners[button]
                callback()
        elif self._previous_button is not None:
            if self._previous_button in self._release_listeners:
                callback = self._release_listeners[self._previous_button]
                callback()

            self._previous_button = None

    def deactivate(self):
        """
        Deactivate the infrared sensor.
        """

        super(Infrared_Sensor, self).deactivate()

        self._active = False
        pylirc.exit()
