import glob
import os
import unittest
from subprocess import check_output

class Test_Run(object):
    def __init__(self):
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

        loader = unittest.TestLoader()
        tests = loader.discover("tests", pattern="*.py", top_level_dir="..")
        runner = unittest.runner.TextTestRunner()
        result = runner.run(tests)

        if not result.wasSuccessful():
            self._failed = True

    def execute_unused_imports_check(self):
        """
        Execute the unused imports check.

        Returns a list of unused imports, and causes the test to fail in case
        there are unused imports.
        """

        excludes = ["__package__", "scipy.sparse.linalg"]
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
            with open(file) as f:
                contents = f.read().rstrip('\n')
                if contents != "":
                    log_contents += contents + "\n"
                    self._failed = True

        return log_contents

    def clear_logs_directory(self):
        """
        Print all logs and clear the logs directory.
        """

        files = glob.glob("logs/*.log")
        for file in files:
            os.remove(file)

def main():
    test_run = Test_Run()
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
    main()
