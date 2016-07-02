import re
import types
import unittest
from mock import patch, MagicMock

__all__ = ["covers", "Method_Coverage"]

# Global coverage tracking dictionaries that are filled with the decorator 
# patterns found during Python interpretation of the tests.
_class_coverage = {}
_function_coverage = {}

def covers(target):
    """
    Decorator for specifying a specific coverage target.

    This decorator can be used in two ways: as a class decorator and as method
    decorator. For the class decorator, one can change which class a test class
    is supposed to be testing. This is useful if the test class name does not
    match enough with the actual class name for this relation to be inferred.
    For example, if the class name is `MyInt` but the test class is `TestInts`,
    then, assuming `MyInt` is imported into the test case, the class coverage
    can be declared with:
    ```
    @covers(MyInt)
    class TestInts(unittest.TestCase):
        pass
    ```
    One can also provide the class name as a string if the class is not imported
    in the test at that point, using dot syntax for relative modules, but this
    is not recommended since the inference can fail more easily.

    The second case is similar, but affirms a relationship between a test method
    and an actual method in the class to be tested. For example, if `MyInt` has
    a method called `add`, but the test method is called `test_operations`, then
    we can declare the method coverage with:
    ```
    @covers(MyInt)
    class TestInts(unittest.TestCase):
        @covers("add")
        def test_operations(self):
            something = MyInt(5)
            self.assertEqual(something.add(1), MyInt(6))
    ```

    Method decorators can be stacked so that they cover multiple methods. Thus,
    if `test_operations` also tests a `substract` method of `MyInt`, then we
    can just add another `@covers("subtract")` line before the definition. This
    is not the case for the class decorator, which can only cover one class.
    """

    def decorator(subject):
        # `subject` is the test class or test function that is being decorated, 
        # which `target` is the actual class or method name that is covered by 
        # this test.
        # Note: At this point we cannot deduce which class a test function 
        # belongs to, because the class is not yet fully instantiated. However, 
        # once we do have the full class and instance methods, then we can 
        # easily compare the instance method's internal function with the 
        # function that we caught here. Also, because class types and functions 
        # are hashable, we can use dictionaries for easy lookups.
        if isinstance(subject, type):
            # Class coverage
            _class_coverage[subject] = target
        elif isinstance(subject, types.FunctionType):
            # Method coverage
            if subject not in _function_coverage:
                _function_coverage[subject] = []

            _function_coverage[subject].append(target)

        return subject

    return decorator

class Method_Coverage(object):
    """
    Method coverage tracker.
    """

    def __init__(self, arguments, import_manager):
        """
        Set up the method coverage tracker.

        The given `arguments` is an `Arguments` object.
        The given `import_manager` is an `Import_Manager` object for the package
        where the tests are run.
        """

        self._import_manager = import_manager

        settings = arguments.get_settings("test_method_coverage")
        # A prefix that is removed from a test class when we infer an actual 
        # class from it.
        self._class_prefix = settings.get("test_class_prefix")
        # A prefix that is removed from a test method when we infer an actual 
        # method from it. In addition, underscores after it are also removed.
        self._method_prefix = settings.get("test_method_prefix")
        # Method names for tests that cover an `__init__`  method
        self._init_test_methods = settings.get("init_test_methods")
        # Method name for tests that cover all properties of a class.
        self._interface_test_methods = settings.get("interface_test_methods")

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
        # - "properties": A list of property names. These names match with keys
        #   in "methods". All properties are covered if there is a test method
        #   with the `interface_test_method` name.
        self._classes = {}

        # Warnings that were generated during the inference process, grouped by 
        # the relevant test class name.
        self._warnings = {}

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

    def _add_warning(self, test_class, warning):
        """
        Add a warning message `warning` related to the class name `test_class`.
        """

        if test_class not in self._warnings:
            self._warnings[test_class] = []

        self._warnings[test_class].append(warning)

    def get_results(self):
        """
        Format the results of the method coverage.

        The returned string contains warnings found during the test class
        inference process, the coverage statistics and untested methods.
        """

        out = ""

        total_methods = 0
        total_covered = 0

        for test_class, data in sorted(self._classes.iteritems(),
                                       key=lambda pair: pair[0]):
            name = self._get_test_class_name(test_class)
            if name in self._warnings:
                warnings = "\n".join(self._warnings[name]) + "\n"
            else:
                warnings = ""

            if data is None:
                out += "\n{}: {}".format(test_class,
                                         warnings if warnings else "no data")
                continue

            module_name = data["module"]
            class_name = data["class"].__name__
            total = len(data["methods"])
            covered = sum(data["methods"].values())

            total_methods += total
            total_covered += covered
            if total == 0 or total == covered:
                continue

            stats_format = "\n{} -> {}.{}: {}/{} ({:.0%})\n"
            out += stats_format.format(test_class, module_name, class_name,
                                       covered, total, covered / float(total))
            out += warnings

            if covered < total:
                missing_methods = []
                for method, found in sorted(data["methods"].iteritems(),
                                            key=lambda pair: pair[0]):
                    if not found:
                        missing_methods.append(method)

                out += "Missed methods: {}\n".format(', '.join(missing_methods))

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
            self._classes[test_class] = self._convert_test(test)

        if self._classes[test_class] is None:
            return

        target_methods = self._convert_test_method(test, test_method)
        for target_method in target_methods:
            if target_method not in self._classes[test_class]["methods"]:
                msg = "Test method '{}' covers nonexistent method '{}'"
                self._add_warning(self._get_test_class_name(test_class),
                                  msg.format(test_method, target_method))
            else:
                self._classes[test_class]["methods"][target_method] = True

    def _convert_test(self, test):
        """
        Handle the test class `test` to deduce module, class and methods
        for the actual class that it tests.

        This pulls the class name through various inference steps to retrieve
        an actual class, and then retrieves the methods in that class.

        If the actual class can be inferred, then this returns a dictionary
        containing the inferred module name, actual class type and methods to be
        covered. If any of the steps fail, then `None` is returned and a warning
        will be added to the output in `get_results`. 
        """

        target_module, target_class = self._convert_test_class(test)
        if target_module is None or target_class is None:
            return None

        # Retrieve the methods in the inferred class, and register them as not 
        # yet covered. We only consider methods implemented in that class, not 
        # inherited methods from superclasses.
        target_methods = {}
        target_properties = []
        for method, attribute in target_class.__dict__.iteritems():
            # Filter internal methods and non-methods such as class variables. 
            if method.startswith('__') and method != "__init__":
                continue

            if isinstance(attribute, property):
                target_properties.append(method)
            elif not isinstance(attribute, types.FunctionType):
                continue

            target_methods[method] = False

        return {
            "module": target_module,
            "class": target_class,
            "methods": target_methods,
            "properties": target_properties
        }

    def _convert_test_class(self, test):
        """
        Handle the test case object `test` to deduce a module and class type.

        This pulls the class name through various inference steps to retrieve
        an actual class.

        If the actual class can be inferred, then this returns a tuple of
        the inferred module name and actual class type. If one or both of these
        cannot be inferred, then one or both will be `None` and a warning will
        be added to the output of `get_results`.
        """

        # Check if the test class is decorated with a `covers` decorator, and 
        # the decorator holds a valid class.
        if test.__class__ in _class_coverage:
            target_class = _class_coverage[test.__class__]
            if isinstance(target_class, str):
                match = re.match(r'(?:(.*)\.)?([^\.]*)', target_class)
                target_module, class_name = match.groups()
                target_class = self._load_class(target_module, class_name)
                return target_module, target_class

            if not isinstance(target_class, type):
                return None, None

            target_module = target_class.__module__
            return target_module, target_class

        # Convert the test class name.
        test_class = self._get_test_class_name(test.__class__.__name__)

        # Split the class name into its CamelCase parts.
        matches = self._camel_case_regex.finditer(test_class)
        target_class_parts = [match.group(0) for match in matches]

        # Infer the module where the class exists from the test class name.
        target_module, target_length = self._infer_module(target_class_parts)
        if target_module is None:
            # Module not found
            msg = "Could not infer module from test class '{}'"
            self._add_warning(test_class, msg.format(test_class))
            return None, None

        # Infer the class from the (remaining) test class name parts.
        target_class = self._infer_class(target_class_parts, target_module,
                                         target_length)
        if target_class is None:
            msg = "Could not infer class in module '{}'"
            self._add_warning(test_class, msg.format(target_module))

        return target_module, target_class

    def _get_test_class_name(self, test_class):
        """
        Return the class name from the name `test_class`, excluding the prefix.
        """

        if test_class.startswith(self._class_prefix):
            test_class = test_class[len(self._class_prefix):]

        return test_class

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
        for class_length in range(target_length + 2):
            # Make a class name from the last few parts. We try to create 
            # a class using the module name (or a part of it) or without the 
            # inferred module name parts, but we never leave any part unused.
            class_name = '_'.join(target_class_parts[class_length:])
            target_class = self._load_class(target_module, class_name)
            if target_class is not None:
                break

        return target_class

    def _load_class(self, module, class_name):
        """
        Attempt to load a class with name `class_name` from `module`.

        Returns the class type if it could be loaded, otherwise this method
        returns `None`.
        """

        try:
            return self._import_manager.load_class(class_name,
                                                   relative_module=module)
        except ImportError:
            return None

    def _convert_test_method(self, test, test_method):
        """
        Handle a test method with the name `test_method` in test case `test`.

        This pulls the method name to some conversion steps to infer the methods
        that it tests. Returns a list with actual method names if this is
        possible, otherwise it returns an empty list and a warning will be
        added to the output of `get_results`.
        """

        target_methods = []
        test_function = getattr(test, test_method).im_func
        if test_function in _function_coverage:
            target_methods = _function_coverage[test_function]

        test_class = test.__class__.__name__
        target_class = self._classes[test_class]["class"]
        methods = target_class.__dict__

        if test_method.startswith(self._method_prefix):
            test_method = test_method[len(self._method_prefix):]
            if test_method.startswith('_'):
                test_method = test_method[1:]

        target_method_parts = test_method.split('_')
        target_method = None
        for method_length in range(len(target_method_parts), 0, -1):
            method = '_'.join(target_method_parts[:method_length])
            if method in self._interface_test_methods:
                # An interface test does not cover methods (or if it does, then 
                # we should specify this via decorators), so do not match the 
                # method name automatically. However, an interface test is 
                # expected to cover all properties.
                target_methods.extend(self._classes[test_class]["properties"])
                break

            if method in self._init_test_methods:
                target_method = "__init__"
            elif method in methods:
                target_method = method
            elif "_{}".format(method) in methods:
                target_method = "_{}".format(method)

            if target_method is not None:
                break

        if target_method is not None:
            target_methods.append(target_method)
        if not target_methods:
            msg = "Could not infer method from test function '{}'"
            self._add_warning(self._get_test_class_name(test_class),
                              msg.format(test_method))

        return target_methods
