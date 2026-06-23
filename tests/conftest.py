"""Shared pytest fixtures and path setup."""

import os
import sys

# Make `lambdas` importable as a package and `common` importable from within it.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lambdas"))
