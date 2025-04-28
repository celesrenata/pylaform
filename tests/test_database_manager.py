import os
import shutil
import sqlite3
import tempfile


class TestDatabaseManager:
    """Manages test database creation and cleanup for unit tests"""

    _instance = None
    _test_db_path = None

    @classmethod
    def get_instance(cls):
        """Singleton pattern to ensure we only have one test database manager"""
        if cls._instance is None:
            cls._instance = TestDatabaseManager()
        return cls._instance

    def __init__(self):
        """Initialize the test database manager"""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.source_db_path = os.path.join(self.base_path, 'pylaform/resources/resume.db')
        self.test_dir = tempfile.mkdtemp(prefix="pylaform_test_")
        self._test_db_path = os.path.join(self.test_dir, 'test_resume.db')

        # Make a fresh copy of the database
        self._create_test_db()

    def _create_test_db(self):
        """Create a fresh copy of the test database"""
        if not os.path.exists(self.source_db_path):
            raise FileNotFoundError(f"Source database not found at {self.source_db_path}")

        # Make sure the test directory exists
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

        # Remove existing test database if it exists
        if os.path.exists(self._test_db_path):
            os.remove(self._test_db_path)

        # Copy the clean database to the test location
        shutil.copy2(self.source_db_path, self._test_db_path)

    def get_db_connection(self):
        """Get a connection to the test database"""
        return sqlite3.connect(self._test_db_path, check_same_thread=False)

    def reset_db(self):
        """Reset the test database to its initial state"""
        self._create_test_db()

    def cleanup(self):
        """Clean up temporary files when done"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @property
    def test_db_path(self):
        """Get the path to the test database"""
        return self._test_db_path