import importlib
import string
from argparse import ArgumentParser
from functools import partial
from Settings import Settings

class Arguments(object):
    """
    Read settings from command line arguments and pass them along to Settings objects.
    """

    def __init__(self, default_settings_file, argv,
                 defaults_file=Settings.DEFAULTS_FILE, **kwargs):
        # Handle settings file manually since we might otherwise eat argument 
        # options that were meant for something else.
        if len(argv) > 0 and not argv[0].startswith('-'):
            self.settings_file = argv.pop(0)
        else:
            self.settings_file = default_settings_file

        self.argv = argv
        self.defaults_file = defaults_file
        # We disable help here so that partial parses do not yet respond to 
        # --help. After all the settings files have registered themselves in 
        # the Arguments handler, we can display help for all the groups using 
        # Arguments.check_help.
        self.parser = ArgumentParser(add_help=False, **kwargs)
        self.groups = {}
        self._type_names = {
            "int": int,
            "float": float,
            "bool": bool,
            "string": str,
            "file": str,
            "class": str,
            "list": list,
            "tuple": tuple
        }

    def get_settings(self, group):
        """
        Retrieve the Settings object or create it if it did not exist yet.

        This returns a Settings object that may have its settings overridden with arguments from the input.
        """

        if group in self.groups:
            return self.groups[group]

        settings = Settings(self.settings_file, group,
                            arguments=self, defaults_file=self.defaults_file)

        self._parse_settings(group, settings)
        self.groups[group] = settings
        return self.groups[group]

    def _parse_settings(self, group, settings):
        self._add_arguments(group, settings)
        self._fill_settings(settings)

    def _get_keys(self, location):
        """
        Retrieve a list of option choices from a module or a (nested) attribute.
        """

        data = importlib.import_module(location[0])
        for attr in location[1:]:
            data = getattr(data, attr)

        if isinstance(data, dict):
            return data.keys()

        if hasattr(data, "__all__"):
            return data.__all__

        return data.__dict__.keys()

    def _make_help(self, key):
        parts = key.split('_')
        return ' '.join([parts[0].title()] + parts[1:])

    def _add_arguments(self, group, settings):
        """
        Register argument specifications in the argument parser for the Settings group.
        """

        argument_group = self.parser.add_argument_group("{} ({})".format(settings.name, group))
        for key, info in settings.get_info():
            # Create arguments dictionary for the argument parser.
            # Use current value of the setting, since it might have been 
            # overridden by the settings compared to the actual defaults.
            kw = {
                "dest": key,
                "default": info["value"],
                "help": info["help"] if "help" in info else self._make_help(key)
            }
            if "options" in info:
                kw["choices"] = info["options"]
            elif "keys" in info:
                kw["choices"] = self._get_keys(info["keys"])
            elif "module" in info:
                package = __package__.split('.')[0]
                kw["choices"] = self._get_keys(["{}.{}".format(package, info["module"])])

            opt = key.replace('_', '-')
            if info["type"] in ("list", "tuple"):
                kw["nargs"] = info["length"] if "length" in info else "*"
                if "subtype" in info and info["subtype"] in self._type_names:
                    kw["type"] = self._type_names[info["subtype"]]
            elif info["type"] == "bool":
                kw["action"] = "store_true"
                argument_group.add_argument("--{}".format(opt), **kw)

                opt = "no-{}".format(opt)
                kw["help"] = "Disable the setting above"
                kw["action"] = "store_false"
            elif "replace" in info:
                # Create a translation table and bind a function that performs 
                # the translation on input to the type of the argument.
                # This ensures the translation is performed before other checks 
                # (such as allowed choices) are done.
                table = string.maketrans(*info["replace"])
                kw["type"] = partial(lambda table, x: str(x).translate(table), table)
            elif info["type"] in self._type_names:
                kw["type"] = self._type_names[info["type"]]

            argument_group.add_argument("--{}".format(opt), **kw)

    def _fill_settings(self, settings):
        """
        Parse arguments from the input and pass any options related to the current Settings object to it.
        """

        args, self.argv = self.parser.parse_known_args(self.argv)
        for key, info in settings.get_info():
            try:
                value = args.__dict__[key]
                if value is not None and info["type"] in self._type_names:
                    typecast = self._type_names[info["type"]]
                    value = typecast(value)

                settings.set(key, value)
            except ValueError as e:
                self.parser.print_help()
                self.parser.exit(status=1, message=str(e))

    def check_help(self):
        """
        Check whether the input has a --help option and act accordingly if so.

        This should be used after all Settings components have been registered,
        so that help for all settings is available.
        This method will end the program in case a --help argument is given,
        or in case nonexistent arguments are given.
        """

        self.parser.add_argument('-h', '--help', action='help', help="Show this help message and exit")
        self.parser.parse_args(self.argv)
