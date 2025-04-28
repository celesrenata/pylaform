# tests/test_db_connect.py
import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
from pylaform_test_case import PylaformTestCase


class TestDbConnect(unittest.TestCase):
    """Test the database connection module"""

    @patch('os.path.exists')
    @patch('shutil.copyfile')
    def test_db_connection_missing_file(self, mock_copyfile, mock_exists):
        """Test database connection when the file doesn't exist"""
        # Configure mocks
        mock_exists.return_value = False

        # Import the module
        from pylaform.commands.db import connect

        # Mock the sqlite3.connect function
        with patch('sqlite3.connect') as mock_sqlite_connect:
            mock_connection = MagicMock()
            mock_sqlite_connect.return_value = mock_connection

            # Call the db function
            result = connect.db()

            # Verify the file existence was checked
            mock_exists.assert_called_once()

            # Verify copyfile was called
            mock_copyfile.assert_called_once()

            # Verify sqlite3.connect was called
            mock_sqlite_connect.assert_called_once()

            # Verify the returned value is the mock connection
            self.assertEqual(result, mock_connection)