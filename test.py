import glob
import os
import sys
import unittest
from subprocess import check_output
from __init__ import __package__
from settings import Arguments

class Test_Run(object):
    def __init__(self, arguments):
        self._settings = arguments.get_settings("test_runner")
        self._failed = False

    def is_passed(self):
        """
        Check whether all the test run parts succeeded.
        """

        return not self._failed

    def execute_unit_tests(self):
        """
        Execute the unit tests.
        """

        pattern = self._settings.get("pattern")
        verbosity = self._settings.get("verbosity")

        loader = unittest.TestLoader()
        tests = loader.discover("tests", pattern=pattern, top_level_dir="..")
        runner = unittest.runner.TextTestRunner(verbosity=verbosity)
        result = runner.run(tests)

        if not result.wasSuccessful():
            self._failed = True

    def execute_unused_imports_check(self):
        """
        Execute the unused imports check.

        Returns a list of unused imports, and causes the test to fail in case
        there are unused imports.
        """

        excludes = self._settings.get("import_exclude")
        output = check_output(["importchecker", "."])
        unused_imports = []
        for line in output.splitlines():
            ignore = False
            for exclude in excludes:
                if exclude in line:
                    ignore = True

            if ignore:
                continue

            unused_imports.append(line.rstrip())
            self._failed = True

        return unused_imports

    def read_logs_directory(self):
        """
        Read all logs in the logs directory.

        Returns the concatenared file contents of all the logs.
        """

        files = glob.glob("logs/*.log")
        log_contents = ""
        for file in files:
            with open(file) as log_file:
                contents = log_file.read().rstrip("\n")
                if contents != "":
                    log_contents += contents + "\n"
                    self._failed = True

        return log_contents

    def clear_logs_directory(self):
        """
        Clear all log files the logs directory.
        """

        files = glob.glob("logs/*.log")
        for file in files:
            os.remove(file)

def main(argv):
    arguments = Arguments("settings.json", argv)

    test_run = Test_Run(arguments)

    arguments.check_help()

    # Clean up the logs directory so that old logs are not considered when 
    # checking for exception logs.
    test_run.clear_logs_directory()

    print("> Executing unit tests")
    test_run.execute_unit_tests()

    print("> Executing unused imports check")
    unused_imports = test_run.execute_unused_imports_check()
    for unused_import in unused_imports:
        print("Unused import found: {}".format(unused_import))

    print("> Cleaning up the logs directory")
    log_contents = test_run.read_logs_directory()
    if log_contents != "":
        print("Exception logs found:")
        print(log_contents)

    test_run.clear_logs_directory()

    if not test_run.is_passed():
        exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
