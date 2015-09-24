import json

class Settings(object):
    def __init__(self, file_name, component_name):
        self.component_name = component_name
        
        with open(file_name) as data:
            settings = json.load(data)
        
        self.settings = None
        for settings_object in settings:
            if settings_object["component"] == self.component_name:
                self.settings = settings_object["settings"]

    def get(self, key):
        if self.settings == None or key not in self.settings:
            raise KeyError("Setting '{}' for component '{}' not found.".format(key, self.component_name))

        return self.settings[key]
