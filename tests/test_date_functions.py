import unittest
from pylaform.utilities.commands import date_adapter

class TestDateAdapter(unittest.TestCase):
    """Test the date_adapter function independently of the database"""

    def test_date_adapter_normal_date(self):
        """Test date_adapter with a normal date string"""
        test_date = "2007-12-01"
        result = date_adapter(test_date)
        self.assertEqual(result, "2007-12-01", "date_adapter should not modify valid date strings")

    def test_date_adapter_empty_string(self):
        """Test date_adapter with an empty string"""
        test_date = ""
        result = date_adapter(test_date)
        self.assertEqual(result, "9999-01-01", "date_adapter should convert empty string to 9999-01-01")

    def test_date_adapter_hidden(self):
        """Test date_adapter with 'hidden' value"""
        test_date = "hidden"
        result = date_adapter(test_date)
        self.assertEqual(result, "0001-01-01", "date_adapter should convert 'hidden' to 0001-01-01")

if __name__ == '__main__':
    unittest.main()