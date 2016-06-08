# Core imports
from StringIO import StringIO

# Library imports
from mock import patch, MagicMock

# Package imports
from ..settings import Arguments, Settings
from settings import SettingsTestCase

class MockModule(object):
    def __dir__(self):
        return ['g', 'h', 'i', 'j']

class TestArguments(SettingsTestCase):
    def test_default_settings(self):
        arguments = Arguments("tests/settings/invalid.json", [
            "tests/settings/settings.json"
        ], defaults_file="tests/settings/defaults.json")
        # Command line input for settings file is initialized immediately
        self.assertEqual(arguments.settings_file, "tests/settings/settings.json")
        self.assertEqual(arguments.defaults_file, "tests/settings/defaults.json")
        settings = arguments.get_settings("foo")
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.get("bar"), 2)

    def test_settings(self):
        arguments = Arguments("tests/settings/settings.json", [
            '--bar', '5', '--no-baz', '--long-name', 'my_text',
            '--items', '4', '5', '--other'
        ], defaults_file="tests/settings/defaults.json")
        settings = arguments.get_settings("foo")
        # We get the same object every time
        self.assertEqual(id(settings), id(arguments.get_settings("foo")))
        # Command line arguments override values in both settings and defaults 
        # JSON files.
        self.assertEqual(settings.get("bar"), 5)
        self.assertEqual(settings.get("baz"), False)
        self.assertEqual(settings.get("long_name"), "my_text")
        self.assertEqual(settings.get("items"), [4, 5])
        # Arguments left to parse that may be part of another component
        self.assertEqual(arguments.argv, ['--other'])

    def test_check_help(self):
        arguments = Arguments("tests/settings/settings.json", ['--help'],
                              defaults_file="tests/settings/defaults.json")
        arguments.get_settings("foo")

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                # Test whether the argument parser calls sys.exit on help.
                # This can be caught as an exception.
                with self.assertRaises(SystemExit):
                    arguments.check_help()

        self.assertRegexpMatches(output.getvalue(), "--help")
        self.assertRegexpMatches(output.getvalue(), r"Foo component \(foo\)")

    def test_arguments_after_help(self):
        arguments = Arguments("tests/settings/settings.json", ['--no-baz'],
                              defaults_file="tests/settings/defaults.json")
        settings = arguments.get_settings("foo")

        # Buffer help output so it doesn't mess up the test output.
        with patch('sys.stdout'):
            with patch('sys.stderr'):
                try:
                    arguments.check_help()
                except SystemExit:
                    self.fail("Arguments.check_help raised a SystemExit without any help or unused arguments")

        self.assertTrue(arguments._done_help)
        self.assertEqual(arguments.argv, [])
        self.assertFalse(settings.get("baz"))

        # Retrieving settings after Arguments is done does not alter its value 
        # from the defaults/overrides anymore.
        child = arguments.get_settings("child")
        self.assertTrue(child.get("baz"))

    def test_required_settings(self):
        arguments = Arguments("tests/settings/settings.json", ['--long-name'],
                              defaults_file="tests/settings/defaults.json")

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                # Test whether the argument parser calls sys.exit on help.
                # This can be caught as an exception.
                with self.assertRaises(SystemExit):
                    arguments.get_settings("foo")
                    arguments.check_help()

        self.assertRegexpMatches(output.getvalue(), "expected one argument")

    def test_required_error(self):
        arguments = Arguments("tests/settings/settings.json", ['--long-name='],
                              defaults_file="tests/settings/defaults.json")

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                # Test whether the argument parser calls sys.exit on help.
                # This can be caught as an exception.
                with self.assertRaises(SystemExit):
                    arguments.get_settings("foo")
                    arguments.check_help()

        self.assertRegexpMatches(output.getvalue(), "must be nonempty")

    def test_nonexistent_settings(self):
        arguments = Arguments("tests/settings/settings.json", ['--qux', '42'],
                              defaults_file="tests/settings/defaults.json")

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                # Test whether the argument parser calls sys.exit on help.
                # This can be caught as an exception.
                with self.assertRaises(SystemExit):
                    arguments.check_help()

        self.assertRegexpMatches(output.getvalue(), "unrecognized arguments")

    def test_get_help(self):
        arguments = Arguments("tests/settings/settings.json", [],
                              defaults_file="tests/settings/defaults.json")
        info = {"help": "Help text"}
        self.assertEqual(arguments.get_help("okey", info), info["help"])
        self.assertEqual(arguments.get_help("long_setting", {}), "Long setting")

    def test_choices(self):
        arguments = Arguments("tests/settings/settings.json", ['--select='],
                              defaults_file="tests/settings/defaults.json")

        # It is possible to select an empty default when the setting is not 
        # required.
        settings = arguments.get_settings("foo")
        self.assertEqual(settings.get("select"), "")

    def test_get_choices(self):
        arguments = Arguments("tests/settings/settings.json", [],
                              defaults_file="tests/settings/defaults.json")
        info = {"options": ["foo", "bar", "baz"]}
        self.assertEqual(arguments.get_choices(info), info["options"])

        # Retrieving choices from a nonexistent module results in None.
        info = {"module": "nonexistent_module"}
        self.assertIsNone(arguments.get_choices(info))

        # Retrieving choices from keys of a dictionary variable works.
        data = {'a': 'b', 'c': 'd'}
        expected = data.keys()
        mock_module = MagicMock()
        mock_module.mock_member.mock_add_spec(data)
        mock_module.mock_member.keys.return_value = expected
        modules = {
            "mock_module": mock_module
        }
        with patch.dict('sys.modules', modules):
            info = {"keys": ["mock_module", "mock_member"]}
            self.assertEqual(arguments.get_choices(info), expected)
            mock_module.mock_member.keys.assert_called_once_with()

        # Retrieving choices from __all__ works as expected.
        expected = ['e', 'f']
        mock_module = MagicMock(__all__=expected)
        modules = {
            __package__.split('.')[0] + ".mock_module": mock_module
        }
        with patch.dict('sys.modules', modules):
            info = {"module": "mock_module"}
            self.assertEqual(arguments.get_choices(info), expected)

        # Retrieving choices from dir() works as expected
        mock_module = MockModule()
        expected = dir(mock_module)
        modules = {
            __package__.split('.')[0] + ".mock_module": mock_module
        }
        with patch.dict('sys.modules', modules):
            info = {"module": "mock_module"}
            self.assertEqual(arguments.get_choices(info), expected)
