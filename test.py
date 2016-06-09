# Core imports
import glob
import os
import sys
from cProfile import Profile
from pstats import Stats
from subprocess import check_call, check_output
from StringIO import StringIO

# Unit test imports
import unittest
from mock import patch

# Additional test report imports
import coverage
import pylint.lint

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

    def _get_travis_environment(self, name):
        """
        Retrieve the string value of an environment variable with a name that
        starts with `TRAVIS_`, followed by the given `name`.

        If the environment variable is not found, an empty string is returned.
        """

        environment_variable = "TRAVIS_{}".format(name)
        if environment_variable not in os.environ:
            return ""

        return os.environ[environment_variable]

    def get_changed_files(self):
        """
        Retrieve the files that were changed in a commit range.

        The Git commit range is retrieved from the environment variable
        `TRAVIS_COMMIT_RANGE`, which is set by Travis CI when the tests are run.
        The commit range is altered to contain all commits from the current
        branch stated in the `TRAVIS_BRANCH` environment variable, but only if
        the branch is not the default and the `TRAVIS_PULL_REQUEST` environment
        variable has the value "false" denoting that it is not a PR build.

        Only files that were changed and not deleted in those commits are
        included in the returned list.
        """

        # Check the commit range determined by Travis. We do not provide a list 
        # of changed files if we are not running on Travis.
        commit_range = self._get_travis_environment("COMMIT_RANGE")
        if not commit_range:
            return []

        if self._get_travis_environment("PULL_REQUEST") == "false":
            branch = self._get_travis_environment("BRANCH")
            default_branch = self._settings.get("default_branch")
            if branch != default_branch:
                # Retrieve the FETCH_HEAD of the default branch, since Travis 
                # has a partial clone that does not contain all branch heads.
                check_call(["git", "fetch", "origin", default_branch])

                # Determine the latest commit of the current branch.
                range_parts = commit_range.split('.')
                latest_commit = range_parts[-1]

                # Find commit hash of the earliest boundary point, which should 
                # be the fork point of the current branch, i.e. where the 
                # commits diverge from master ignoring merges from master. This 
                # could also be found using `git merge-base --fork-point`, but 
                # this is not supported on Git 1.8. There are more contrived 
                # solutions at http://stackoverflow.com/q/1527234 but this 
                # single call works good enough.
                commits = check_output([
                    "git", "rev-list", "--boundary",
                    "FETCH_HEAD...{}".format(latest_commit)
                ]).splitlines()

                fork_commits = [commit[1:] for commit in commits if commit.startswith('-')]
                if fork_commits:
                    commit_range = "{}..{}".format(fork_commits[-1], latest_commit)

        # Retrieve all files that were changed in a commit. This excludes 
        # deleted files which no longer exist at this point. Based on 
        # a solution at http://stackoverflow.com/q/424071
        output = check_output([
            "git", "diff-tree", "--no-commit-id", "--name-only",
            "--diff-filter=ACMRTUXB", "-r", commit_range
        ])

        return output.splitlines()

    def execute_pylint(self, files):
        """
        Execute pylint on a given list of files.

        Only Python files are included in the lint check.
        """

        files = [filename for filename in files if filename.endswith('.py')]
        try:
            pylint.lint.Run(["--disable=duplicate-code", "--reports=n"] + files)
        except SystemExit as e:
            if e.code != 0:
                self._failed = True

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

    files = test_run.get_changed_files()
    if files:
        print("> Executing pylint on changed files")
        test_run.execute_pylint(files)

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
