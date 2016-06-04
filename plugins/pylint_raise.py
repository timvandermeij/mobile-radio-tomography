# Plugin to allow bare and broad except clauses when the body calls an 
# interrupt handler method/function with a specific name.

from functools import partial
import astroid
import pylint.checkers.exceptions as exceptions
import pylint.checkers.utils as utils

def is_raising(linter, body):
    for node in body:
        if isinstance(node, astroid.Expr) and isinstance(node.value, astroid.Call):
            func = utils.safe_infer(node.value.func)
            print(func.name)
            if func.name in ("destroy", "interrupt"):
                return True

    return linter._old_is_raising(body)

def register(linter):
    if not hasattr(linter, '_old_is_raising'):
        linter._old_is_raising = utils.is_raising
        new_is_raising = partial(is_raising, linter)
        exceptions.is_raising = new_is_raising
        utils.is_raising = new_is_raising
