import importlib
import sys
import types

class Import_Manager(object):
    """
    A manager for dynamically importing modules.
    """

    def __init__(self):
        """
        Initialize the import manager.
        """

        self._package = __package__.split('.')[0]
        self._unloaded_modules = {}

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

        If `module` is not given, then the module has the same name as the class
        name, relative to the base package. If `relative_module` is given, then
        the module is actually relative to this submodule, which in turn is
        relative to the package.

        If the module and class can be imported, then the class object is
        returned. Otherwise, an `ImportError` is raised.
        """

        if module is None:
            module = class_name

        import_module = self.load(module, relative_module=relative_module)
        try:
            return import_module.__dict__[class_name]
        except KeyError:
            raise ImportError("Cannot import class name '{}' from module '{}'".format(class_name, import_module.__name__))

    def unload(self, module, relative=True, store=True):
        """
        Unload the given `module` from Python.

        This removes the module from the module cache, meaning that a future
        import reimports the module.

        If `relative` is `True`, then the module is assumed to be relative to
        the base package. Otherwise, if `False` is given, then the module is
        a global or core module.

        Only use this when there are no other active modules that directly or
        indirectly reference the given module. Otherwise, their references may
        become corrupt. The module is stored in the import manager, unless
        `store` is `False`, until the import manager itself is dereferenced.
        However, this is no guarantee that the module will continue to function
        while it is unloaded. The stored module can be reloaded with `reload`
        using its `unloaded` argument.

        Returns `True` if the module was unloaded, or `False` if it was not
        loaded to begin with.
        """

        if relative:
            module = "{}.{}".format(self._package, module)

        if module not in sys.modules:
            return False

        if store:
            self._unloaded_modules[module] = sys.modules[module]

        del sys.modules[module]
        return True

    def reload(self, module, relative=True):
        """
        Reload a new version of the given `module` into Python.

        This method has two functions. The first and default option works
        similar to the `reload` builtin (or `importlib.reload` in Python 3),
        which replaces a previously imported module with an updated one.
        The difference with the core function is that the global module
        variables are discarded by this method, and the new module is completely
        fresh. The `module` to this function can a module name or module object.

        If `relative` is `True`, then the module name is assumed to be relative
        to the base package. Otherwise, if `False` is given, then the module is
        a global or core module. It is not recommended to reload a core module.
        The `relative` argument is ignored if `module` is a module object.

        Only use this `reload` method when there are no other active modules
        that directly or indirectly reference the given module. Otherwise, their
        references may become corrupt.

        If the module was not previously loaded via `load` or a normal import,
        then this method raises an `ImportError` to signal the import failure.
        """

        if isinstance(module, types.ModuleType):
            module = module.__name__
            relative = False

        if not self.unload(module, relative=relative, store=False):
            raise ImportError("Module '{}' was not previously loaded".format(module))

        return self.load(module, relative=relative)

    def reload_unloaded(self, module, relative=True):
        """
        Reregister the given `module` that was unloaded with `unload`.

        When a module is unloaded, then it is in a corrupt state where it may
        not have access to its own variables, nor do references to anything
        from that unloaded module. One way that could fix this is to register
        the module again, which this method does.

        If the module was imported normally in between `unload` and `reload`,
        then this version of the module is in fact dereferenced, and may also
        become corrupt if it is still referenced elsewhere. The "old" version
        of the module takes its place in the registry, and should become
        usable again.

        If the module was not previously unloaded via `unload`, then this method
        raises an `ImportError` to signal the import failure. Otherwise, this
        method returns the reloaded module object.
        """

        if relative:
            module = "{}.{}".format(self._package, module)

        if module not in self._unloaded_modules:
            raise ImportError("Module '{}' was not previously unloaded".format(module))

        sys.modules[module] = self._unloaded_modules[module]
        del self._unloaded_modules[module]

        return sys.modules[module]
