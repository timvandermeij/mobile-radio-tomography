# Core imports
import glob
import os
from subprocess import check_call, check_output
from StringIO import StringIO

# Unit test imports
import unittest
from mock import patch

# Additional test report imports
import coverage
import pylint.lint

# Package imports
from ..core.Import_Manager import Import_Manager
from Method_Coverage import Method_Coverage
from Test_Result import Test_Result_Factory

class Test_Run(object):
    """
    Test runner class.

    This class provides the means for running unit tests, code coverage, style
    checks and other steps that can be taken before, during and after the tests.
    """

    def __init__(self, arguments):
        self._arguments = arguments
        self._settings = self._arguments.get_settings("test_runner")
        self._failed = False

        self._import_manager = Import_Manager()
        self._preimported_modules = [
            "core.Import_Manager", "settings", "settings.Settings",
            "settings.Arguments"
        ]

        self._loader = unittest.TestLoader()
        self._loader.testMethodPrefix = self._settings.get("test_method_prefix")

        if self._settings.get("coverage"):
            # Only consider our own module so that we exclude system and site 
            # packages, and exclude the test bench, test runner and tests 
            # themselves from code coverage.
            path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            include_path = "{}/*".format(path)
            excluded_patterns = ["test.py", "bench/*", "tests/*"]
            excluded_paths = [
                "{}/{}".format(path, pattern) for pattern in excluded_patterns
            ]
            self._statement_coverage = coverage.Coverage(include=include_path,
                                                         omit=excluded_paths)

            self._method_coverage = Method_Coverage(self._arguments,
                                                    self._import_manager)
        else:
            self._statement_coverage = None
            self._method_coverage = None

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

        if self._statement_coverage is not None:
            # Enable statement coverage around loading and running tests.
            self._statement_coverage.start()

        pattern = self._settings.get("pattern")
        verbosity = self._settings.get("verbosity")

        tests = self._loader.discover("tests", pattern=pattern,
                                      top_level_dir="..")

        factory = Test_Result_Factory(self._arguments)
        runner = unittest.runner.TextTestRunner(verbosity=verbosity,
                                                resultclass=factory)

        result = runner.run(tests)

        if self._statement_coverage is not None:
            self._statement_coverage.stop()

        # Reload the Import_Manager so that the Method_Coverage can safely use 
        # it again to load modules.
        self._import_manager.reload_unloaded("core.Import_Manager")
        if self._method_coverage is not None:
            self._method_coverage.run(tests)

        if not result.wasSuccessful():
            self._failed = True

    def execute_statement_coverage_report(self):
        """
        Create a statement coverage report if coverage is enabled. We
        automatically disable coverage if we do not run all tests or a test has
        failed. The test run also fails if the statement coverage is not 100%.

        This method returns the report text if coverage is enabled, otherwise
        it returns `None`.
        """

        if self._statement_coverage is None:
            return None

        if self._failed or not self._settings.is_default("pattern"):
            return None

        report = StringIO()
        percentage = self._statement_coverage.report(file=report,
                                                     show_missing=True,
                                                     skip_covered=True)

        if percentage < 100:
            self._failed = True

        return report.getvalue()

    def execute_method_coverage_report(self):
        """
        Create a method coverage report if coverage is enabled. We automatically
        disable coverage if we do not run all tests or a test has failed.
        The test run also fails if the method coverage is not 100%.

        This method returns the report text if coverage is enabled, otherwise
        it returns `None`.
        """

        if self._method_coverage is None:
            return None

        if self._failed or not self._settings.is_default("pattern"):
            return None

        output, percentage = self._method_coverage.get_results()

        if percentage < 100:
            self._failed = True

        return output

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

    def _get_commit_range(self):
        """
        Retrieve a Git commit range specification that includes the current
        branch, pull request or pushed commits.

        If no such range can be found, this returns an empty string.
        """

        # Check the commit range determined by Travis.
        commit_range = self._get_travis_environment("COMMIT_RANGE")
        if not commit_range:
            # For branches with only one commit, there may be no commit range. 
            # Try to find the one commit.
            return self._get_travis_environment("COMMIT")

        # Determine the commit range of the current branch.
        range_parts = commit_range.split('.')
        first_commit = range_parts[0]
        latest_commit = range_parts[-1]
        pull_request = self._get_travis_environment("PULL_REQUEST")
        base_commit = ""

        if pull_request == "false":
            branch = self._get_travis_environment("BRANCH")
            default_branch = self._settings.get("default_branch")
            if branch != default_branch:
                # Retrieve the FETCH_HEAD of the default branch, since Travis 
                # has a partial clone that does not contain all branch heads.
                check_call(["git", "fetch", "origin", default_branch])
                base_commit = "FETCH_HEAD"
        elif pull_request:
            base_commit = self._get_travis_environment("BRANCH")

        if base_commit:
            # Find commit hash of the earliest boundary point, which should be 
            # the fork point of the current branch, i.e. where the commits 
            # diverge from master ignoring merges from master. This could also 
            # be found using `git merge-base --fork-point`, but this is not 
            # supported on Git 1.8. There are more contrived solutions at 
            # http://stackoverflow.com/q/1527234 but this single call works 
            # good enough.
            commits = check_output([
                "git", "rev-list", "--boundary",
                "{}...{}".format(base_commit, latest_commit)
            ]).splitlines()

            fork_commits = [
                commit[1:] for commit in commits if commit.startswith('-')
            ]
            if fork_commits:
                first_commit = fork_commits[-1]

        return "{}..{}".format(first_commit, latest_commit)

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
        included in the returned list. The commit range is also returned.
        """

        commit_range = self._get_commit_range()
        if not commit_range:
            # We can only determine the commit range on Travis.
            return [], ""

        # Retrieve all files that were changed in a commit. This excludes 
        # deleted files which no longer exist at this point. Based on 
        # a solution at http://stackoverflow.com/q/424071
        output = check_output([
            "git", "diff-tree", "--no-commit-id", "--name-only",
            "--diff-filter=ACMRTUXB", "-r", commit_range
        ])

        return output.splitlines(), commit_range

    def execute_pylint(self, files):
        """
        Execute pylint on a given list of files.

        Only Python files are included in the lint check.
        """

        # Filter list of file names to only include Python files.
        files = [filename for filename in files if filename.endswith('.py')]
        # There might not be any Python files left after filtering the list, so 
        # do not run pylint if this is the case.
        if not files:
            return

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
