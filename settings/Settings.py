import json
import os
import re

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

        data = self.settings[key]

        value = self.check_format(key, data, value)

        # Numerical type-specific: check minimum and maximum value constraint
        if "min" in data and value < data["min"]:
            raise ValueError("Setting '{}' for component '{}' must be at least {}, not {}".format(key, self.component_name, data["min"], value))
        if "max" in data and value > data["max"]:
            raise ValueError("Setting '{}' for component '{}' must be at most {}, not {}".format(key, self.component_name, data["max"], value))

        data["value"] = value

    def make_format_regex(self, format):
        return re.escape(format).replace("\\{\\}", "(.*)")

    def check_format(self, key, data, value):
        # A required value must be nonempty (not None and not a value that 
        # evaluates to false according to its type)
        required = "required" in data and data["required"]
        if required and not value:
            raise ValueError("Setting '{}' for component '{}' must be nonempty, not '{}'".format(key, self.component_name, value))

        # File type: If we have a formatter and have a file name, we can do 
        # multiple things:
        # - For required settings, we ensure that the file exists and matches
        #   the given format. The resulting value will just be the part that is 
        #   filled in the format. We refuse nonexistent or nonconforming files.
        # - For non-required strings, we check whether the file exists. If only
        #   part to be filled in the format is given, we convert the resulting 
        #   value to the full path. We refuse nonexistent files, but full file 
        #   names not conforming to the format are allowed.
        if data["type"] == "file" and "format" in data and value is not None:
            if os.path.isfile(value):
                if required:
                    regex = self.make_format_regex(data["format"])
                    match = re.match(regex, value)
                    if match:
                        return match.group(1)
                    else:
                        raise ValueError("Setting '{}' for component '{}' must match the format '{}', value '{}' does not".format(key, self.component_name, data["format"].format("*"), value))
            else:
                full_value = data["format"].format(value)
                if os.path.isfile(full_value):
                    if not required:
                        return full_value
                else:
                    raise ValueError("Setting '{}' for component '{}' must be given an existing file, not '{}'".format(key, self.component_name, value))

        return value
