from argparse import ArgumentParser
from Settings import Settings

class Arguments(object):
    """
    Read settings from command line arguments and pass them along to Settings objects.
    """

    def __init__(self, default_settings_file, argv, **kwargs):
        # Handle settings file manually since we might otherwise eat argument 
        # options that were meant for something else.
        if len(argv) > 0 and not argv[0].startswith('-'):
            self.settings_file = argv.pop(0)
        else:
            self.settings_file = default_settings_file

        self.argv = argv
        # We disable help here so that partial parses do not yet respond to 
        # --help. After all the settings files have registered themselves in 
        # the Arguments handler, we can display help for all the groups using 
        # Arguments.check_help.
        self.parser = ArgumentParser(add_help=False, **kwargs)
        self.groups = {}

    def get_settings(self, group):
        """
        Retrieve the Settings object or create it if it did not exist yet.

        This returns a Settings object that may have its settings overridden with arguments from the input.
        """

        if group in self.groups:
            return self.groups[group]

        settings = Settings(self.settings_file, group)
        self._parse_settings(group, settings)
        self.groups[group] = settings
        return self.groups[group]

    def _parse_settings(self, group, settings):
        self._add_arguments(group, settings)
        self._fill_settings(settings)

    def _add_arguments(self, group, settings):
        """
        Register argument specifications in the argument parser for the Settings group.
        """

        group = self.parser.add_argument_group(group)
        for key, value in settings.get_all():
            kw = {
                "dest": key,
                "default": value
            }
            if isinstance(value, list):
                kw["nargs"] = "?"
                if len(value) > 0:
                    kw["type"] = type(value[0])
            elif value is not None:
                kw["type"] = type(value)

            group.add_argument("--{}".format(key.replace('_','-')), **kw)

    def _fill_settings(self, settings):
        """
        Parse arguments from the input and pass any options related to the current Settings object to it.
        """

        args, self.argv = self.parser.parse_known_args(self.argv)
        for key, _ in settings.get_all():
            settings.set(key, args.__dict__[key])

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
