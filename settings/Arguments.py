import os
import string
import sys
from argparse import ArgumentParser, HelpFormatter
from copy import copy
from functools import partial
from ..core.Import_Manager import Import_Manager
from Settings import Settings

class ArgumentsHelpFormatter(HelpFormatter):
    """
    A help formatter that can have a list of optional positionals that can only
    appear at the start of the provided argument list.
    """

    def __init__(self, *a, **kw):
        super(ArgumentsHelpFormatter, self).__init__(*a, **kw)
        self._is_positional_section = False

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = "Usage: "

        return super(ArgumentsHelpFormatter, self)._format_usage(usage, actions, groups, prefix)

    def _format_actions_usage(self, actions, groups):
        text = super(ArgumentsHelpFormatter, self)._format_actions_usage(actions, groups)
        if not text:
            return ""

        if isinstance(self._prog, Arguments):
            positional_args = self._prog.get_positional_args()
            pos = ' '.join("[{}]".format(positional["name"]) for positional in positional_args)
            return pos + " " + text

    def start_section(self, heading):
        super(ArgumentsHelpFormatter, self).start_section(heading)
        if heading == Arguments.POSITIONAL_GROUP:
            self._current_section.heading = "Positional arguments"
            self._is_positional_section = True

    def end_section(self):
        super(ArgumentsHelpFormatter, self).end_section()
        self._is_positional_section = False

    def add_arguments(self, actions):
        if self._is_positional_section and isinstance(self._prog, Arguments):
            actions = self._prog.get_positional_actions()

        super(ArgumentsHelpFormatter, self).add_arguments(actions)

class Arguments(object):
    """
    Command line argument handler.

    This class reads settings from positional and optional arguments and passes
    them along to `Settings` objects. It handles incremental parsing, help
    formatting and type conversions.
    """

    POSITIONAL_GROUP = "$positional"

    def __init__(self, default_settings_file, argv, program_name=None,
                 defaults_file=Settings.DEFAULTS_FILE, positionals=None,
                 **kwargs):
        """
        Set up the arguments handler with the supplied configuration.

        The `default_settings_file` is a file name from which we read settings
        overrides. This file name itself can be overridden through a positional
        argument, which, if used, must be at the start of the arguments list
        `argv`. `argv` is a list of command line arguments split on the spaces,
        as provided by `sys.argv[1:]` for example. `program_name` is the name
        of the program, which defaults to `sys.argv[0]` so that it receives the
        Python script file name when it is called as in `python script.py`.

        The `defaults_file` is the settings defaults file, passed through to
        the `Settings` objects. For all purposes within the core, this should
        remain the default, but tests can override this file.

        The `positionals` is a list of dictionary registries for positional
        arguments, as mentioned before. These registries follow a similar
        format as the ones in the components of the defaults JSON file.
        At the very least, a `name` must be provided in each registry
        so that it can be retrieved by this name in `get_positional_value`.
        The positional argument for the settings file name is always added
        to the end of the positionals, whether it is provided or not.
        """

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

        if program_name is None:
            self._program_name = os.path.basename(sys.argv[0])
        else:
            self._program_name = program_name

        self.argv = argv
        self.defaults_file = defaults_file

        # Handle positional arguments manually since we might otherwise eat 
        # argument options that were meant for something else due to the 
        # partial incremental parsing that we do.
        if positionals is None:
            self._positional_args = []
        else:
            self._positional_args = copy(positionals)

        self._positional_args.append({
            "name": "settings",
            "help": "Settings file to read from",
            "type": "string",
            "value": default_settings_file
        })

        self._positional_values = {}

        # Create the real argument parser.
        self.parser = self._create_parser(kwargs)
        self._import_manager = Import_Manager()

        # Create a positional arguments group that is used as a marker for the 
        # ArgumentsHelpFormatter to know where to insert them, namely as first 
        # optional arguments.
        description = "If provided, must be given in order at the start of the arguments"
        self.parser.add_argument_group(self.POSITIONAL_GROUP, description)

        # Create a fake argument parser which creates the actions for the 
        # positional arguments. The ArgumentsHelpFormatter can then retrieve 
        # these actions without them influencing the argument parsing.
        self._positional_actions = []
        fake_parser = self._create_parser(kwargs)
        for positional in self._positional_args:
            kw = self._get_argument_options(positional["name"], positional)
            self._positional_actions.append(fake_parser.add_argument(**kw))

        self.groups = {}

        self._done_help = False

        # Parse the positional arguments from the arguments list so that they 
        # no longer influence other parsing.
        self._handle_positionals()
        self.settings_file = self.get_positional_value("settings")

    def _create_parser(self, kwargs):
        # We disable help here so that partial parses do not yet respond to 
        # --help. After all the settings files have registered themselves in 
        # the Arguments handler, we can display help for all the groups using 
        # Arguments.check_help.
        return ArgumentParser(prog=self, add_help=False,
                              formatter_class=ArgumentsHelpFormatter, **kwargs)

    def __str__(self):
        """
        Create a string formatting for the `Arguments` object.

        This returns the program name which allows the argument parser to show
        this in its usage messages.
        """

        return self._program_name

    def _handle_positionals(self):
        """
        Parse the positional arguments from the argument list input.

        The values read from the arguments list for the positional argument
        registries are then available from `get_positional_value`.
        """

        for info in self._positional_args:
            name = info["name"]
            if len(self.argv) > 0 and not self.argv[0].startswith('-'):
                value = self.argv.pop(0)
            elif "required" in info and info["required"]:
                self.error("Positional argument '{}' is required".format(name))
            elif "value" in info:
                value = info["value"]
            else:
                value = None

            try:
                self._positional_values[name] = self._type_cast(value, info)
            except ValueError as e:
                self.error(str(e))

    def get_positional_args(self):
        """
        Retrieve the list of positional argument registries.
        """

        return self._positional_args

    def get_positional_actions(self):
        """
        Retrieve the list of positional argument actions.
        """

        return self._positional_actions

    def get_positional_value(self, name):
        """
        Retrieve the value of a positional argument by its registry `name`.

        If the positional did not receive a value from the arguments list, then
        this either returns the value from the `default`, or `None` otherwise.

        If the positional registry has a `type`, then the value is type cast
        to this value before returning.
        """

        return self._positional_values[name]

    def get_settings(self, group):
        """
        Retrieve the `Settings` object for the given group name `group`, or
        create it if it did not exist yet.

        This returns a `Settings` object that may have its settings overridden
        with arguments from the input.
        """

        if group in self.groups:
            return self.groups[group]

        settings = Settings(self.settings_file, group,
                            arguments=self, defaults_file=self.defaults_file)

        self._parse_settings(group, settings)
        self.groups[group] = settings
        return self.groups[group]

    def _parse_settings(self, group, settings):
        """
        Parse the arguments relevant to the `Settings` object `settings` with
        group name `group`. This registers the command line arguments in the
        argument parser and partially parses the argument list to update the
        settings with overridden values.
        """

        if not self._done_help:
            self._add_arguments(group, settings)
            self._fill_settings(settings)

    def _get_keys(self, location, relative=True):
        """
        Retrieve a list of option choices from a module or a (nested) attribute.

        The `location` is a list with at least one element, where the first
        element is a module. The module is relative to the base package if
        `relative` is `True`, otherwise it is a global module. The remainder of
        that list, if provided, are variable names that, in order, exist in that
        module, the variable previously in the list, and so on. The final
        variable must be a dictionary, or if it was only a module, then it must
        have an `__all__` variable or be enumerable with `dir`.

        Returns the keys from the variable dictionary or the enumerated values
        from the module's exportable contents.
        """

        try:
            data = self._import_manager.load(location[0], relative=relative)
        except ImportError:
            # Module is not installed. Instead of dieing, simply allow every 
            # value. If the module is of importance outside of the setting, 
            # then the error will be handled in a better way there.
            return None

        for attr in location[1:]:
            data = getattr(data, attr)

        if isinstance(data, dict):
            return data.keys()

        if hasattr(data, "__all__"):
            return data.__all__

        return dir(data)

    def get_help(self, key, info):
        """
        Retrieve a human-readable help message for the setting with the key
        `key` and its registry information `info`.

        Even if no help is defined for this setting, we may provide something
        that is more readable than the key.
        """

        if "help" in info:
            return info["help"]

        parts = key.split('_')
        return ' '.join([parts[0].title()] + parts[1:])

    def get_choices(self, info):
        """
        Retrieve a list of option choices from the setting registry `info`.

        The returned list provides the possible choices for the value of this
        setting. Note that if the setting is not required, then the empty string
        is also a choice, even if it is not in this list.
        """

        if "options" in info:
            return copy(info["options"])
        if "keys" in info:
            return copy(self._get_keys(info["keys"], relative=False))
        if "module" in info:
            return copy(self._get_keys([info["module"]], relative=True))

        return None

    def _get_argument_options(self, key, info):
        """
        Convert the registry information `info` for a given setting key or
        positional argument name `key` to action arguments that are suitable for
        the argument parser.

        Returns the options in a dictionary.
        """

        kw = {
            "dest": key,
            "help": self.get_help(key, info)
        }

        if "value" in info:
            kw["default"] = info["value"]

        required = True
        if "required" in info and not info["required"]:
            kw["required"] = required = info["required"]

        choices = self.get_choices(info)
        if choices is not None:
            if not required:
                choices.append('')

            kw["choices"] = choices

        if info["type"] in ("list", "tuple"):
            kw["nargs"] = info["length"] if "length" in info else "*"
            if "subtype" in info:
                subtype = info["subtype"]
                if isinstance(subtype, dict):
                    subtype = subtype["type"]

                if subtype in self._type_names:
                    kw["type"] = self._type_names[subtype]
        elif "replace" in info:
            # Create a translation table and bind a function that performs the 
            # translation on input to the type of the argument.
            # This ensures the translation is performed before other checks 
            # (such as allowed choices) are done.
            table = string.maketrans(*info["replace"])
            kw["type"] = partial(lambda table, x: str(x).translate(table), table)
        elif info["type"] == "bool":
            # Create options for enabling the setting. The counterpart for 
            # disabling is handled in `_add_arguments`.
            kw["action"] = "store_true"
        elif info["type"] in self._type_names:
            kw["type"] = self._type_names[info["type"]]

        return kw

    def _add_arguments(self, group, settings):
        """
        Register argument specifications in the argument parser for the
        given `Settings` object `settings` with group name `group`.
        """

        argument_group = self.parser.add_argument_group("{} ({})".format(settings.name, group))
        for key, info in settings.get_info():
            # Create arguments dictionary for the argument parser.
            # Use current value of the setting, since it might have been 
            # overridden by the settings compared to the actual defaults.
            kw = self._get_argument_options(key, info)

            sub_group = argument_group
            opt = key.replace('_', '-')

            if info["type"] == "bool":
                sub_group = argument_group.add_mutually_exclusive_group()
                sub_group.add_argument("--{}".format(opt), **kw)

                opt = "no-{}".format(opt)
                kw["help"] = "Disable the setting above"
                kw["action"] = "store_false"

            sub_group.add_argument("--{}".format(opt), **kw)

    def _type_cast(self, value, info):
        """
        Cast the given string `value` to the correct type according to
        registry information in `info`.

        Returns the value of the type appropriate for the setting or positional
        argument.
        """

        if value is not None and "type" in info and info["type"] in self._type_names:
            typecast = self._type_names[info["type"]]
            return typecast(value)

        return value

    def _fill_settings(self, settings):
        """
        Parse arguments from the input and pass any options related to the current Settings object to it.
        """

        args, self.argv = self.parser.parse_known_args(self.argv)
        for key, info in settings.get_info():
            try:
                value = self._type_cast(args.__dict__[key], info)
                settings.set(key, value)
            except ValueError as e:
                # Display errors from setting the value as a usage message.
                # This makes the error display wonky when running this in unit 
                # tests, but the runner scripts need this for good display.
                self.error(str(e))

    def error(self, message):
        """
        Display a textual error `message` and stop the program.

        This method also checks whether the user wants to receive the full help
        message rather than just the usage line and the error.
        """

        try:
            self.check_help()
        except SystemExit:
            self.parser.exit(2, "{}: error: {}\n".format(self._program_name, message))

        self.parser.error(message)

    def check_help(self):
        """
        Check whether the input has a --help option and act accordingly if so.

        This should be used after all Settings components have been registered,
        so that help for all settings is available.
        This method will end the program in case a --help argument is given,
        or in case nonexistent arguments are given.
        """

        argument_group = self.parser.add_argument_group("Optional arguments")
        argument_group.add_argument('-h', '--help', action='help', help="Show this help message and exit")
        self.parser.parse_args(self.argv)
        self._done_help = True
