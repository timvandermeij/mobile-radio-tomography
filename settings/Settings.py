import os
import json

class Settings(object):
    DEFAULTS_FILE = 'settings/defaults.json'
    settings_files = {}

    @classmethod
    def get_settings(cls, file_name):
        """
        Retrieve the settings from a file name, load the JSON data and 
        unserialize it. We store the settings object statically in this class 
        so that later uses of the same settings file can reuse it.
        """

        if file_name not in cls.settings_files:
            with open(file_name) as data:
                cls.settings_files[file_name] = json.load(data)

        return cls.settings_files[file_name]

    def __init__(self, file_name, component_name,
                 arguments=None, defaults_file=DEFAULTS_FILE):
        if not os.path.isfile(defaults_file):
            raise IOError("File '{}' does not exist.".format(defaults_file))
        if not os.path.isfile(file_name):
            raise IOError("File '{}' does not exist.".format(file_name))

        self.component_name = component_name

        # Read the default settings and the overrides.
        defaults = self.__class__.get_settings(defaults_file)
        settings = self.__class__.get_settings(file_name)
        if self.component_name not in defaults:
            raise KeyError("Component '{}' not found.".format(self.component_name))

        # Fetch information related to the current component from the default 
        # settings, and set the current values of each setting from the 
        # overrides or the defaults.
        self.settings = defaults[self.component_name]["settings"]
        self.name = defaults[self.component_name]["name"]
        for key, data in self.settings.iteritems():
            if key in settings:
                data["value"] = settings[key]
            else:
                data["value"] = data["default"]

        if "parent" in defaults[self.component_name]:
            parent = defaults[self.component_name]["parent"]
            if arguments is not None:
                self.parent = arguments.get_settings(parent)
            else:
                self.parent = Settings(file_name, parent,
                                       defaults_file=defaults_file)
        else:
            self.parent = None

    def get_all(self):
        """
        Retrieve all the settings values for this component.

        This function deliberately does not return inherited values from parent
        components. This helper function should only be used for raw interaction
        with this component only, for example to register arguments for the
        relevant settings keys.

        The returned value is a generator yielding key and current value.
        """

        return ((key, self.settings[key]["value"]) for key in self.settings)

    def get_info(self):
        """
        Retrieve all the settings information for this component.

        The returned value is a generator yielding key and setting data.
        """

        return self.settings.iteritems()

    def keys(self):
        """
        Retrieve all the settings keys for this component.

        The returned value is a generator yielding the key.
        """

        return self.settings.iterkeys()

    def get(self, key):
        if key not in self.settings:
            if self.parent is not None:
                try:
                    return self.parent.get(key)
                except KeyError:
                    pass

            raise KeyError("Setting '{}' for component '{}' not found.".format(key, self.component_name))

        return self.settings[key]["value"]

    def set(self, key, value):
        if key not in self.settings:
            if self.parent is not None:
                try:
                    self.parent.set(key, value)
                    return
                except KeyError:
                    pass

            raise KeyError("Setting '{}' for component '{}' not found.".format(key, self.component_name))

        self.settings[key]["value"] = value
