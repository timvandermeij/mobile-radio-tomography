import json
import unittest

class Type_Checker(object):
    def __init__(self, setting, key, *types):
        self._setting = setting
        self._key = key
        self._types = types

    def check(self):
        return self._setting[self._key] in self._types

    def __nonzero__(self):
        """
        Determine the value of casting the type checker to boolean.
        """

        return self.check()

    def __str__(self):
        """
        Return the formatted representation of the type checker.
        """

        if len(self._types) == 1:
            type_format = "'{}'".format(self._types[0])
        else:
            type_format = "one of {}".format(self._types)

        return "the '{}' must be {}, not '{}'".format(self._key, type_format, self._setting[self._key])

    def __repr__(self):
        """
        Return a Python expression that defines the type checker.
        """

        return "{} in {}".format(self._setting[self._key], self._types)

class TestSettingsDefaults(unittest.TestCase):
    def _is_sequence_type(self, setting):
        return Type_Checker(setting, "type", "list", "tuple")

    def _is_dict_type(self, setting):
        key = "subtype" if "subtype" in setting else "type"

        return Type_Checker(setting, key, "dict")

    def _is_class_type(self, setting):
        return Type_Checker(setting, "type", "class")

    def _is_numeric_type(self, setting):
        subkey = "subtype" if self._is_sequence_type(setting) else "type"
        return Type_Checker(setting, subkey, "int", "float")

    def assert_has_key(self, component, key, setting, subkey):
        """
        Check whether a setting with name `key` and information registration
        `setting`, which was retrieved from the component with name `component`,
        has a key `subkey` in its data.
        """

        msg = "Setting '{}' in component '{}' must have a '{}' key"
        self.assertIn(subkey, setting, msg.format(key, component, subkey))

    def assert_match_type_keys(self, component, key, setting, type_check, *subkeys, **options):
        """
        Check whether a setting with name `key` and information registration
        `setting`, which was retrieved from the component with name `component`,
        satisfies the following implication:

        if there are any keys from `subkeys` in the setting's data, then
        the type of the setting must be accepted by the `Type_Checker` object
        returned by the callback in `type_check`.

        The type of the setting can be either the 'type' or the 'subtype' within
        the setting's data, depending on the type checker function.

        The inverse of this implication (if the setting is of such a type, then
        all the subkeys must be present in the setting's data) is only checked
        when `required_keys` is enabled.
        """

        required_keys = "required_keys" in options and options["required_keys"]
        if required_keys and type_check(setting):
            for subkey in subkeys:
                self.assert_has_key(component, key, setting, subkey)

        if any(subkey in setting for subkey in subkeys):
            type_checker = type_check(setting)

            msg = "Setting '{}' in component '{}' has {}, thus {}"
            if len(subkeys) == 1:
                subkeys_format = "a key '{}'".format(subkeys[0])
            else:
                subkeys_format = "one or more keys from {}".format(subkeys)

            self.assertTrue(type_checker, msg.format(key, component, subkeys_format, type_checker))

    def _check_setting(self, component, key, setting, dictinfo=False):
        """
        Check whether a setting with name `key` and information registration
        `setting`, which was retrieved from the component with name `component`,
        has all the keys it should have, depending on its type.

        If `dictinfo` is given, then this does not check for the presence of
        the 'help' and 'default' fields which are not needed for dictionary
        subitems.
        """

        if not dictinfo:
            self.assert_has_key(component, key, setting, "help")
            self.assert_has_key(component, key, setting, "default")

        self.assert_has_key(component, key, setting, "type")

        self.assert_match_type_keys(component, key, setting, self._is_dict_type,
                                    "dictinfo", required_keys=True)
        self.assert_match_type_keys(component, key, setting,
                                    self._is_class_type,
                                    "module", required_keys=True)
        self.assert_match_type_keys(component, key, setting,
                                    self._is_sequence_type, "length", "subtype")
        self.assert_match_type_keys(component, key, setting,
                                    self._is_numeric_type, "min", "max")

        if self._is_dict_type(setting):
            for dictkey in setting["dictinfo"]:
                self._check_setting(component, "{}-{}".format(key, dictkey), setting["dictinfo"][dictkey], dictinfo=True)
        elif self._is_sequence_type(setting):
            self.assert_has_key(component, key, setting, "subtype")

    def test_settings_defaults(self):
        # Test whether all the settings in each components have appropriate 
        # information registration in their defaults.

        with open("settings/defaults.json") as defaults_file:
            components = json.load(defaults_file)

        for component in components:
            self.assertIn("name", components[component], "Component '{}' must have a 'name' key".format(component))
            self.assertIn("settings", components[component], "Component '{}' must have a 'settings' key".format(component))
            if "parent" in components:
                parent = components[component]["parent"]
                self.assertIn(parent, component, "Component '{}' has a parent '{}' that must exist".format(component, parent))

            settings = components[component]["settings"]
            for key in settings:
                self._check_setting(component, key, settings[key])
