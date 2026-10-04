import os
import sys
import unittest

# Ensure backend/src and backend/ are on python path
BACKEND_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "src"))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_SRC not in sys.path:
    sys.path.insert(0, BACKEND_SRC)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def load_tests(loader, standard_tests, pattern):
    backend_tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "tests"))
    suite = loader.discover(start_dir=backend_tests_dir, top_level_dir=BACKEND_ROOT, pattern="test_*.py")
    standard_tests.addTests(suite)
    return standard_tests
