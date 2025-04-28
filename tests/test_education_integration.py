# tests/test_education_integration.py
import unittest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import ImmutableMultiDict
from pylaform.commands.templateWorker import Worker
from pylaform.utilities.commands import date_adapter
from tests.mock_setup import setup_app_mocks
from tests.pylaform_test_case import PylaformTestCase


class TestEducationIntegration(PylaformTestCase):
    """Integration tests for education functionality"""

    def setUp(self):
        """Set up test environment"""
        # Call parent setup to set up database mocks
        super().setUp()

        # Setup app mocks
        self.app_mocks = setup_app_mocks()

        # Create a mock query to track method calls
        self.original_query = self.worker.query
        self.mock_query = MagicMock()
        self.mock_query.get_education.return_value = [
            {'id': 'school_1', 'attr': 'schoolname', 'value': 'Test University', 'state': 1},
            {'id': 'school_1', 'attr': 'location', 'value': 'Test City', 'state': 1},
            {'id': 'focus_1', 'attr': 'focusname', 'value': 'Computer Science', 'state': 1},
            {'id': 'focus_1', 'attr': 'school', 'value': 'school_1', 'state': 1},
            {'id': 'focus_1', 'attr': 'startdate', 'value': '2020-01-01', 'state': 1},
            {'id': 'focus_1', 'attr': 'enddate', 'value': '2024-01-01', 'state': 1}
        ]

    # The rest of your test methods can remain the same
    def test_date_formatting(self):
        """Test date formatting function"""
        # Test various date format scenarios
        test_dates = [
            ("2022-01-01", "2022-01-01"),  # Normal date
            ("", "9999-01-01"),  # Empty date
            ("hidden", "0001-01-01")  # Hidden date
        ]

        for input_date, expected_output in test_dates:
            actual_output = date_adapter(input_date)
            self.assertEqual(actual_output, expected_output,
                             f"Expected '{input_date}' to be converted to '{expected_output}'")

    def test_update_education_with_dates(self):
        """Test updating dates in education"""
        # Create form data with updated dates
        form_data = ImmutableMultiDict([
            ('focus_1_focus_startdate', '2021-05-15'),
            ('focus_1_focus_enddate', '2025-12-31'),
            ('focus_1_focus_name', 'Computer Science'),
            ('focus_1_rowid', 'focus_1'),
            ('school_1_school_name', 'Test University'),
            ('school_1_school_location', 'Test City'),
            ('school_1_rowid', 'school_1')
        ])

        # Mock the DB operations
        with patch.object(self.worker.update, 'multi_column') as mock_update:
            # Call update_education
            self.worker.update_education(form_data)

            # Verify update.multi_column was called for focus with correct dates
            update_calls = mock_update.call_args_list

            # Find the focus update call
            focus_update_call = None
            for call in update_calls:
                args, kwargs = call
                if args[0] == 'focus':
                    focus_update_call = call
                    break

            # Verify the call was made
            self.assertIsNotNone(focus_update_call, "Focus update call not found")

            # Check date values in the update call
            _, kwargs = focus_update_call
            self.assertEqual(kwargs.get('startdate', None), '2021-05-15')
            self.assertEqual(kwargs.get('enddate', None), '2025-12-31')

    def test_delete_education_entry(self):
        """Test deleting an education entry"""
        # Create form data with delete flags
        form_data = ImmutableMultiDict([
            ('school_1_delete', 'true'),
            ('focus_1_delete', 'true')
        ])

        # Mock the delete method
        with patch.object(self.worker.delete, 'delete_target') as mock_delete:
            # Call update_education
            self.worker.update_education(form_data)

            # Verify delete_target was called twice (once for school, once for focus)
            self.assertEqual(mock_delete.call_count, 2, "delete_target should be called twice")

            # Verify the specific delete calls
            expected_calls = [
                unittest.mock.call('1', 'school'),
                unittest.mock.call('1', 'focus')
            ]
            mock_delete.assert_has_calls(expected_calls, any_order=True)