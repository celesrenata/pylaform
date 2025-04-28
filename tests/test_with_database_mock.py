import unittest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import ImmutableMultiDict
from pylaform.utilities.commands import date_adapter


class TestWithDatabaseMock(unittest.TestCase):
    """Test class that mocks database connections"""

    def setUp(self):
        """Set up before each test - create mocks and patches"""
        # Create the patcher for the database connection
        self.db_patcher = patch('pylaform.commands.db.connect.db')
        # Start the patcher and store the mock
        self.mock_db = self.db_patcher.start()

        # Create a mock connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor

        # Have the mock db function return our mock connection
        self.mock_db.return_value = self.mock_connection

    def tearDown(self):
        """Clean up after each test"""
        # Stop the patcher
        self.db_patcher.stop()

    def test_update_education_with_mock(self):
        """Test the update_education method with a mocked database"""
        from pylaform.commands.templateWorker import Worker

        # Create a form similar to what would be submitted by the form
        form_data = ImmutableMultiDict([
            ("1_focus_dropdown", "EDIT"),
            ("1_focus_name", "Photography"),
            ("1_focus_startdate", "2005-01-01"),
            ("1_focus_enddate", "2007-12-01"),
            ("1_focus_enabled", "on"),
            ("1_rowid", "focus_1"),
            ("1_school_dropdown", "1"),  # Add school info
            ("1_school_name", "Bellevue College"),
            ("1_school_location", "Bellevue, WA"),
            ("1_school_enabled", "on")
        ])

        # Configure mock cursor to handle our test case
        # When executing queries, just return empty result sets
        self.mock_cursor.execute.return_value = self.mock_cursor
        self.mock_cursor.fetchall.return_value = []

        # Use patching to track calls to date_adapter
        with patch('pylaform.commands.templateWorker.date_adapter', wraps=date_adapter) as mock_date_adapter:
            # Initialize Worker (constructor will use our mocked db connection)
            worker = Worker()

            # Mock the query_id method to return a valid ID for our school
            with patch.object(worker.query, 'query_id', return_value=1):
                # Call update_education with our test form data
                worker.update_education(form_data)

            # Check if date_adapter was called with the correct dates
            date_calls = [call[0][0] for call in mock_date_adapter.call_args_list]
            print(f"Date adapter was called with: {date_calls}")

            # Check if "2007-12-01" was included in the calls
            self.assertIn("2007-12-01", date_calls,
                          "date_adapter should be called with '2007-12-01'")


if __name__ == '__main__':
    unittest.main()