# tests/test_education_integration_fixed.py
import unittest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import ImmutableMultiDict
from pylaform.utilities.commands import date_adapter


class TestEducationIntegration(unittest.TestCase):
    """Integration tests for education functionality"""

    def setUp(self):
        """Set up test environment"""
        # Create database connection patcher
        self.db_patcher = patch('pylaform.commands.db.connect.db')
        self.mock_db = self.db_patcher.start()

        # Create mock connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_db.return_value = self.mock_connection

        # Import worker after patching database
        from pylaform.commands.templateWorker import Worker
        self.worker = Worker()

        # Create mocks for worker components
        self.worker.query = MagicMock()
        self.worker.update = MagicMock()
        self.worker.insert = MagicMock()
        self.worker.delete = MagicMock()

        # Configure query mock
        self.worker.query.get_education.return_value = [
            {'id': 'school_1', 'attr': 'schoolname', 'value': 'Test University', 'state': 1},
            {'id': 'school_1', 'attr': 'location', 'value': 'Test City', 'state': 1},
            {'id': 'focus_1', 'attr': 'focusname', 'value': 'Computer Science', 'state': 1},
            {'id': 'focus_1', 'attr': 'school', 'value': 'school_1', 'state': 1},
            {'id': 'focus_1', 'attr': 'startdate', 'value': '2020-01-01', 'state': 1},
            {'id': 'focus_1', 'attr': 'enddate', 'value': '2024-01-01', 'state': 1}
        ]
        self.worker.query.query_id.return_value = 1

    def tearDown(self):
        """Clean up after each test"""
        self.db_patcher.stop()

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

        # Call update_education
        self.worker.update_education(form_data)

        # Verify update.multi_column was called for focus with correct dates
        update_calls = self.worker.update.multi_column.call_args_list

        # Find the focus update call with date values
        focus_date_call = False
        for call in update_calls:
            args, kwargs = call
            if args[0] == 'focus' and 'startdate' in kwargs and 'enddate' in kwargs:
                focus_date_call = True
                self.assertEqual(kwargs['startdate'], '2021-05-15')
                self.assertEqual(kwargs['enddate'], '2025-12-31')
                break

        self.assertTrue(focus_date_call, "No focus update call found with the expected dates")

    def test_delete_education_entry(self):
        """Test deleting an education entry"""
        # Create form data with delete flags
        form_data = ImmutableMultiDict([
            ('school_1_delete', 'true'),
            ('focus_1_delete', 'true')
        ])

        # Call update_education
        self.worker.update_education(form_data)

        # Verify delete_target was called twice (once for school, once for focus)
        self.assertEqual(self.worker.delete.delete_target.call_count, 2,
                         "delete_target should be called twice")

        # Verify the specific delete calls
        delete_calls = [call[0] for call in self.worker.delete.delete_target.call_args_list]
        focus_delete = ('1', 'focus') in delete_calls
        school_delete = ('1', 'school') in delete_calls

        self.assertTrue(focus_delete, "Should have called delete_target for focus")
        self.assertTrue(school_delete, "Should have called delete_target for school")