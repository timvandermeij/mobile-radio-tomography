import importlib
import sys

class Import_Manager(object):
    """
    A manager for dynamically importing modules.
    """

    def __init__(self):
        """
        Initialize the import manager.
        """

        self._package = __package__.split('.')[0]

    @property
    def package(self):
        """
        Retrieve the base package of the import manager.
        """

        return self._package

    def load(self, module, relative=True, relative_module=None):
        """
        Import the given `module` and return the module object.

        If `relative` is `True`, then the module is assumed to be relative to
        the base package. If `relative_module` is given, then it is relative
        to this submodule instead. Otherwise, if `relative` is `False`, then
        the module is a global or core module.
        """

        if relative_module is not None:
            module = "{}.{}.{}".format(self._package, relative_module, module)
        elif relative:
            module = "{}.{}".format(self._package, module)

        try:
            return importlib.import_module(module)
        except ImportError as e:
            raise ImportError("Cannot import module '{}': {}".format(module, e.message))

    def load_class(self, class_name, module=None, relative_module=None):
        """
        Import the class with the given `class_name` from a certain module
        relative to the base package.

        If `module` is not given, then the module is this module relative to
        the base package. Otherwise, if `relative_module` is given, then the
        module has the same name as the class name, but relative to this
        submodule, which in turn is relative to the package. Otherwise,
        the module is the class name relative to the package.

        If the module and class can be imported, then the class object is
        returned. Otherwise, an `ImportError` is raised. Providing both
        `module` and `relative_module` raises a `ValueError`.
        """

        if module is None:
            module = class_name
        elif relative_module is not None:
            raise ValueError("At most one of `module` and `relative_module` can be provided")

        import_module = self.load(module, relative_module=relative_module)
        try:
            return import_module.__dict__[class_name]
        except KeyError:
            raise ImportError("Cannot import class name '{}' from module '{}.{}'".format(class_name, self._package, module))

    def unload(self, module, relative=True):
        """
        Unload the given `module` from Python.

        This removes the module from the module cache, meaning that a future
        import reimports the module.

        If `relative` is `True`, then the module is assumed to be relative to
        the base package. Otherwise, if `False` is given, then the module is
        a global or core module.

        Only use this when there are no other active modules that directly or
        indirectly reference the given module. Otherwise, their references may
        become corrupt.
        """

        if relative:
            module = "{}.{}".format(self._package, module)

        if module in sys.modules:
            del sys.modules[module]
