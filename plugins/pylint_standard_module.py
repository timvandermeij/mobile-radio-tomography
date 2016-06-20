# Plugin to consider modules in /usr/lib64/python2.7/site-packages or 
# equivalent path in a virtualenv or custom install to be non-standard 
# packages, rather than guessing that they are part of the core modules.

from functools import partial
import site
import astroid.modutils as modutils
import pylint.checkers.imports as imports

def is_standard_module(linter, modname, std_path=None):
    standard = linter._old_is_standard_module(modname, std_path=std_path)
    if standard:
        try:
            filename = modutils.file_from_modpath([modname])
        except ImportError:
            # Import failed, so we can suppose that the module is not standard.
            return False

        if filename is not None and '/site-packages/' in filename:
            return False

    return standard

def register(linter):
    if not hasattr(linter, '_old_is_standard_module'):
        linter._old_is_standard_module = modutils.is_standard_module
        new_is_standard_module = partial(is_standard_module, linter)
        modutils.is_standard_module = new_is_standard_module
        imports.is_standard_module = new_is_standard_module

        # Add the user site packages to external import locations, if it exists
        try:
            for checker in linter._checkers['imports']:
                checker._site_packages.update(site.getsitepackages())
                checker._site_packages.add(site.getusersitepackages())
        except AttributeError:
            # Running in a virtual environment, in which case there is no
            # `site.getusersitepackages()` method.
            pass
