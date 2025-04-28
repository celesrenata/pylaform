import unittest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import ImmutableMultiDict
from tests.pylaform_test_case import PylaformTestCase
from tests.mock_setup import setup_app_mocks

class TestEducationFrontend(PylaformTestCase):
    """Test the education frontend functionality"""

    def setUp(self):
        """Set up test environment"""
        super().setUp()
        
        # Setup app mocks if needed
        self.app_mocks = setup_app_mocks()
        
        # Mock education data for testing
        self.mock_education_data = [
            {'id': 'school_1', 'attr': 'schoolname', 'value': 'Test University', 'state': 1},
            {'id': 'school_1', 'attr': 'location', 'value': 'Test City', 'state': 1},
            {'id': 'focus_1', 'attr': 'focusname', 'value': 'Computer Science', 'state': 1},
            {'id': 'focus_1', 'attr': 'school', 'value': 'school_1', 'state': 1},
            {'id': 'focus_1', 'attr': 'startdate', 'value': '2020-01-01', 'state': 1},
            {'id': 'focus_1', 'attr': 'enddate', 'value': '2024-01-01', 'state': 1},
        ]

    def test_update_education_dates(self):
        """Test updating dates in education entries"""
        # Prepare form data with modified dates
        form_data = ImmutableMultiDict([
            ('focus_1_focus_startdate', '2021-02-01'),  # Changed date
            ('focus_1_focus_enddate', '2025-03-01'),    # Changed date
            ('focus_1_focus_name', 'Computer Science'),
            ('school_1_school_name', 'Test University'),
            ('school_1_school_location', 'Test City'),
            ('school_1_rowid', 'school_1'),
            ('focus_1_rowid', 'focus_1')
        ])
        
        # Test that date formatting works properly
        with patch('pylaform.commands.templateWorker.date_adapter') as mock_date_adapter:
            mock_date_adapter.side_effect = lambda x: x  # Just return the input
            
            # Call the method
            self.worker.update_education(form_data)
            
            # Verify date_adapter was called with the expected dates
            mock_date_adapter.assert_any_call('2021-02-01')
            mock_date_adapter.assert_any_call('2025-03-01')

    def test_delete_education(self):
        """Test deleting an education entry"""
        # Prepare form data with delete flags
        form_data = ImmutableMultiDict([
            ('school_1_delete', 'true'),
            ('focus_1_delete', 'true')
        ])

        # Mock the necessary methods to test deletion
        with patch.object(self.worker.delete, 'delete_target') as mock_delete:
            # Call update_education
            self.worker.update_education(form_data)

            # Verify delete_target was called for both entries
            expected_calls = [
                unittest.mock.call('1', 'school'),
                unittest.mock.call('1', 'focus')
            ]
            mock_delete.assert_has_calls(expected_calls, any_order=True)

    def test_add_new_education(self):
        """Test adding a new education entry"""
        # Prepare form data for a new education entry
        form_data = ImmutableMultiDict([
            ('new_school_name', 'New University'),
            ('new_school_location', 'New City'),
            ('new_school_enabled', 'on'),
            ('new_focus_name', 'New Degree'),
            ('new_focus_startdate', '2023-01-01'),
            ('new_focus_enddate', '2027-01-01'),
            ('new_focus_enabled', 'on'),
            ('new_rowid', 'new')
        ])

        # Mock insert and query_id methods
        with patch.object(self.worker.insert, 'multi_column') as mock_insert, \
                patch.object(self.worker.query, 'query_id', return_value=99) as mock_query_id:
            # Call update_education
            self.worker.update_education(form_data)

            # Verify the school was inserted
            mock_insert.assert_any_call('school',
                                        name='New University',
                                        location='New City',
                                        state=1)

            # Verify the focus was inserted with the new school id
            mock_insert.assert_any_call('focus',
                                        school=99,
                                        name='New Degree',
                                        startdate='2023-01-01',
                                        enddate='2027-01-01',
                                        state=1)

            # Verify query_id was called to look up the new school
            mock_query_id.assert_called_with('New University', 'school')

    def test_education_route_get(self):
        """Test the education route with GET request"""
        # Use the already mocked app.education function
        app_education = self.app_mocks['education']
        
        # Set up mock request
        self.app_mocks['request'].method = 'GET'
        
        # Call the education route
        app_education()
        
        # Verify render_template was called
        self.app_mocks['render_template'].assert_called_once()
        
        # Verify template name
        template_name = self.app_mocks['render_template'].call_args[0][0]
        self.assertEqual(template_name, 'education_index.html')
        
        # Verify query.get_education was called
        self.app_mocks['query'].get_education.assert_called_once()
        
        # Verify worker.dropdowns was called
        self.app_mocks['worker'].dropdowns.assert_called_with('education')