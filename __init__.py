# Initialize root directory as a package so that import .. works in subpackages

if __name__ in ["__main__", "__builtin__", "__init__"]:
    if __package__ is None:
        import sys
        import os
        path = os.path.dirname(os.path.abspath(__file__))
        name = os.path.basename(path)
        sys.path.append(os.path.dirname(path))
        sys.modules[name] = __import__(name)
        __package__ = name

__all__ = []
