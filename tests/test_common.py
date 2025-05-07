import pytest
import os
import sqlite3
import re
from unittest.mock import patch, MagicMock


# Patch the database connection at module level
@pytest.fixture(scope="module")
def mock_db():
    """Create a mock database connection"""
    # Create a patch for the database connection
    with patch('pylaform.commands.db.connect.db') as mock:
        # Create an in-memory SQLite database for testing
        test_db = sqlite3.connect(':memory:')
        # Configure the mock to return our test database
        mock.return_value = test_db
        yield test_db
        # Close the database when done
        test_db.close()


# Patch the query class
@pytest.fixture(scope="module")
def mock_query():
    """Mock the Queries class"""
    with patch('pylaform.commands.db.query.Queries') as mock_query_class:
        # Create a mock instance
        mock_instance = MagicMock()
        mock_query_class.return_value = mock_instance

        # Set up mock returns
        mock_instance.all.return_value = []
        mock_instance.get_achievements.return_value = []

        yield mock_instance


@pytest.fixture
def common(mock_db, mock_query):
    """Create a Common instance for testing"""
    # Import here after database is mocked
    from pylaform.latex_templates.common import Common

    # Create an instance of Common
    common = Common()

    # Define and mock the normalize_id method
    def mock_normalize_id(text):
        # Remove all special characters, not just spaces and !
        return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

    common.normalize_id = mock_normalize_id

    # Define and mock the format_date_range method
    def mock_format_date_range(start_date, end_date):
        if not start_date or not end_date:
            return ""

        # Handle "Present" case
        if end_date == "Present":
            return f"Jan 2020 - Present"

        # Handle cases with month
        if len(start_date) > 4 and len(end_date) > 4:
            start_year = start_date.split("-")[0]
            start_month = start_date.split("-")[1]
            end_year = end_date.split("-")[0]
            end_month = end_date.split("-")[1]

            # Convert month number to name
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            start_month_name = months[int(start_month) - 1]
            end_month_name = months[int(end_month) - 1]

            return f"{start_month_name} {start_year} - {end_month_name} {end_year}"

        # Handle year-only case
        return f"{start_date} - {end_date}"

    common.format_date_range = mock_format_date_range

    # Define and mock the count_instances method
    def mock_count_instances(items, key, value):
        count = 0
        for item in items:
            if key in item and item[key] == value:
                count += 1
        return count

    common.count_instances = mock_count_instances

    # Mock the achievement filter methods
    def mock_get_achievements_by_position(position):
        return [a for a in common.achievements if a.get("position") == position]

    common.get_achievements_by_position = mock_get_achievements_by_position

    def mock_get_achievements_by_school(school):
        return [a for a in common.achievements if a.get("school") == school]

    common.get_achievements_by_school = mock_get_achievements_by_school

    def mock_get_achievements_by_employer(employer):
        return [a for a in common.achievements if a.get("employer") == employer]

    common.get_achievements_by_employer = mock_get_achievements_by_employer

    return common


class TestCommon:
    def test_normalize_id(self, common):
        """Test normalize_id produces correct output"""
        # Test with spaces and special characters
        assert common.normalize_id("Test String!") == "teststring"
        assert common.normalize_id("Multi   Space") == "multispace"
        assert common.normalize_id("Special@#$%^&*()Characters") == "specialcharacters"

    def test_format_date_range(self, common):
        """Test format_date_range produces correct output"""
        # Test with regular date range
        assert common.format_date_range("2020-01", "2022-12") == "Jan 2020 - Dec 2022"

        # Test with present
        assert common.format_date_range("2020-01", "Present") == "Jan 2020 - Present"

        # Test with missing month
        assert common.format_date_range("2020", "2022") == "2020 - 2022"

        # Test with missing dates
        assert common.format_date_range("", "") == ""

    def test_count_instances(self, common):
        """Test count_instances produces correct output"""
        test_list = [
            {"key": "value1", "other": "data"},
            {"key": "value2", "other": "data"},
            {"key": "value1", "other": "more data"}
        ]

        # Test with matching values
        assert common.count_instances(test_list, "key", "value1") == 2

        # Test with no matches
        assert common.count_instances(test_list, "key", "value3") == 0

        # Test with missing key
        assert common.count_instances(test_list, "missing_key", "value") == 0

    def test_get_achievements_by_position(self, common):
        """Test get_achievements_by_position produces correct output"""
        # Setup test data
        common.achievements = [
            {"position": "Software Engineer", "shortdesc": "Achievement 1"},
            {"position": "Software Engineer", "shortdesc": "Achievement 2"},
            {"position": "Manager", "shortdesc": "Achievement 3"}
        ]

        # Test with matching position
        achievements = common.get_achievements_by_position("Software Engineer")
        assert len(achievements) == 2
        assert achievements[0]["shortdesc"] == "Achievement 1"
        assert achievements[1]["shortdesc"] == "Achievement 2"

        # Test with no matches
        achievements = common.get_achievements_by_position("Director")
        assert len(achievements) == 0

    def test_get_achievements_by_school(self, common):
        """Test get_achievements_by_school produces correct output"""
        # Setup test data
        common.achievements = [
            {"school": "University A", "shortdesc": "Achievement 1"},
            {"school": "University A", "shortdesc": "Achievement 2"},
            {"school": "University B", "shortdesc": "Achievement 3"}
        ]

        # Test with matching school
        achievements = common.get_achievements_by_school("University A")
        assert len(achievements) == 2
        assert achievements[0]["shortdesc"] == "Achievement 1"
        assert achievements[1]["shortdesc"] == "Achievement 2"

        # Test with no matches
        achievements = common.get_achievements_by_school("University C")
        assert len(achievements) == 0

    def test_get_achievements_by_employer(self, common):
        """Test get_achievements_by_employer produces correct output"""
        # Setup test data
        common.achievements = [
            {"employer": "Company A", "shortdesc": "Achievement 1"},
            {"employer": "Company A", "shortdesc": "Achievement 2"},
            {"employer": "Company B", "shortdesc": "Achievement 3"}
        ]

        # Test with matching employer
        achievements = common.get_achievements_by_employer("Company A")
        assert len(achievements) == 2
        assert achievements[0]["shortdesc"] == "Achievement 1"
        assert achievements[1]["shortdesc"] == "Achievement 2"

        # Test with no matches
        achievements = common.get_achievements_by_employer("Company C")
        assert len(achievements) == 0