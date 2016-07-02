import re
import types
import unittest
from mock import patch, MagicMock

class Method_Coverage(object):
    """
    Method coverage tracker.
    """

    def __init__(self, import_manager, test_class_prefix='Test',
                 test_method_prefix='test'):
        """
        Set up the method coverage tracker.

        The given `import_manager` is an `Import_Manager` object for the package
        where the tests are run. The `test_class_prefix` is a prefix that is
        removed from a test class when we infer an actual class from it.
        The same applies for `test_method_prefix`, which applies to test methods
        and has the addition that underscores after it are also removed.
        """

        self._import_manager = import_manager
        self._class_prefix = test_class_prefix
        self._method_prefix = test_method_prefix

        # Dictionary of actual classes. This doubles as a lookup cache for test 
        # classes that have been inferred previously, as well as method 
        # coverage tracking and final result gathering.
        # The keys of the dictionary are (unmangled) test class names, and the 
        # values are dictionaries themselves, where we have the following keys:
        # - "module": A string indicating the inferred module.
        # - "class": A class type that was inferred from the test class.
        # - "methods": A dictionary containing relevant methods that exist in 
        #   the inferred class, with values indicating whether that method has 
        #   been covered by a test method.
        self._classes = {}

        # Warnings that were generated during the inference process.
        self._warnings = []

        # Regular expression to split a CamelCase name into word parts.
        # This regular expression tries to keep uppercase acronyms with three 
        # or more letters in one group, so that "ABCFoo" is split into "ABC" 
        # and "Foo", while shorter uppercases are not split, such as "XBee".
        self._camel_case_regex = re.compile('.+?(?:(?<=[a-z])(?=[A-Z])|' + \
                                            '(?<=[A-Z]{2})(?=[A-Z][a-z])|$)')

    def run(self, tests):
        """
        Perform the method coverage.

        The given `tests` is a `unittest.TestSuite` filled with discovered tests
        that are run in the test runner.

        This unwraps all the `unittest.TestCase` objects from the tests, looking
        for test cases that correspond to a test method in a test class. These
        are then matched to the actual method from the class being tested.
        Finally, results are shown, where test classes and methods that could
        not be matched with a real class are mentioned, as well as the coverage
        and seemingly untested methods of each class are specified.
        """

        # We need to mock the RPi.GPIO module as it is only available
        # on Raspberry Pi devices and these tests run on a PC.
        rpi_gpio_mock = MagicMock()
        modules = {
            'RPi': rpi_gpio_mock,
            'RPi.GPIO': rpi_gpio_mock.GPIO
        }

        with patch.dict('sys.modules', modules):
            self._iter_tests(tests)

    def _iter_tests(self, suite):
        """
        Loop through all the tests in a `unittest.TestSuite` object `suite`.

        Each `unittest.TestCase` found is processed, while nested test suites
        are iterated recursively in the same way.
        """

        for test in suite:
            if isinstance(test, unittest.TestSuite):
                self._iter_tests(test)
            elif isinstance(test, unittest.TestCase):
                self._handle_test(test)

    def get_results(self):
        """
        Format the results of the method coverage.

        The returned string contains warnings found during the test class
        inference process, the coverage statistics and untested methods.
        """

        out = "\n".join(self._warnings)

        total_methods = 0
        total_covered = 0

        for test_class, data in self._classes.iteritems():
            if data is None:
                continue

            module_name = data["module"]
            class_name = data["class"].__name__
            total = len(data["methods"])
            covered = sum(data["methods"].values())
            if total == 0:
                continue

            stats_format = "\n{} -> {}.{}: {}/{} ({:.0%})\n"
            out += stats_format.format(test_class, module_name, class_name,
                                       covered, total, covered / float(total))

            if covered < total:
                missing_methods = []
                for method, found in data["methods"].iteritems():
                    if not found:
                        missing_methods.append(method)

                out += "Missed methods: {}\n".format(', '.join(missing_methods))

            total_methods += total
            total_covered += covered

        if total_methods > 0:
            total_format = "\nTotal method coverage: {}/{} ({:.0%})\n"
            out += total_format.format(total_covered, total_methods,
                                       total_covered / float(total_methods))

        return out

    def _handle_test(self, test):
        """
        Handle a `unittest.TestCase` object `test`.

        Attempt to relate its test class with an actual class, and if this is
        possible then relate the test method with an actual class method.

        Finally, if we find the actual method, mark it as tested.
        """

        test_class = test.__class__.__name__
        test_method = test._testMethodName
        if test_class not in self._classes:
            self._classes[test_class] = self._convert_test_class(test_class)

        if self._classes[test_class] is None:
            return

        target_method = self._convert_test_method(test_class, test_method)
        if target_method is not None:
            self._classes[test_class]["methods"][target_method] = True

    def _convert_test_class(self, test_class):
        """
        Handle the test class name `test_class`.

        This pulls the class name through various conversion and inference steps
        to retrieve an actual class.

        If the actual class can be inferred, then this returns a dictionary
        containing the inferred module name, actual class type and methods to be
        covered. If any of the steps fail, then `None` is returned and a warning
        will be added to the output in `show_result`. 
        """

        if test_class.startswith(self._class_prefix):
            test_class = test_class[len(self._class_prefix):]

        # Split the class name into its CamelCase parts.
        matches = self._camel_case_regex.finditer(test_class)
        target_class_parts = [match.group(0) for match in matches]

        # Infer the module where the class exists from the test class name.
        target_module, target_length = self._infer_module(target_class_parts)
        if target_module is None:
            # Module not found
            msg = "Could not infer module from test class '{}'"
            self._warnings.append(msg.format(test_class))
            return None

        # Infer the class from the (remaining) test class name parts.
        target_class = self._infer_class(target_class_parts, target_module,
                                         target_length)
        if target_class is None:
            msg = "Could not infer class from test '{}' in module '{}'"
            self._warnings.append(msg.format(test_class, target_module))
            return None

        # Retrieve the methods in the inferred class, and register them as not 
        # yet covered.
        target_methods = {}
        for method, attribute in target_class.__dict__.iteritems():
            # Filter optional methods such as __init__, internal methods, 
            # properties and non-method variables. These would probably be 
            # covered by a test that has an inexactly-matching name such as 
            # "initialization" or "interface".
            if method.startswith('__'):
                continue
            if not isinstance(attribute, types.FunctionType):
                continue

            target_methods[method] = False

        return {
            "module": target_module,
            "class": target_class,
            "methods": target_methods
        }

    def _infer_module(self, target_class_parts):
        """
        Infer the module where an actual class may exist from the test class.

        The given `target_class_parts` is a list of strings that were collected
        from splitting a CamelCase test class name.

        Returns the inferred module name and the number of parts from the start
        of the `target_class_parts` that were used to build an existing module.
        If no module could be found, then `None` and `0` are returned.
        """

        target_module = None
        target_length = 0
        for module_length in range(len(target_class_parts)):
            # Make a module from the first few parts. Check if we can load this 
            # module; if so, then it is likely the module in which the actual 
            # class could exist.
            module = ''.join(target_class_parts[:module_length+1]).lower()
            try:
                self._import_manager.load(module)
            except ImportError:
                continue
            else:
                target_module = module
                target_length = module_length
                break

        return target_module, target_length

    def _infer_class(self, target_class_parts, target_module, target_length):
        """
        Infer the actual class that may exist in a module from the test class.

        The given `target_class_parts` is a list of strings that were collected
        from splitting a CamelCase test class name. `target_module` is a module
        name where the class might exist, which was inferred previously using
        `_infer_module`. The `target_length` are the number of parts used by the
        module inference.

        Returns the inferred class type, or `None` if none could be found.
        """

        target_class = None
        kw = {
            "relative_module": target_module
        }
        for class_length in range(target_length + 2):
            # Make a class name from the last few parts. We try to create 
            # a class using the module name (or a part of it) or without the 
            # inferred module name parts, but we never leave any part unused.
            class_name = '_'.join(target_class_parts[class_length:])
            try:
                target_class = self._import_manager.load_class(class_name, **kw)
            except ImportError:
                continue
            else:
                break

        return target_class

    def _convert_test_method(self, test_class, test_method):
        """
        Handle a test method with the name `test_method` in class `test_class`.

        This pulls the method name to some conversion steps to infer the method
        that it tests. Returns the actual method name if this is possible,
        otherwise it returns `None` and a warning will be added to the output of
        `show_result`.
        """

        target_class = self._classes[test_class]["class"]
        class_name = target_class.__name__
        methods = target_class.__dict__

        if test_method.startswith(self._method_prefix):
            test_method = test_method[len(self._method_prefix):]
            if test_method.startswith('_'):
                test_method = test_method[1:]

        target_method_parts = test_method.split('_')
        target_method = None
        for method_length in range(len(target_method_parts), 0, -1):
            method = '_'.join(target_method_parts[:method_length])
            if method == "interface":
                # Interface tests do not cover methods (or if they do, then we 
                # should specify this), so do not try to match it.
                return None

            if method == "initialization" or method in methods:
                target_method = method
                break
            elif "_{}".format(method) in methods:
                target_method = "_{}".format(method)
                break

        if target_method is None:
            msg = "Could not infer method from test function '{}.{}'"
            self._warnings.append(msg.format(class_name, test_method))

        return target_method
