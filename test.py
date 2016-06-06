# Core imports
import glob
import os
import sys
from cProfile import Profile
from pstats import Stats
from subprocess import check_output
from StringIO import StringIO

# Unit test imports
import unittest
from mock import patch

# Coverage imports
import coverage

# Package imports
from __init__ import __package__
from core.Import_Manager import Import_Manager
from settings import Arguments

class TestResultFactory(object):
    """
    A factory that creates appropriate test result objects when it is called.
    """

    def __init__(self, settings):
        self._settings = settings

    def __call__(self, stream, descriptions, verbosity):
        return BenchTestResult(self._settings, stream, descriptions, verbosity)

class BenchTestResult(unittest.runner.TextTestResult):
    """
    A textual test result formatter that can display additional information
    such as profile output and benchmarks.
    """

    def __init__(self, settings, stream, descriptions, verbosity):
        super(BenchTestResult, self).__init__(stream, descriptions, verbosity)
        self._sort = settings.get("profile_sort")
        self._limit = settings.get("profile_limit")
        self._benchmark = verbosity > 2
        self._profiler = None

    def startTest(self, test):
        super(BenchTestResult, self).startTest(test)
        if self._benchmark:
            self._profiler = Profile()
            self._profiler.enable()

    def stopTest(self, test):
        super(BenchTestResult, self).stopTest(test)
        if self._benchmark:
            self._profiler.disable()
            stats = Stats(self._profiler)
            stats.sort_stats(self._sort)
            stats.print_stats(self._limit)

class Test_Run(object):
    def __init__(self, arguments):
        self._settings = arguments.get_settings("test_runner")
        self._failed = False

        self._import_manager = Import_Manager()
        self._preimported_modules = [
            "core.Import_Manager", "settings", "settings.Settings",
            "settings.Arguments"
        ]

        if self._settings.get("coverage"):
            # Only consider our own module so that we exclude system and site 
            # packages, and exclude the test runner and tests themselves from 
            # code coverage.
            path = os.path.dirname(os.path.abspath(__file__))
            self._coverage = coverage.Coverage(include="{}/*".format(path),
                                               omit=[__file__, "tests/*"])
        else:
            self._coverage = None

    def is_passed(self):
        """
        Check whether all the test run parts succeeded.
        """

        return not self._failed

    def execute_unit_tests(self):
        """
        Execute the unit tests.
        """

        # Import pymavlink.mavutil with a patched output in order to suppress 
        # the debugging print that occurs while importing it. This makes later 
        # imports skip this debug print.
        with patch('sys.stdout'):
            self._import_manager.load("pymavlink.mavutil", relative=False)

        # Discard the module cache for the package modules imported in the test 
        # runner. This ensures that they are reimported in the tests, which 
        # makes the coverage consider start-up calls again.
        for module in self._preimported_modules:
            self._import_manager.unload(module, relative=True)

        pattern = self._settings.get("pattern")
        verbosity = self._settings.get("verbosity")

        if self._coverage is not None:
            # Enable code coverage around the loading and running of tests.
            self._coverage.start()

        loader = unittest.TestLoader()
        tests = loader.discover("tests", pattern=pattern, top_level_dir="..")

        factory = TestResultFactory(self._settings)
        runner = unittest.runner.TextTestRunner(verbosity=verbosity,
                                                resultclass=factory)

        result = runner.run(tests)

        if self._coverage is not None:
            self._coverage.stop()

        if not result.wasSuccessful():
            self._failed = True

    def execute_coverage_report(self):
        """
        Create a code coverage report if coverage is enabled and all tests
        have succeeded.
        """

        if self._failed:
            return None

        if self._coverage is not None:
            report = StringIO()
            self._coverage.report(file=report,
                                  show_missing=True, skip_covered=True)

            return report.getvalue()

        return None

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

    coverage_report = test_run.execute_coverage_report()
    if coverage_report is not None:
        print("> Executing code coverage")
        print(coverage_report)

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
