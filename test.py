import glob
import os
from subprocess import call, check_output

class Test_Run(object):
    def __init__(self):
        self._failed = False

    def is_passed(self):
        return not self._failed

    def execute_unit_tests(self):
        """
        Execute the unit tests.
        """

        return_code = call(["python2", "-m", "unittest", "discover",
                            "-s", "tests", "-p", "*.py", "-t", ".."])

        if return_code != 0:
            self._failed = True

    def execute_unused_imports_check(self):
        """
        Execute the unused imports check.
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

    def clear_logs_directory(self):
        """
        Clear the logs directory.
        """

        files = glob.glob("logs/*.log")
        for file in files:
            os.remove(file)

def main():
    test_run = Test_Run()

    print("> Executing unit tests")
    test_run.execute_unit_tests()

    print("> Executing unused imports check")
    unused_imports = test_run.execute_unused_imports_check()
    for unused_import in unused_imports:
        print("Unused import found: {}".format(unused_import))

    print("> Clearing the logs directory")
    test_run.clear_logs_directory()

    if not test_run.is_passed():
        exit(1)

if __name__ == "__main__":
    main()
