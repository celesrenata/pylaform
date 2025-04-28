# tests/pylaform_test_environment.py
"""Setup proper test environment for PylaForm tests"""
import sys
import os
from unittest.mock import MagicMock

# Create mocks for app and modules before they get imported by other tests
mock_app = MagicMock()

# Add mock to sys.modules
sys.modules['pylaform.app'] = mock_app
sys.modules['pylaform.app.worker'] = MagicMock()
sys.modules['pylaform.app.query'] = MagicMock()

# You can add other module mocks as needed