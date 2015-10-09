import unittest
from mock import patch
from StringIO import StringIO
from ..settings import Arguments, Settings

class TestArguments(unittest.TestCase):
    def tearDown(self):
        Settings.settings_files = {}

    def test_default_settings(self):
        arguments = Arguments("tests/invalid.json", ["tests/settings.json"])
        # Command line input for settings file is initialized immediately
        self.assertEqual(arguments.settings_file, "tests/settings.json")
        settings = arguments.get_settings("foo")
        self.assertEqual(settings.get("bar"), 2)

    def test_settings(self):
        arguments = Arguments("tests/settings.json", ['--bar', '5'])
        settings = arguments.get_settings("foo")
        # We get the same object every time
        self.assertEqual(id(settings), id(arguments.get_settings("foo")))
        # Command line arguments override values in JSON.
        self.assertEqual(settings.get("bar"), 5)

    def test_check_help(self):
        arguments = Arguments("tests/settings.json", ['--help'])

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

    def test_nonexistent_settings(self):
        arguments = Arguments("tests/settings.json", ['--qux', '42'])

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
