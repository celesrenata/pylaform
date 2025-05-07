import unittest
import os
import tempfile
import json
import sqlite3
from unittest.mock import patch, MagicMock


# Use a TestCase with proper mocking setup
class PylaformTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Create data directory if it doesn't exist
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Set up the database patch
        cls.db_patcher = patch('pylaform.commands.db.connect.db')
        cls.mock_db = cls.db_patcher.start()

        # Create an in-memory SQLite database
        cls.test_db = sqlite3.connect(':memory:')
        cls.mock_db.return_value = cls.test_db

        # Create a cursor for the database
        cls.cursor = cls.test_db.cursor()

        # Patch the query class methods that are used in the app
        cls.query_patcher = patch('pylaform.commands.db.query.Queries')
        cls.mock_query = cls.query_patcher.start()

        # Mock instance of Queries
        cls.mock_query_instance = MagicMock()
        cls.mock_query.return_value = cls.mock_query_instance

        # Set up mock returns for common query methods
        cls.mock_query_instance.all.return_value = []
        cls.mock_query_instance.get_achievements.return_value = []
        cls.mock_query_instance.get_positions.return_value = []
        cls.mock_query_instance.get_education.return_value = []
        cls.mock_query_instance.get_identification.return_value = [
            {"id": 1, "attr": "name", "value": "Test Name", "state": True},
            {"id": 1, "attr": "contacttype", "value": "name", "state": True},
            {"id": 2, "attr": "email", "value": "test@example.com", "state": True},
            {"id": 2, "attr": "contacttype", "value": "email", "state": True},
            {"id": 3, "attr": "phone", "value": "1234567890", "state": True},
            {"id": 3, "attr": "contacttype", "value": "phone", "state": True},
            {"id": 4, "attr": "location", "value": "Test Location", "state": True},
            {"id": 4, "attr": "contacttype", "value": "location", "state": True},
            {"id": 5, "attr": "www", "value": "example.com", "state": True},  # Changed from website to www
            {"id": 5, "attr": "contacttype", "value": "www", "state": True},  # Changed contacttype too
            {"id": 6, "attr": "github", "value": "github.com/test", "state": True},
            {"id": 6, "attr": "contacttype", "value": "github", "state": True}
        ]
        cls.mock_query_instance.get_skills.return_value = []
        cls.mock_query_instance.get_summary.return_value = []
        cls.mock_query_instance.get_certifications.return_value = []
        cls.mock_query_instance.get_glossary.return_value = []
        cls.mock_query_instance.get_options.return_value = {'employer': [], 'position': []}

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done"""
        # Stop the patchers
        cls.db_patcher.stop()
        cls.query_patcher.stop()

        # Close the test database
        cls.test_db.close()

    def setUp(self):
        """Set up test environment before each test"""
        # Import app here after environment is set up
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Import the app after patching
        from app import app
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_landing_page(self):
        """Test that the landing page loads correctly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_information_page(self):
        """Test that the information page loads correctly"""
        response = self.client.get('/information')
        self.assertEqual(response.status_code, 200)

    def test_summary_page(self):
        """Test that the summary page loads correctly"""
        response = self.client.get('/summary')
        self.assertEqual(response.status_code, 200)

    def test_education_page(self):
        """Test that the education page loads correctly"""
        response = self.client.get('/education')
        self.assertEqual(response.status_code, 200)

    def test_certifications_page(self):
        """Test that the certifications page loads correctly"""
        response = self.client.get('/certifications')
        self.assertEqual(response.status_code, 200)

    def test_skills_page(self):
        """Test that the skills page loads correctly"""
        response = self.client.get('/skills')
        self.assertEqual(response.status_code, 200)

    def test_achievements_page(self):
        """Test that the achievements page loads correctly"""
        # Mock the specific methods needed for the achievements page
        self.mock_query_instance.all_achievements = MagicMock(return_value=[])
        self.mock_query_instance.all_position_employer = MagicMock(return_value=[])

        response = self.client.get('/achievements')
        self.assertEqual(response.status_code, 200)

    def test_glossary_page(self):
        """Test that the glossary page loads correctly"""
        response = self.client.get('/glossary')
        self.assertEqual(response.status_code, 200)

    def test_one_page_generation(self):
        """Test the one-page resume generation"""
        # Patch contact_flatten to return expected data structure
        contact_data = {
            "name": {"value": "Test Name", "state": True},
            "email": {"value": "test@example.com", "state": True},
            "phone": {"value": "1234567890", "state": True},
            "location": {"value": "Test Location", "state": True},
            "www": {"value": "example.com", "state": True},
            "github": {"value": "github.com/test", "state": True}
        }

        with patch('pylaform.utilities.commands.contact_flatten', return_value=contact_data):
            with patch('flask.render_template', return_value='PDF would be generated'):
                # Completely bypass PDF generation
                with patch('pylaform.latex_templates.onePage.Generator.run'):
                    response = self.client.get('/generate/one-page')
                    self.assertEqual(response.status_code, 200)

    def test_hybrid_generation(self):
        """Test the hybrid resume generation"""
        # Patch contact_flatten to return expected data structure
        contact_data = {
            "name": {"value": "Test Name", "state": True},
            "email": {"value": "test@example.com", "state": True},
            "phone": {"value": "1234567890", "state": True},
            "location": {"value": "Test Location", "state": True},
            "www": {"value": "example.com", "state": True},
            "github": {"value": "github.com/test", "state": True}
        }

        with patch('pylaform.utilities.commands.contact_flatten', return_value=contact_data):
            with patch('flask.render_template', return_value='PDF would be generated'):
                # Completely bypass PDF generation
                with patch('pylaform.latex_templates.hybrid.Generator.run'):
                    response = self.client.get('/generate/hybrid')
                    self.assertEqual(response.status_code, 200)

    @patch('pylaform.services.ai_service.OllamaService.generate_improvement')
    def test_improve_text_api(self, mock_generate_improvement):
        """Test the AI text improvement API"""
        # Mock the AI service response
        mock_generate_improvement.return_value = {"response": "Improved text content"}

        # Test API endpoint
        response = self.client.post('/api/improve-text',
                                    data=json.dumps({
                                        'text': 'Original text',
                                        'type': 'tenet'
                                    }),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response'], "Improved text content")

    def test_ai_status_api(self):
        """Test the AI status API"""
        # Skip patching the OllamaService internal implementation
        # Instead, just test the route's response
        response = self.client.get('/api/ai-status')

        # Check that the route returns a valid response
        self.assertEqual(response.status_code, 200)

        # Parse the response JSON
        data = json.loads(response.data)

        # Check that it has the expected structure based on the actual API response
        self.assertIn('status', data)
        self.assertIn('models', data)


if __name__ == '__main__':
    unittest.main()