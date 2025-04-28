from pylaform_test_case import PylaformTestCase
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import ImmutableMultiDict
from pylaform.utilities.commands import date_adapter
import sqlite3
import os
import logging

# Set up logging for test diagnostics
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='test_employment.log')
logger = logging.getLogger('test_employment')


# Custom cursor class to track SQL statements
class TracingCursor(sqlite3.Cursor):
    def execute(self, sql, params=None):
        if params:
            logger.debug(f"SQL: {sql}, Params: {params}")
        else:
            logger.debug(f"SQL: {sql}")
        return super().execute(sql, params or ())


# Custom Connection class that uses our TracingCursor
class TracingConnection(sqlite3.Connection):
    def cursor(self):
        return super().cursor(factory=TracingCursor)


class TestEmploymentFormFeatures(PylaformTestCase):
    """Test the employment form features"""

    def setUp(self):
        """Set up before each test"""
        super().setUp()

        # Create a test database connection for verification
        self.test_db_path = "test_employment.db"

        # If a previous test database exists, remove it
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        # Create a fresh database connection for verification with our tracing features
        self.verify_conn = sqlite3.connect(self.test_db_path, factory=TracingConnection)
        self.verify_cursor = self.verify_conn.cursor()

        # Create tables needed for testing
        self.verify_cursor.execute("""
                                   CREATE TABLE IF NOT EXISTS employer
                                   (
                                       id       INTEGER PRIMARY KEY AUTOINCREMENT,
                                       employer TEXT,
                                       location TEXT,
                                       state    INTEGER
                                   )
                                   """)

        self.verify_cursor.execute("""
                                   CREATE TABLE IF NOT EXISTS position
                                   (
                                       id        INTEGER PRIMARY KEY AUTOINCREMENT,
                                       employer  INTEGER,
                                       position  TEXT,
                                       startdate TEXT,
                                       enddate   TEXT,
                                       state     INTEGER,
                                       FOREIGN KEY (employer) REFERENCES employer (id)
                                   )
                                   """)

        self.verify_cursor.execute("""
                                   CREATE TABLE IF NOT EXISTS achievement
                                   (
                                       id        INTEGER PRIMARY KEY AUTOINCREMENT,
                                       employer  INTEGER,
                                       position  INTEGER,
                                       shortdesc TEXT,
                                       longdesc  TEXT,
                                       state     INTEGER,
                                       FOREIGN KEY (employer) REFERENCES employer (id),
                                       FOREIGN KEY (position) REFERENCES position (id)
                                   )
                                   """)

        self.verify_conn.commit()

        # Patch the worker's connection and cursor to use our test database
        patch_conn = patch.object(self.worker, 'conn', self.verify_conn)
        patch_cursor = patch.object(self.worker, 'cursor', self.verify_cursor)

        # Start the patches
        self.patch_conn = patch_conn.start()
        self.patch_cursor = patch_cursor.start()

        # Store the patchers for cleanup
        self.addCleanup(patch_conn.stop)
        self.addCleanup(patch_cursor.stop)

        # Create a patcher for date_adapter
        date_adapter_patcher = patch('pylaform.utilities.commands.date_adapter', wraps=date_adapter)
        self.mock_date_adapter = date_adapter_patcher.start()
        self.addCleanup(date_adapter_patcher.stop)

    def tearDown(self):
        """Clean up after each test"""
        # Debug: Show what's in the database before closing
        try:
            self.verify_cursor.execute("SELECT * FROM employer")
            employers = self.verify_cursor.fetchall()
            logger.debug(f"Employers at teardown: {employers}")

            self.verify_cursor.execute("SELECT * FROM position")
            positions = self.verify_cursor.fetchall()
            logger.debug(f"Positions at teardown: {positions}")
        except Exception as e:
            logger.error(f"Error in teardown diagnostics: {e}")

        self.verify_conn.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        super().tearDown()

    def _get_employer_count(self):
        """Helper to count employers in the database"""
        self.verify_cursor.execute("SELECT COUNT(*) FROM employer")
        count = self.verify_cursor.fetchone()[0]
        logger.debug(f"Current employer count: {count}")
        return count

    def _get_position_count(self):
        """Helper to count positions in the database"""
        self.verify_cursor.execute("SELECT COUNT(*) FROM position")
        count = self.verify_cursor.fetchone()[0]
        logger.debug(f"Current position count: {count}")
        return count

    def _get_achievement_count(self):
        """Helper to count achievements in the database"""
        self.verify_cursor.execute("SELECT COUNT(*) FROM achievement")
        count = self.verify_cursor.fetchone()[0]
        logger.debug(f"Current achievement count: {count}")
        return count

    def test_tracking_sql_update(self):
        """This test is specifically to track the SQL executed in update_positions"""
        # Store initial counts
        initial_employer_count = self._get_employer_count()

        # Call update_positions with a simple form to add an employer
        form_data = ImmutableMultiDict([
            ("new_employer_name", "Tracking Test Corp"),
            ("new_employer_location", "Test Location"),
            ("new_employer_enabled", "on"),
            ("new_employer_dropdown", "EDIT"),
            ("new_rowid", "new_record")
        ])

        # Log the form data before calling update_positions
        logger.debug(f"Form data: {form_data}")

        # Call the method we're testing
        self.worker.update_positions(form_data)

        # Verify database state by direct querying
        self.verify_cursor.execute("SELECT * FROM employer")
        employers = self.verify_cursor.fetchall()
        logger.debug(f"Employers in DB after update_positions: {employers}")

        # Get final counts
        final_employer_count = self._get_employer_count()

        # Check if anything was actually inserted
        logger.debug(f"Initial employer count: {initial_employer_count}")
        logger.debug(f"Final employer count: {final_employer_count}")

        # This test doesn't assert anything - it's diagnostic to see what happens

    def test_insert_direct(self):
        """Test direct insertion into database to confirm our connection works"""
        # First confirm employer count is 0
        initial_count = self._get_employer_count()
        self.assertEqual(0, initial_count, "Database should start empty")

        # Directly insert a record without going through Worker methods
        self.verify_cursor.execute(
            "INSERT INTO employer (employer, location, state) VALUES (?, ?, ?)",
            ("Direct Insert Company", "Direct Location", 1)
        )
        self.verify_conn.commit()

        # Verify the record was inserted
        final_count = self._get_employer_count()
        self.assertEqual(1, final_count, "Direct insert should create 1 record")

        # Get the data to verify
        self.verify_cursor.execute("SELECT employer, location FROM employer")
        employer_data = self.verify_cursor.fetchone()
        self.assertEqual("Direct Insert Company", employer_data[0])
        self.assertEqual("Direct Location", employer_data[1])


def test_add_new_employer(self):
    """Test adding a new employer with position through the form"""
    # Get initial counts
    initial_employer_count = self._get_employer_count()
    initial_position_count = self._get_position_count()

    # Create form data that exactly matches the expected format
    form_data = ImmutableMultiDict([
        # The key here needs to match exactly what the method is looking for
        ("new_employer_name", "Acme Corporation"),
        ("new_employer_location", "Seattle, WA"),
        ("new_employer_enabled", "on"),
        ("new_position_name", "Senior Software Engineer"),
        ("new_startdate", "2019-03-15"),  # Note: no "position_" prefix here
        ("new_enddate", "2023-06-30"),  # Note: no "position_" prefix here
        ("new_position_enabled", "on"),
        ("new_position_dropdown", "EDIT"),
        ("new_employer_dropdown", "EDIT"),
        ("new_rowid", "new_record")
    ])

    # Call update_positions with our test form data
    self.worker.update_positions(form_data)

    # Force a commit (the method already commits, but just to be sure)
    self.verify_conn.commit()

    # Log the database state for debugging
    self.verify_cursor.execute("SELECT * FROM employer")
    employers = self.verify_cursor.fetchall()
    logger.debug(f"Employers after test: {employers}")

    self.verify_cursor.execute("SELECT * FROM position")
    positions = self.verify_cursor.fetchall()
    logger.debug(f"Positions after test: {positions}")

    # Verify a new employer was added
    final_employer_count = self._get_employer_count()
    self.assertEqual(initial_employer_count + 1, final_employer_count,
                     "Should have added one new employer")

    # Now verify employer exists with correct data
    self.verify_cursor.execute("SELECT employer, location FROM employer")
    employer_data = self.verify_cursor.fetchone()
    if employer_data:
        self.assertEqual("Acme Corporation", employer_data[0], "Employer name should match input")
        self.assertEqual("Seattle, WA", employer_data[1], "Employer location should match input")
    else:
        self.fail("No employer data found in the database")

    # Verify a new position was added
    final_position_count = self._get_position_count()
    self.assertEqual(initial_position_count + 1, final_position_count,
                     "Should have added one new position")

    # Verify date_adapter was called
    self.assertTrue(self.mock_date_adapter.called, "date_adapter should be called")


def test_update_education_dates(self):
    """Test updating dates for an existing focus record"""
    # First, ensure there's a record to update
    self.verify_cursor.execute(
        "INSERT INTO school (id, name, location, state) VALUES (100, 'Test School', 'Test Location', 1)"
    )
    self.verify_cursor.execute(
        "INSERT INTO focus (id, school, name, startdate, enddate, state) VALUES (100, 100, 'Test Focus', '2020-01-01', '2022-01-01', 1)"
    )
    self.verify_conn.commit()

    # Now create a form that updates the dates
    form_data = ImmutableMultiDict([
        ("100_focus_dropdown", "EDIT"),
        ("100_focus_name", "Test Focus"),
        ("100_focus_startdate", "2020-02-15"),  # Changed date
        ("100_focus_enddate", "2022-12-31"),  # Changed date
        ("100_focus_enabled", "on"),
        ("100_rowid", "focus_100"),
        ("100_school_dropdown", "100"),
        ("100_school_name", "Test School"),
        ("100_school_location", "Test Location"),
        ("100_school_enabled", "on"),
        ("100_rowid", "school_100")
    ])

    # Use patching to track calls to date_adapter
    with patch('pylaform.commands.templateWorker.date_adapter', wraps=date_adapter) as mock_date_adapter:
        # Call update_education with our test form data
        self.worker.update_education(form_data)

        # Force a commit to ensure changes are written
        self.verify_conn.commit()

        # Verify date_adapter was called with our new dates
        date_calls = [call[0][0] for call in mock_date_adapter.call_args_list]
        self.assertIn("2020-02-15", date_calls, "date_adapter should be called with new start date")
        self.assertIn("2022-12-31", date_calls, "date_adapter should be called with new end date")

        # Directly query the database to verify the changes were saved
        self.verify_cursor.execute("SELECT startdate, enddate FROM focus WHERE id = 100")
        dates = self.verify_cursor.fetchone()
        self.assertEqual("2020-02-15", dates[0], "Start date should be updated in database")
        self.assertEqual("2022-12-31", dates[1], "End date should be updated in database")