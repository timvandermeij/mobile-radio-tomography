import os
import json

class Settings(object):
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

    def __init__(self, file_name, component_name, arguments=None):
        if not os.path.isfile(file_name):
            raise IOError("File '{}' does not exist.".format(file_name))

        self.component_name = component_name

        settings = self.__class__.get_settings(file_name)
        if self.component_name not in settings:
            raise KeyError("Component '{}' not found.".format(self.component_name))

        self.settings = settings[self.component_name]["settings"]
        self.name = settings[self.component_name]["name"]

        if "parent" in settings[self.component_name]:
            if arguments is not None:
                self.parent = arguments.get_settings(settings[self.component_name]["parent"])
            else:
                self.parent = Settings(file_name, settings[self.component_name]["parent"])
        else:
            self.parent = None

    def get_all(self):
        """
        Retrieve all the settings values for this component.

        This function deliberately does not return inherited values from parent components,
        because this helper function should only be used for raw interaction
        with this component only, for example to register arguments for the
        relevant settings keys.
        """

        return self.settings.iteritems()

    def get(self, key):
        if key not in self.settings:
            if self.parent is not None:
                try:
                    return self.parent.get(key)
                except KeyError:
                    pass

            raise KeyError("Setting '{}' for component '{}' not found.".format(key, self.component_name))

        return self.settings[key]

    def set(self, key, value):
        self.settings[key] = value
