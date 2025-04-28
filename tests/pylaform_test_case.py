import unittest
from unittest.mock import patch, MagicMock
import os
from test_database_manager import TestDatabaseManager


class PylaformTestCase(unittest.TestCase):
    """Base test case for Pylaform tests"""

    def setUp(self):
        """Set up test case - create mocks and patches for database connection"""
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

        # Now import and initialize classes with the patched DB connection
        from pylaform.commands.templateWorker import Worker
        from pylaform.commands.db.query import Queries

        self.worker = Worker()
        self.query = Queries()

    def tearDown(self):
        """Clean up after each test"""
        # Stop the patcher
        self.db_patcher.stop()