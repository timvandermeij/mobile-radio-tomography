import sys
from __init__ import __package__
from bench.Test_Run import Test_Run
from settings import Arguments

def main(argv):
    arguments = Arguments("settings.json", argv)

    test_run = Test_Run(arguments)

    arguments.check_help()

    # Clean up the logs directory so that old logs are not considered when 
    # checking for exception logs.
    test_run.clear_logs_directory()

    print("> Executing unit tests")
    test_run.execute_unit_tests()

    code_coverage_report = test_run.execute_code_coverage_report()
    if code_coverage_report is not None:
        print("> Executing code coverage")
        print(code_coverage_report)

    method_coverage_report = test_run.execute_method_coverage_report()
    if method_coverage_report is not None:
        print("> Executing method coverage")
        print(method_coverage_report)

    files, commit_range = test_run.get_changed_files()
    if files:
        print("> Executing pylint on changed files in {}".format(commit_range))
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
