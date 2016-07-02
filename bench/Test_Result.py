from cProfile import Profile
from pstats import Stats
import unittest

class Test_Result_Factory(object):
    """
    A factory that creates appropriate test result objects when it is called.

    This can be used for the `resultclass` argument of a `TextTestRunner`.
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
