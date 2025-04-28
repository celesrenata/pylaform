# tests/mock_setup.py
import unittest
from unittest.mock import patch, MagicMock
import sys
import types


def setup_app_mocks():
    """Set up mock objects for app-related testing"""
    # Create the mock app module
    mock_app = types.ModuleType('app')

    # Create mock objects
    mock_worker = MagicMock(name='mock_worker')
    mock_query = MagicMock(name='mock_query')
    mock_request = MagicMock(name='mock_request')
    mock_render_template = MagicMock(name='mock_render_template')

    # Create a mock education function that uses the mocks
    def mock_education():
        if mock_request.method == 'GET':
            education_data = mock_query.get_education()
            dropdowns = mock_worker.dropdowns('education')
            return mock_render_template('education_index.html', payload=education_data, ddpayload=dropdowns)
        else:  # POST
            mock_worker.update_education(mock_request.form)
            mock_query.purge_cache('education')
            education_data = mock_query.get_education()
            dropdowns = mock_worker.dropdowns('education')
            return mock_render_template('education_index.html', payload=education_data, ddpayload=dropdowns)

    # Add attributes to the mock app module
    mock_app.worker = mock_worker
    mock_app.query = mock_query
    mock_app.request = mock_request
    mock_app.render_template = mock_render_template
    mock_app.education = mock_education

    # Setup default configurations for the mocks
    mock_query.get_education.return_value = {
        'payload': [
            {'id': 'school_1', 'attr': 'schoolname', 'value': 'Test University', 'state': 1},
            {'id': 'school_1', 'attr': 'location', 'value': 'Test City', 'state': 1},
            {'id': 'focus_1', 'attr': 'focusname', 'value': 'Computer Science', 'state': 1},
            {'id': 'focus_1', 'attr': 'school', 'value': 'school_1', 'state': 1},
            {'id': 'focus_1', 'attr': 'startdate', 'value': '2020-01-01', 'state': 1},
            {'id': 'focus_1', 'attr': 'enddate', 'value': '2024-01-01', 'state': 1}
        ]
    }

    # Mock dropdowns
    mock_worker.dropdowns.return_value = {
        "school": {"options": []},
        "focus": {"options": []}
    }

    # Register the mock app in sys.modules
    sys.modules['pylaform.app'] = mock_app

    # Return all mocks for test access
    return {
        'app': mock_app,
        'worker': mock_worker,
        'query': mock_query,
        'request': mock_request,
        'render_template': mock_render_template,
        'education': mock_education
    }