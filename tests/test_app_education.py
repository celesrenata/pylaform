# tests/test_app_education.py
import unittest
from werkzeug.datastructures import ImmutableMultiDict
from tests.mock_setup import setup_app_mocks


class TestAppEducation(unittest.TestCase):
    """Test education route functionality"""

    def setUp(self):
        """Set up test environment"""
        # Setup mocks
        self.mocks = setup_app_mocks()

    def test_education_get_route(self):
        """Test the GET route for education"""
        # Configure request.method to be 'GET'
        self.mocks['request'].method = 'GET'

        # Call the education route function
        self.mocks['education']()

        # Verify render_template was called with the right parameters
        self.mocks['render_template'].assert_called_once()
        args, kwargs = self.mocks['render_template'].call_args

        # Check template name
        self.assertEqual(args[0], 'education_index.html')

        # Check payload structure
        self.assertIn('payload', kwargs)
        self.assertIn('ddpayload', kwargs)

    def test_education_post_route(self):
        """Test the POST route for education"""
        # Configure request to be POST with form data
        self.mocks['request'].method = 'POST'
        self.mocks['request'].form = ImmutableMultiDict([
            ('focus_1_focus_startdate', '2021-05-15'),
            ('focus_1_focus_enddate', '2025-12-31')
        ])

        # Call the education route function directly from the mock
        self.mocks['education']()

        # Verify worker.update_education was called with the form data
        self.mocks['worker'].update_education.assert_called_once_with(self.mocks['request'].form)

        # Verify cache was purged
        self.mocks['query'].purge_cache.assert_called_once_with('education')