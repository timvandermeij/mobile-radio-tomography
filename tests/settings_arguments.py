# Core imports
from StringIO import StringIO
from argparse import Action, ArgumentParser

# Library imports
from mock import patch, MagicMock

# Package imports
from ..bench.Method_Coverage import covers
from ..settings import Arguments, Settings
from settings import SettingsTestCase

class MockModule(object):
    def __dir__(self):
        return ['g', 'h', 'i', 'j']

class TestSettingsArguments(SettingsTestCase):
    def setUp(self):
        super(TestSettingsArguments, self).setUp()
        self.defaults_file = "tests/settings/defaults.json"
        self.positional_args = [
            {
                "name": "first",
                "type": "int",
                "required": True
            },
            {
                "name": "second",
                "type": "string",
                "value": "xyz"
            },
            {
                "name": "third",
                "type": "float"
            }
        ]

    def test_initialization(self):
        arguments = Arguments("tests/settings/settings.json", ['1', '--xyz'],
                              program_name="TestProgram",
                              defaults_file=self.defaults_file)

        self.assertEqual(str(arguments), "TestProgram")
        # Positional arguments are immediately removed
        self.assertEqual(arguments.argv, ['--xyz'])
        self.assertIsInstance(arguments.parser, ArgumentParser)
        self.assertEqual(arguments.groups, {})

    def test_initialization_default_settings(self):
        arguments = Arguments("tests/settings/invalid.json", [
            "tests/settings/settings.json"
        ], defaults_file=self.defaults_file)
        # Command line input for settings file is initialized immediately
        self.assertEqual(arguments.settings_file, "tests/settings/settings.json")
        self.assertEqual(arguments.defaults_file, self.defaults_file)
        settings = arguments.get_settings("foo")
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.get("bar"), 2)

    def test_get_settings(self):
        arguments = Arguments("tests/settings/settings.json", [
            '--bar', '5', '--no-baz', '--long-name', 'my_text',
            '--items', '4', '5', '--other'
        ], defaults_file=self.defaults_file)
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
                              defaults_file=self.defaults_file)
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

    @covers("get_positional_args")
    @covers("get_positional_actions")
    @covers("get_positional_value")
    def test_positional(self):
        arguments = Arguments("tests/settings/settings.json", ["3", "abc"],
                              positionals=self.positional_args,
                              defaults_file=self.defaults_file)

        positional = arguments.get_positional_args()[:len(self.positional_args)]
        self.assertEqual(positional, self.positional_args)

        actions = arguments.get_positional_actions()
        self.assertEqual(len(actions), len(self.positional_args) + 1)
        self.assertTrue(all(isinstance(action, Action) for action in actions))

        self.assertEqual(arguments.get_positional_value("first"), 3)
        self.assertEqual(arguments.get_positional_value("second"), "abc")
        self.assertIsNone(arguments.get_positional_value("third"))

    @covers("_handle_positionals")
    def test_positional_required(self):
        # Buffer help output so it doesn't mess up the test output.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                with self.assertRaises(SystemExit):
                    Arguments("tests/settings/settings.json", [],
                              positionals=self.positional_args,
                              defaults_file=self.defaults_file)

        self.assertRegexpMatches(output.getvalue(),
                                 "Positional argument 'first' is required")

    @covers("_handle_positionals")
    def test_positional_error_help(self):
        # Buffer help output so it doesn't mess up the test output.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                with self.assertRaises(SystemExit):
                    Arguments("tests/settings/settings.json",
                              ["42", "?", "aah", "--help"],
                              positionals=self.positional_args,
                              defaults_file=self.defaults_file)

        # The output contains the original error as well as the help message.
        self.assertRegexpMatches(output.getvalue(),
                                 "could not convert string to float: aah")
        self.assertRegexpMatches(output.getvalue(), "--help")

    @covers("check_help")
    def test_arguments_after_help(self):
        arguments = Arguments("tests/settings/settings.json", ['--no-baz'],
                              defaults_file=self.defaults_file)
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

    @covers("check_help")
    def test_required_settings(self):
        arguments = Arguments("tests/settings/settings.json", ['--long-name'],
                              defaults_file=self.defaults_file)

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

    @covers("check_help")
    def test_required_error(self):
        arguments = Arguments("tests/settings/settings.json", ['--long-name='],
                              defaults_file=self.defaults_file)

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

    @covers("check_help")
    def test_nonexistent_settings(self):
        arguments = Arguments("tests/settings/settings.json", ['--qux', '42'],
                              defaults_file=self.defaults_file)

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

    def test_error(self):
        arguments = Arguments("tests/settings/settings.json", [],
                              defaults_file=self.defaults_file)

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                with self.assertRaises(SystemExit):
                    arguments.error("test message")

        self.assertRegexpMatches(output.getvalue(), "test message")

    def test_error_help(self):
        arguments = Arguments("tests/settings/settings.json", ["--help"],
                              defaults_file=self.defaults_file)

        # Buffer help output so it doesn't mess up the test output and we can 
        # actually test whether it prints help.
        output = StringIO()
        with patch('sys.stdout', output):
            with patch('sys.stderr', output):
                with self.assertRaises(SystemExit):
                    arguments.error("test message")

        # The output contains the error message as well as the help message.
        self.assertRegexpMatches(output.getvalue(), "test message")
        self.assertRegexpMatches(output.getvalue(), "--help")

    def test_get_help(self):
        arguments = Arguments("tests/settings/settings.json", [],
                              defaults_file=self.defaults_file)
        info = {"help": "Help text"}
        self.assertEqual(arguments.get_help("okey", info), info["help"])
        self.assertEqual(arguments.get_help("long_setting", {}), "Long setting")

    @covers("_get_argument_options")
    def test_choices(self):
        arguments = Arguments("tests/settings/settings.json", ['--select='],
                              defaults_file=self.defaults_file)

        # It is possible to select an empty default when the setting is not 
        # required.
        settings = arguments.get_settings("foo")
        self.assertEqual(settings.get("select"), "")

    def test_get_choices(self):
        arguments = Arguments("tests/settings/settings.json", [],
                              defaults_file=self.defaults_file)
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
            actual = arguments.get_choices(info)
            self.assertEqual(actual, expected)

            # Adding a new choice to the return value does not change the 
            # original reference.
            actual.append('something')
            self.assertNotIn('something', expected)
            self.assertNotEqual(actual, expected)

        # Retrieving choices from dir() works as expected
        mock_module = MockModule()
        expected = dir(mock_module)
        modules = {
            __package__.split('.')[0] + ".mock_module": mock_module
        }
        with patch.dict('sys.modules', modules):
            info = {"module": "mock_module"}
            self.assertEqual(arguments.get_choices(info), expected)
