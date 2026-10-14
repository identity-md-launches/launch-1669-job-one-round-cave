#!/usr/bin/env python3
"""Run an inherited unittest command, confining temporary directories to scratch."""
from pathlib import Path
import sys
import tempfile
import unittest

scratch = Path('test/scratch').resolve()
scratch.mkdir(parents=True, exist_ok=True)
original = tempfile.TemporaryDirectory

def temporary(*args, **kwargs):
    kwargs['dir'] = scratch
    return original(*args, **kwargs)

tempfile.TemporaryDirectory = temporary
if __name__ == '__main__':
    unittest.main(module=None, argv=['unittest'] + sys.argv[1:])
