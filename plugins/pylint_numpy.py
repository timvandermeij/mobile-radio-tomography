# Plugin to let pylint's AST parser know which attributes exist in numpy arrays
# Based on https://www.logilab.org/blogentry/78354 and 
# https://docs.pylint.org/plugins.html
from astroid import MANAGER, nodes
from astroid.builder import AstroidBuilder

def transform(module):
    if module.name == 'numpy':
        fake = AstroidBuilder(manager=MANAGER).string_build('''
import numpy
class array(numpy.ndarray):
    pass

class recarray(numpy.ndarray):
    pass
''')

        for name in ("array", "recarray"):
            module.locals[name] = fake.locals[name]

def register(linter):
    """
    Register new linter checkers and transformers
    Called when loaded by pylint's load-plugins option.
    We register our tranformation function here.
    """

    MANAGER.register_transform(nodes.Module, transform)
