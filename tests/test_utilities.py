import unittest
from unittest.mock import patch, MagicMock
from pylaform.utilities.commands import contact_flatten, date_adapter


class TestUtilityFunctions(unittest.TestCase):
    """Test various utility functions used in the application"""

    def test_contact_flatten(self):
        """Test flatten contact information from DB format to dict format"""
        # Sample data that matches the structure returned from the database
        db_data = [
            {"id": 1, "attr": "name", "value": "Test User", "state": 1},
            {"id": 1, "attr": "contacttype", "value": "name", "state": 1},
            {"id": 2, "attr": "email", "value": "test@example.com", "state": 1},
            {"id": 2, "attr": "contacttype", "value": "email", "state": 1},
            {"id": 3, "attr": "phone", "value": "1234567890", "state": 1},
            {"id": 3, "attr": "contacttype", "value": "phone", "state": 1},
            {"id": 4, "attr": "location", "value": "Test City", "state": 1},
            {"id": 4, "attr": "contacttype", "value": "location", "state": 1},
            {"id": 5, "attr": "www", "value": "example.com", "state": 1},
            {"id": 5, "attr": "contacttype", "value": "www", "state": 1}
        ]

        # Call the function
        result = contact_flatten(db_data)

        # Validate the result structure
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 6)  # Should be 6 items including contacttype

        # Check specific values
        self.assertEqual(result["name"]["value"], "Test User")
        self.assertEqual(result["email"]["value"], "test@example.com")
        self.assertEqual(result["phone"]["value"], "1234567890")
        self.assertEqual(result["location"]["value"], "Test City")
        self.assertEqual(result["www"]["value"], "example.com")
        self.assertEqual(result["contacttype"]["value"], "www")  # Last contacttype overwrites previous

    def test_date_adapter(self):
        """Test date format adaptation for database"""
        # Test valid date format
        result1 = date_adapter("2023-01-15")
        self.assertEqual(result1, "2023-01-15")

        # Test empty string - should return '9999-01-01' for empty strings
        result2 = date_adapter("")
        self.assertEqual(result2, "9999-01-01")

        # Test None value - should return None
        result3 = date_adapter(None)
        self.assertIsNone(result3)

        # Test partial date with month and year only - function adds the day
        result4 = date_adapter("2023-01")
        self.assertEqual(result4, "2023-01-01")

        # Test year only - function adds month and day
        result5 = date_adapter("2023")
        self.assertEqual(result5, "2023-01-01")

        # Test invalid format (should handle gracefully)
        result6 = date_adapter("invalid-date")
        self.assertEqual(result6, "9999-01-01")