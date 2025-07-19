"""Unit tests for SDWire CLI application."""

# This file makes the tests/unit directory a Python package
# and can contain common test utilities and imports.

import os
import sys

# Add the sdwire package to the Python path for testing
# This ensures tests can import sdwire modules even when running
# from the tests directory
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(test_dir))
sdwire_path = os.path.join(project_root, 'sdwire')

if sdwire_path not in sys.path:
    sys.path.insert(0, project_root)
