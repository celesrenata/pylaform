import unittest
import os
import tempfile
import json
import sqlite3
from unittest.mock import patch, MagicMock

from app import app
from app import information
from flask import request, flash
from flask import url_for
import sys

from app import get_secret_key
from app import update_skills
from flask import Flask
from flask import Flask, request, flash, redirect, url_for
from flask import Flask, url_for
from flask import render_template
from flask import session
from unittest.mock import patch


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
        # Models might be empty in testing, so we just check the field exists
        self.assertIn('models', data)

    def test_achievements_2(self):
        """
        Test adding a new achievement and updating an existing one.

        This test covers the following path constraints:
        - request.method == 'POST'
        - not ('_delete_achievement' in form_data)
        - key.startswith('new-achievement-') and key.endswith('_title')
        - title is not empty
        - result is truthy (new achievement added successfully)
        - f"{achievement_id}_title" in form_data (for existing achievement)
        - (title != current_title or description != current_desc or date != current_date or
           url != current_url or enabled != current_state or achievement_order != current_order)
        - result is truthy (existing achievement updated successfully)
        - new_added or updates_made is True

        Expected return: redirect(url_for('achievements'))
        """
        with self.app.test_request_context():
            # Mock the Worker class and its methods
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.add_standalone_achievement.return_value = 'new_achievement_id'
                mock_worker.get_all_achievements.return_value = [{
                    'SK': 'existing_achievement_id',
                    'title': 'Old Title',
                    'description': 'Old Description',
                    'date': '2023-01-01',
                    'url': 'http://old.com',
                    'state': 0,
                    'achievement_order': 1
                }]
                mock_worker.update_achievement.return_value = True

                # Simulate POST request with form data
                form_data = {
                    'new-achievement-1_title': 'New Achievement',
                    'new-achievement-1_description': 'New Description',
                    'new-achievement-1_date': '2023-12-31',
                    'new-achievement-1_url': 'http://new.com',
                    'new-achievement-1_enabled': 'on',
                    'new-achievement-1_achievement_order': '2',
                    'existing_achievement_id_title': 'Updated Title',
                    'existing_achievement_id_description': 'Updated Description',
                    'existing_achievement_id_date': '2023-12-31',
                    'existing_achievement_id_url': 'http://updated.com',
                    'existing_achievement_id_enabled': 'on',
                    'existing_achievement_id_achievement_order': '3'
                }

                response = self.client.post('/achievements', data=form_data)

                # Assert that a new achievement was added
                mock_worker.add_standalone_achievement.assert_called_once_with(
                    title='New Achievement',
                    description='New Description',
                    date='2023-12-31',
                    url='http://new.com',
                    achievement_order=2
                )

                # Assert that the existing achievement was updated
                mock_worker.update_achievement.assert_called_once_with(
                    'existing_achievement_id',
                    title='Updated Title',
                    description='Updated Description',
                    date='2023-12-31',
                    url='http://updated.com',
                    state=1,
                    achievement_order=3
                )

                # Assert that the response is a redirect to the achievements page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/achievements')

    def test_achievements_3(self):
        """
        Test case for the achievements route when updating existing achievements and adding new ones.

        This test covers the following path constraints:
        - request.method == 'POST'
        - not ('_delete_achievement' in form_data)
        - key.startswith('new-achievement-') and key.endswith('_title')
        - title exists
        - existing achievement update condition is met
        - updates are made to existing achievements
        - new achievements are added

        The test verifies that the route correctly processes form data, updates existing achievements,
        adds new achievements, and redirects to the achievements page.
        """
        with self.app.test_request_context():
            # Mock the Worker class and its methods
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.get_all_achievements.return_value = [
                    {'SK': 'existing1', 'title': 'Old Title', 'description': 'Old Desc', 'date': '2023-01-01', 'url': 'http://old.com', 'state': 0, 'achievement_order': 1}
                ]
                mock_worker.update_achievement.return_value = True
                mock_worker.add_standalone_achievement.return_value = 'new1'

                # Prepare form data
                form_data = {
                    'new-achievement-1_title': 'New Achievement',
                    'new-achievement-1_description': 'New Description',
                    'new-achievement-1_date': '2023-12-31',
                    'new-achievement-1_url': 'http://new.com',
                    'new-achievement-1_enabled': 'on',
                    'new-achievement-1_achievement_order': '2',
                    'existing1_title': 'Updated Title',
                    'existing1_description': 'Updated Desc',
                    'existing1_date': '2023-01-02',
                    'existing1_url': 'http://updated.com',
                    'existing1_enabled': 'on',
                    'existing1_achievement_order': '1'
                }

                # Make a POST request to the achievements route
                response = self.client.post('/achievements', data=form_data)

                # Verify that the worker methods were called correctly
                mock_worker.get_all_achievements.assert_called_once()
                mock_worker.update_achievement.assert_called_once_with(
                    'existing1',
                    title='Updated Title',
                    description='Updated Desc',
                    date='2023-01-02',
                    url='http://updated.com',
                    state=1,
                    achievement_order=1
                )
                mock_worker.add_standalone_achievement.assert_called_once_with(
                    title='New Achievement',
                    description='New Description',
                    date='2023-12-31',
                    url='http://new.com',
                    achievement_order=2
                )

                # Check if the response is a redirect to the achievements page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/achievements')

    def test_achievements_4(self):
        """
        Test updating an existing achievement with changes.

        This test covers the following path constraints:
        - request.method == 'POST'
        - not ('_delete_achievement' in form_data)
        - f"{achievement_id}_title" in form_data
        - (title != current_title or description != current_desc or date != current_date or
           url != current_url or enabled != current_state or achievement_order != current_order)
        - result (update successful)
        - updates_made

        Expected outcome: Redirect to achievements page after successful update.
        """
        with self.client as client:
            # Mock the Worker class and its methods
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.get_all_achievements.return_value = [{
                    'SK': 'existing_achievement',
                    'title': 'Old Title',
                    'description': 'Old Description',
                    'date': '2023-01-01',
                    'url': 'http://old.url',
                    'state': 0,
                    'achievement_order': 1
                }]
                mock_worker.update_achievement.return_value = True

                # Simulate a POST request with form data
                response = client.post('/achievements', data={
                    'existing_achievement_title': 'New Title',
                    'existing_achievement_description': 'New Description',
                    'existing_achievement_date': '2024-01-01',
                    'existing_achievement_url': 'http://new.url',
                    'existing_achievement_enabled': 'on',
                    'existing_achievement_achievement_order': '2'
                })

                # Assert that the update_achievement method was called with correct arguments
                mock_worker.update_achievement.assert_called_once_with(
                    'existing_achievement',
                    title='New Title',
                    description='New Description',
                    date='2024-01-01',
                    url='http://new.url',
                    state=1,
                    achievement_order=2
                )

                # Check for redirect response
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/achievements')

    def test_ai_config(self):
        """
        Test case for the ai_config() function.

        This test verifies that the ai_config route returns the correct template
        and status code.
        """
        with patch('flask.render_template') as mock_render:
            mock_render.return_value = 'AI Config Template'
            response = self.client.get('/ai-config')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('ai_config.html')

    def test_ai_status_1(self):
        """
        Test the AI status endpoint to ensure it returns the correct status and message.

        This test verifies that the /api/ai-status endpoint returns a JSON response
        with 'status' set to 'ok' and 'message' indicating that Amazon Q is available.
        """
        response = self.client.get('/api/ai-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, {"status": "ok", "message": "Amazon Q is available"})

    def test_certifications_1(self):
        """
        Test case for certifications route when deleting a certification.

        This test verifies that when a POST request is made to the certifications route
        with a '_delete' parameter in the form data, the route properly handles the deletion
        and redirects to the certifications page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/certifications', data={
                '_delete': '123'  # Simulating deletion of certification with ID 123
            })

            # Assert that delete_entry was called with correct arguments
            mock_worker.delete_entry.assert_called_once_with("certification", "123")

            # Assert that the response is a redirect to the certifications page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/certifications')

    def test_certifications_exception_handling(self):
        """
        Test exception handling in the certifications route.
        This test verifies that when an exception occurs, the route returns a 500 error with the error message.
        """
        # Mock Worker to raise an exception
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker.side_effect = Exception("Test exception")

            response = self.client.get('/certifications')

            self.assertEqual(response.status_code, 500)
            self.assertIn("Error: Test exception", response.get_data(as_text=True))

    def test_delete_nonexistent_achievement(self):
        """
        Test deleting a non-existent achievement.
        This tests the edge case where a delete operation is attempted on an achievement that doesn't exist.
        """
        # Mock the delete_entry method to return False, simulating a failed deletion
        self.mock_query_instance.delete_entry = MagicMock(return_value=False)

        # Attempt to delete a non-existent achievement
        response = self.client.post('/achievements', data={
            '_delete_achievement': 'nonexistent_id'
        })

        # Check that the response redirects (as it should in both success and failure cases)
        self.assertEqual(response.status_code, 302)

        # Verify that delete_entry was called with the correct arguments
        self.mock_query_instance.delete_entry.assert_called_once_with("standalone_achievement", "nonexistent_id")

    def test_delete_standalone_achievement(self):
        """
        Test deleting a standalone achievement in the achievements route.

        This test verifies that when a POST request is made to the achievements
        route with a '_delete_achievement' parameter, the corresponding achievement
        is deleted and the user is redirected to the achievements page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/achievements', data={
                '_delete_achievement': 'test_achievement_id'
            }, follow_redirects=True)

            mock_worker.delete_entry.assert_called_once_with("standalone_achievement", "test_achievement_id")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Achievement deleted successfully', response.data)

    def test_education_1(self):
        """
        Test the education route to ensure it initializes the worker,
        retrieves education data, and renders the correct template with the payload.
        """
        mock_schools = [{"name": "Test School", "degree": "Test Degree"}]
        self.mock_query_instance.get_all_education = MagicMock(return_value=mock_schools)

        with patch('flask.render_template') as mock_render:
            response = self.client.get('/education')

            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with("education_index.html", payload=mock_schools)
            print("DEBUG: Retrieved", len(mock_schools), "schools")

    def test_education_post_1(self):
        """
        Test case for education_post() when deleting a new education entry.

        This test verifies that when a POST request is made to delete a new education entry
        (i.e., an entry that hasn't been saved to the database yet), the application correctly
        handles the request by not performing any database operation and redirecting to the
        education page.
        """
        with self.client as client:
            response = client.post('/education', data={
                '_delete': 'new1'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Education', response.data)  # Assuming 'Education' is in the page title

            # Verify that no database operation was performed
            self.mock_query_instance.delete_entry.assert_not_called()

    def test_education_post_2(self):
        """
        Test case for education_post() method when deleting an existing education entry.

        This test verifies that when a POST request is made to delete an existing education entry,
        the entry is successfully deleted and the user is redirected to the education page.

        Path constraints:
        - "_delete" is in form_data
        - delete_id exists and is not empty
        - delete_id does not start with "new"

        Expected behavior:
        - The delete_entry method of the Worker is called with correct parameters
        - A success flash message is set
        - The user is redirected to the education page
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/education', data={
                '_delete': 'existing_id'
            }, follow_redirects=True)

            mock_worker.delete_entry.assert_called_once_with("school", "existing_id")
            self.assertIn(b"School deleted successfully", response.data)
            self.assertEqual(response.request.path, '/education')

    def test_education_post_3(self):
        """
        Test case for education_post() method when adding a new school with focus areas.

        This test covers the following path constraints:
        - "_delete" not in form_data
        - "_" in key
        - "focus_" in key
        - school_id not in focus_data initially
        - len(focus_parts) > 1
        - "enabled" in data
        - "rowid" in data
        - school_id.startswith("new")
        - "name" in data
        - school_id in focus_data
        - focus["description"].strip() is truthy

        Expected result: Redirect to the education page after successful addition.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.add_school.return_value = "new_school_id"

            form_data = {
                "new1_name": "Test School",
                "new1_degree": "Test Degree",
                "new1_graddate": "2023",
                "new1_enabled": "on",
                "new1_rowid": "1",
                "new1_focus_1": "Test Focus Area"
            }

            response = self.client.post('/education', data=form_data)

            # Assert that add_school was called with correct parameters
            mock_worker.add_school.assert_called_once_with(
                name="Test School",
                degree="Test Degree",
                graddate="2023"
            )

            # Assert that add_focus was called with correct parameters
            mock_worker.add_focus.assert_called_once_with("new_school_id", "Test Focus Area")

            # Assert that the response is a redirect to the education page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/education')

    def test_education_post_4(self):
        """
        Test adding a new school with focus areas to the education database.

        This test verifies that:
        1. A new school can be added successfully.
        2. Focus areas for the new school are added correctly.
        3. The response redirects to the education page after successful addition.

        Path constraints:
        - Form data does not contain "_delete"
        - Form data contains keys with underscores
        - Form data includes "focus_" keys
        - New school ID is not already in focus_data
        - Focus key parts length is greater than 1
        - "enabled" and "rowid" are in the school data
        - School ID starts with "new"
        - "name" is in the school data
        - New school ID is in focus_data
        - Focus description is not empty
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.add_school.return_value = "new_school_1"
                mock_worker.add_focus.return_value = True

                form_data = {
                    "new1_name": "Test University",
                    "new1_degree": "Bachelor of Science",
                    "new1_graddate": "2023-05-15",
                    "new1_enabled": "on",
                    "new1_rowid": "1",
                    "new1_focus_1": "Computer Science",
                    "new1_focus_2": "Data Structures"
                }

                response = self.client.post('/education', data=form_data)

                # Verify that add_school was called with correct parameters
                mock_worker.add_school.assert_called_once_with(
                    name="Test University",
                    degree="Bachelor of Science",
                    graddate="2023-05-15"
                )

                # Verify that add_focus was called for each focus area
                mock_worker.add_focus.assert_any_call("new_school_1", "Computer Science")
                mock_worker.add_focus.assert_any_call("new_school_1", "Data Structures")

                # Check if the response is a redirect to the education page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/education')

    @patch('app.Worker')
    def test_education_post_delete_nonexistent_school(self, mock_worker):
        """
        Test deleting a non-existent school ID.
        This tests the edge case where a delete operation is attempted on a school ID that doesn't exist.
        """
        mock_worker_instance = mock_worker.return_value
        mock_worker_instance.delete_entry.return_value = False

        response = self.client.post('/education', data={
            '_delete': 'nonexistent_id'
        })

        self.assertEqual(response.status_code, 302)  # Expecting a redirect
        mock_worker_instance.delete_entry.assert_called_once_with("school", "nonexistent_id")

    @patch('app.Worker')
    def test_education_post_empty_form_submission(self, mock_worker):
        """
        Test submitting an empty form.
        This tests the edge case where no data is submitted in the form.
        """
        response = self.client.post('/education', data={})

        self.assertEqual(response.status_code, 302)  # Expecting a redirect
        mock_worker.assert_called_once()  # Worker should be initialized
        # No other methods should be called on the worker

    @patch('app.Worker')
    def test_education_post_invalid_date_format(self, mock_worker):
        """
        Test submitting a form with an invalid date format.
        This tests the edge case where an invalid date format is provided for graddate.
        """
        mock_worker_instance = mock_worker.return_value
        mock_worker_instance.add_school.return_value = 'new_school_id'

        response = self.client.post('/education', data={
            'new1_name': 'Test School',
            'new1_degree': 'Test Degree',
            'new1_graddate': 'invalid_date'  # Invalid date format
        })

        self.assertEqual(response.status_code, 302)  # Expecting a redirect
        mock_worker_instance.add_school.assert_called_once_with(
            name='Test School',
            degree='Test Degree',
            graddate='invalid_date'
        )
        # Note: The method doesn't perform date validation, so it will pass the invalid date to add_school

    def test_employment_3(self):
        """
        Test the employment route when deleting an achievement that fails.

        This test verifies the behavior of the employment route when:
        1. The request method is POST
        2. The form data includes a '_delete_achievement' key
        3. The achievement_id is valid and starts with 'achievement_'
        4. The deletion operation fails

        Expected outcome:
        - The user should be redirected to the employment page
        - An error flash message should be set
        """
        with self.app.test_request_context():
            with patch('app.Worker') as mock_worker:
                mock_worker_instance = mock_worker.return_value
                mock_worker_instance.delete_entry.return_value = False

                response = self.client.post('/employment', data={
                    '_delete_achievement': 'achievement_123',
                })

                mock_worker_instance.delete_entry.assert_called_once_with("achievement", "123")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('employment'))

                with self.client.session_transaction() as session:
                    flash_messages = session['_flashes']
                    self.assertEqual(len(flash_messages), 1)
                    self.assertEqual(flash_messages[0], ('danger', 'Error deleting achievement'))

    def test_employment_4(self):
        """
        Test the employment route when a POST request is made to delete an achievement,
        but the achievement ID is either not provided or starts with "new-achievement-".
        This should result in a redirect to the employment page without performing any deletion.
        """
        with self.app.test_request_context():
            response = self.client.post('/employment', data={
                '_delete_achievement': 'new-achievement-123'
            })
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('employment'))

    def test_employment_delete_achievement(self):
        """
        Test case for deleting an achievement in the employment route.

        This test verifies that when a POST request is made to delete an achievement,
        the appropriate actions are taken and a redirect response is returned.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.delete_entry.return_value = True

            response = self.client.post('/employment', data={
                '_delete_achievement': 'achievement_123'
            })

            mock_worker_instance.delete_entry.assert_called_once_with("achievement", "123")
            self.assertEqual(response.status_code, 302)  # Expecting a redirect
            self.assertEqual(response.location, '/employment')

    def test_employment_delete_achievement_2(self):
        """
        Test the employment route for deleting an achievement.

        This test covers the path where:
        - The request method is POST
        - '_delete_achievement' is in the form data
        - The achievement_id is provided and doesn't start with "new-achievement-"
        - The achievement_id doesn't start with "achievement_"
        - The deletion is successful

        The expected result is a redirect to the employment page.
        """
        with self.app.test_client() as client:
            with patch('pylaform.database.templateWorker.Worker.delete_entry', return_value=True) as mock_delete:
                response = client.post('/employment', data={
                    '_delete_achievement': 'valid_achievement_id'
                })

                # Assert that delete_entry was called with correct arguments
                mock_delete.assert_called_once_with("achievement", "valid_achievement_id")

                # Check if the response is a redirect
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers['Location'], '/employment')

    def test_employment_delete_nonexistent_achievement(self):
        """
        Test deleting a non-existent achievement.
        This tests the edge case where the achievement ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker.delete_entry', return_value=False):
            response = self.client.post('/employment', data={
                '_delete_achievement': 'nonexistent_id'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting achievement', response.data)

    def test_employment_delete_nonexistent_employer(self):
        """
        Test deleting a non-existent employer.
        This tests the edge case where the employer ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker.delete_entry', return_value=False):
            response = self.client.post('/employment', data={
                '_delete_employer': 'nonexistent_id'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting employer', response.data)

    def test_employment_delete_nonexistent_position(self):
        """
        Test deleting a non-existent position.
        This tests the edge case where the position ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker.delete_entry', return_value=False):
            response = self.client.post('/employment', data={
                '_delete_position': 'nonexistent_id'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting position', response.data)

    def test_get_positions_for_employer_1(self):
        """
        Test the get_positions_for_employer API endpoint.

        This test verifies that the endpoint returns a JSON response containing
        a list of positions for a given employer ID, with each position having
        an 'id' and 'title' field.
        """
        # Mock the Worker class and its get_positions_for_employer method
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker_instance = MockWorker.return_value
            mock_worker_instance.get_positions_for_employer.return_value = [
                {'SK': 'pos1', 'title': 'Software Engineer'},
                {'SK': 'pos2', 'title': 'Project Manager'}
            ]

            # Make a request to the API endpoint
            response = self.client.get('/api/positions/emp1')

            # Check that the response status code is 200 (OK)
            self.assertEqual(response.status_code, 200)

            # Parse the JSON response
            data = json.loads(response.data)

            # Check that the response is a list
            self.assertIsInstance(data, list)

            # Check that each item in the list has the expected structure
            for item in data:
                self.assertIn('id', item)
                self.assertIn('title', item)

            # Check the content of the response
            expected_data = [
                {'id': 'pos1', 'title': 'Software Engineer'},
                {'id': 'pos2', 'title': 'Project Manager'}
            ]
            self.assertEqual(data, expected_data)

            # Verify that the get_positions_for_employer method was called with the correct argument
            mock_worker_instance.get_positions_for_employer.assert_called_once_with('emp1')

    def test_get_positions_for_employer_with_nonexistent_employer(self):
        """
        Test the get_positions_for_employer endpoint with a nonexistent employer ID.
        This tests the edge case where the employer ID does not exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.get_positions_for_employer.return_value = []

            response = self.client.get('/api/positions/nonexistent_id')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data, [])

    def test_glossary_1(self):
        """
        Test case for the glossary route.

        This test verifies that the glossary route initializes a Worker,
        retrieves glossary terms, sorts them alphabetically, and renders
        the correct template with the sorted terms as payload.
        """
        # Mock the Worker class and its get_glossary method
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker_instance = MockWorker.return_value
            mock_worker_instance.get_glossary.return_value = [
                {"term": "Python", "definition": "A programming language"},
                {"term": "Flask", "definition": "A web framework for Python"},
                {"term": "API", "definition": "Application Programming Interface"}
            ]

            # Make a GET request to the glossary route
            response = self.client.get('/glossary')

            # Assert that the response status code is 200 (OK)
            self.assertEqual(response.status_code, 200)

            # Assert that Worker was initialized
            MockWorker.assert_called_once()

            # Assert that get_glossary was called on the Worker instance
            mock_worker_instance.get_glossary.assert_called_once()

            # Assert that the correct template was rendered
            self.assertIn(b'glossary_index.html', response.data)

            # Assert that the terms are sorted alphabetically in the response
            self.assertIn(b'API', response.data)
            self.assertIn(b'Flask', response.data)
            self.assertIn(b'Python', response.data)
            # Check if 'API' appears before 'Flask' and 'Python' in the response
            api_index = response.data.index(b'API')
            flask_index = response.data.index(b'Flask')
            python_index = response.data.index(b'Python')
            self.assertTrue(api_index < flask_index < python_index)

    def test_glossary_post_1(self):
        """
        Test case for glossary_post() function when a new item is deleted.

        This test verifies the behavior of the glossary_post() function when
        a new glossary item (with ID starting with "new") is marked for deletion.
        The function should redirect to the glossary page without performing any
        database operations.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value

            response = self.client.post('/glossary', data={
                '_delete': 'new1'
            })

            # Assert that delete_entry was not called
            mock_worker_instance.delete_entry.assert_not_called()

            # Assert that we get redirected to the glossary page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/glossary')

    def test_glossary_post_deletion_with_invalid_id(self):
        """
        Test deletion of a glossary term with an invalid ID.
        This tests the edge case where a delete request is made with an ID that doesn't exist.
        """
        with self.client as client:
            response = client.post('/glossary', data={'_delete': 'invalid_id'})
            self.assertEqual(response.status_code, 302)  # Expecting a redirect
            self.assertTrue(response.headers['Location'].endswith('/glossary'))  # Redirect to glossary page

    def test_improve_text_1(self):
        """
        Test the improve_text API endpoint with valid input data.

        This test verifies that the API returns the expected response
        when provided with valid text and improvement type.
        """
        # Prepare test data
        test_data = {
            "text": "Original text",
            "type": "grammar"
        }

        # Make a POST request to the API endpoint
        response = self.client.post('/api/improve-text',
                                    data=json.dumps(test_data),
                                    content_type='application/json')

        # Check the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response'], f"Improved text would appear here. Type: {test_data['type']}")

    def test_improve_text_exception_handling(self):
        """
        Test that the improve_text function handles exceptions properly.
        """
        # Test with invalid JSON data
        response = self.client.post('/api/improve-text',
                                    data='invalid json',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_index_1(self):
        """
        Test that the index route returns the landing page template.

        This test verifies that when the root URL ("/") is accessed,
        the index function renders and returns the "landing.html" template.
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'landing.html', response.data)

    def test_information_1(self):
        """
        Test the information route when a POST request is made and the worker's identification method is successful.

        This test verifies that:
        1. The route handles POST requests correctly.
        2. The worker's identification method is called with the form data.
        3. A success flash message is set when the identification is successful.
        4. The template is rendered with the correct data.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.identification.return_value = True
            mock_worker.get_identification.return_value = {"test": "data"}

            response = self.client.post('/information', data={'key': 'value'})

            self.assertEqual(response.status_code, 200)
            mock_worker.identification.assert_called_once_with({'key': 'value'})
            mock_worker.get_identification.assert_called_once()

            # Check if the success flash message is set
            with self.client.session_transaction() as session:
                flash_messages = session['_flashes']
                self.assertIn(('success', 'Contact information updated successfully'), flash_messages)

            # Check if the template is rendered with the correct data
            self.assertTrue(b'test' in response.data and b'data' in response.data)
            self.assertTrue(b'debug' in response.data)

    def test_information_2(self):
        """
        Test case for the information route when a POST request is made and the update is unsuccessful.

        This test verifies that when a POST request is made to the /information route and the
        worker.identification method returns False (indicating an unsuccessful update), the route
        flashes an error message and renders the information template with the correct data.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.identification.return_value = False
            mock_worker.get_identification.return_value = {"test": "data"}

            with self.app.test_request_context('/information', method='POST', data={}):

                response = information()

                # Assert that the flash message for error was called
                flash.assert_called_once_with("Error updating contact information", "danger")

                # Assert that the template was rendered with the correct data
                self.assertIn('information.html', response[0])
                self.assertIn(b'"test": "data"', response[0])
                self.assertIn(b'"debug": true', response[0])

    def test_information_3(self):
        """
        Test case for the information route when the request method is not POST.

        This test verifies that the information route correctly handles GET requests
        by rendering the information.html template with the appropriate payload and debug flag.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.get_identification.return_value = {"test_data": "test_value"}

            with patch('flask.render_template') as mock_render_template:
                mock_render_template.return_value = "Mocked template"

                response = self.client.get('/information')

                self.assertEqual(response.status_code, 200)
                mock_worker_instance.get_identification.assert_called_once()
                mock_render_template.assert_called_once_with(
                    "information.html", 
                    payload={"test_data": "test_value"}, 
                    debug=True
                )

    def test_information_exception_handling(self):
        """
        Test exception handling in the information route.
        """
        # Mock Worker to raise an exception
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker.side_effect = Exception("Test exception")

            response = self.client.get('/information')

            # Check if the response contains the error message
            self.assertIn(b"Error loading information page", response.data)
            self.assertIn(b"Test exception", response.data)
            self.assertEqual(response.status_code, 200)  # The route returns 200 even for errors

    def test_linkedin_import_page(self):
        """
        Test that the LinkedIn import page loads correctly without any edge cases.
        """
        response = self.client.get('/linkedin-import')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'linkedin_import.html', response.data)

    def test_linkedin_import_page_1(self):
        """
        Test that the LinkedIn import page loads correctly and renders the expected template.
        """
        response = self.client.get('/linkedin-import')
        self.assertEqual(response.status_code, 200)
        self.assert_template_used('linkedin_import.html')

    def test_linkedin_settings_1(self):
        """
        Test that the LinkedIn settings page loads correctly and returns the expected template.
        """
        response = self.client.get('/linkedin-settings')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('linkedin_settings.html' in response.get_data(as_text=True))

    def test_linkedin_settings_page_load(self):
        """
        Test that the LinkedIn settings page loads correctly.
        """
        response = self.client.get('/linkedin-settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'linkedin_settings.html', response.data)

    def test_skills_2(self):
        """
        Test case for skills route when deleting a skill fails.

        This test verifies that when a POST request is made to delete a skill,
        and the deletion operation fails, the function redirects to the skills page
        and displays an error flash message.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = False

            response = self.client.post('/skills', data={'_delete': 'test_skill_id'})

            mock_worker.delete_entry.assert_called_once_with("skill", "test_skill_id")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/skills')

            with self.client.session_transaction() as session:
                flash_messages = session['_flashes']
                self.assertEqual(len(flash_messages), 1)
                self.assertEqual(flash_messages[0], ('error', 'Error deleting skill'))

    def test_skills_add_skill_missing_short_description(self):
        """
        Test adding a new skill with a missing short description.
        This tests the edge case where a new skill is submitted without the required short description.
        """
        test_data = {
            'new1_category': 'Test Category',
            'new1_subcategory': 'Test Subcategory',
            'new1_employer_dropdown': '',
            'new1_position_dropdown': '',
            'new1_shortdesc': '',  # Empty short description
            'new1_longdesc': 'Test long description'
        }
        response = self.client.post('/skills', data=test_data)
        self.assertEqual(response.status_code, 302)  # Expect a redirect

        # Verify that no skill was added
        with patch('pylaform.database.templateWorker.Worker.add_skill') as mock_add_skill:
            mock_add_skill.assert_not_called()

    def test_skills_delete(self):
        """
        Test the skills route for deleting a skill.

        This test verifies that when a POST request is made to the skills route
        with a '_delete' parameter, the skill is deleted and the user is redirected
        to the skills page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/skills', data={'_delete': 'skill_id_123'})

            mock_worker.delete_entry.assert_called_once_with("skill", "skill_id_123")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/skills')

    def test_skills_delete_nonexistent_skill(self):
        """
        Test deleting a non-existent skill ID.
        This tests the edge case where the delete operation is attempted on a skill that doesn't exist.
        """
        with patch('pylaform.database.templateWorker.Worker.delete_entry', return_value=False) as mock_delete:
            response = self.client.post('/skills', data={'_delete': 'nonexistent_skill_id'})
            self.assertEqual(response.status_code, 302)  # Expect a redirect
            mock_delete.assert_called_once_with("skill", "nonexistent_skill_id")
            # Check if the appropriate flash message is set
            with self.client.session_transaction() as session:
                flash_messages = session['_flashes']
                self.assertIn(('error', 'Error deleting skill'), flash_messages)

    def test_summary_1(self):
        """
        Test the summary route when a POST request is made to delete a summary item.

        This test verifies that when a POST request is made to the summary route
        with a '_delete' parameter in the form data, the corresponding summary item
        is deleted and the user is redirected to the summary page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/summary', data={
                '_delete': '123'  # Assuming '123' is a valid summary item ID
            }, follow_redirects=True)

            # Assert that delete_entry was called with correct arguments
            mock_worker.delete_entry.assert_called_once_with("summary", "123")

            # Assert that the response is a redirect to the summary page
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Summary', response.data)  # Assuming 'Summary' is in the page title

    def test_summary_2(self):
        """
        Test case for the summary route with specific path constraints.

        This test verifies the behavior of the summary route when:
        - The request method is POST
        - The form contains a '_delete' key
        - The delete_id is falsy
        - There are existing items to update (keys with "_shortdesc" not starting with "new")
        - There are new items to add (keys with "_shortdesc" starting with "new")
        - Updates are made successfully

        Expected outcome:
        - The function should redirect to the 'summary' route
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.delete_entry.return_value = False
            mock_worker_instance.update_summary.return_value = True
            mock_worker_instance.add_summary.return_value = True

            form_data = {
                '_delete': '',  # Falsy delete_id
                'existing_shortdesc': 'Updated Short Description',
                'existing_longdesc': 'Updated Long Description',
                'existing_summaryorder': '1',
                'new1_shortdesc': 'New Short Description',
                'new1_longdesc': 'New Long Description',
                'new1_summaryorder': '2'
            }

            response = self.client.post('/summary', data=form_data)

            self.assertEqual(response.status_code, 302)  # Expecting a redirect
            self.assertEqual(response.location, '/summary')  # Redirect to summary route

    def test_summary_3(self):
        """
        Test case for the summary route when updating existing summaries and adding new ones.

        This test verifies the behavior of the summary route when:
        1. A POST request is made
        2. There's no deletion request
        3. Existing summaries are updated
        4. New summaries are added
        5. Changes are successfully made

        Expected outcome: The route should redirect to the summary page after processing the updates.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.update_summary.return_value = True
            mock_worker.add_summary.return_value = True

            form_data = {
                'existing_1_shortdesc': 'Updated Short Description',
                'existing_1_longdesc': 'Updated Long Description',
                'existing_1_summaryorder': '1',
                'new1_shortdesc': 'New Short Description',
                'new1_longdesc': 'New Long Description',
                'new1_summaryorder': '2'
            }

            response = self.client.post('/summary', data=form_data)

            self.assertEqual(response.status_code, 302)  # Expect a redirect
            self.assertEqual(response.location, '/summary')  # Redirect to summary page

            # Verify that update_summary and add_summary were called
            mock_worker.update_summary.assert_called()
            mock_worker.add_summary.assert_called()

    def test_summary_4(self):
        """
        Test the summary route when a POST request is made with specific form data.

        This test covers the following path:
        - POST request is made
        - '_delete' is in form_data but delete_id is falsy
        - Existing summary is updated (key with "_shortdesc" but not starting with "new")
        - New summary is added (key with "_shortdesc" and starting with "new")
        - Updates are made successfully

        Expected outcome: Redirect to the summary page
        """
        with self.app.test_request_context():
            mock_worker = MagicMock()
            mock_worker.delete_entry.return_value = False
            mock_worker.update_summary.return_value = False
            mock_worker.add_summary.return_value = True

            with patch('app.Worker', return_value=mock_worker):
                response = self.client.post('/summary', data={
                    '_delete': '',  # Falsy delete_id
                    'existing_shortdesc': 'Updated Summary',
                    'existing_longdesc': 'Updated Long Description',
                    'existing_summaryorder': '1',
                    'new1_shortdesc': 'New Summary',
                    'new1_longdesc': 'New Long Description',
                    'new1_summaryorder': '2'
                })

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('summary'))

            mock_worker.delete_entry.assert_not_called()
            mock_worker.update_summary.assert_called()
            mock_worker.add_summary.assert_called()

    def test_summary_exception_handling(self):
        """
        Test that the summary route handles exceptions correctly and returns a 500 error.
        """
        # Mock the Worker to raise an exception
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker.side_effect = Exception("Test exception")

            response = self.client.get('/summary')

            self.assertEqual(response.status_code, 500)
            self.assertIn("Error: Test exception", response.data.decode())

    def test_achievements_1(self):
        """
        Test deleting an achievement via POST request.

        This test verifies that when a POST request is made to delete an achievement,
        the achievement is deleted successfully and the user is redirected to the
        achievements page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/achievements', data={
                '_delete_achievement': 'test_achievement_id'
            })

            mock_worker.delete_entry.assert_called_once_with("standalone_achievement", "test_achievement_id")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/achievements')

    def test_achievements_3_2(self):
        """
        Test case for achievements route when adding a new achievement fails and updating an existing one succeeds.

        This test verifies that:
        1. A new achievement is attempted to be added but fails.
        2. An existing achievement is successfully updated.
        3. The function redirects to the achievements page after processing.

        Path constraints covered:
        - request.method == 'POST'
        - not ('_delete_achievement' in form_data)
        - key.startswith('new-achievement-') and key.endswith('_title')
        - title exists (for new achievement)
        - not (result) for new achievement addition
        - f"{achievement_id}_title" in form_data (for existing achievement)
        - (title != current_title or description != current_desc or date != current_date or
           url != current_url or enabled != current_state or achievement_order != current_order)
        - result is True for existing achievement update
        - updates_made is True (new_added is False)

        Expected return: redirect(url_for('achievements'))
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.add_standalone_achievement.return_value = None  # Simulating failure
                mock_worker.get_all_achievements.return_value = [{
                    'SK': 'existing_achievement',
                    'title': 'Old Title',
                    'description': 'Old Description',
                    'date': '2023-01-01',
                    'url': 'http://old.com',
                    'state': 0,
                    'achievement_order': 1
                }]
                mock_worker.update_achievement.return_value = True

                form_data = {
                    'new-achievement-1_title': 'New Achievement',
                    'new-achievement-1_description': 'New Description',
                    'new-achievement-1_date': '2023-12-31',
                    'new-achievement-1_url': 'http://new.com',
                    'new-achievement-1_enabled': 'on',
                    'new-achievement-1_achievement_order': '2',
                    'existing_achievement_title': 'Updated Title',
                    'existing_achievement_description': 'Updated Description',
                    'existing_achievement_date': '2023-12-31',
                    'existing_achievement_url': 'http://updated.com',
                    'existing_achievement_enabled': 'on',
                    'existing_achievement_achievement_order': '2'
                }

                response = self.client.post('/achievements', data=form_data)

                # Assert that add_standalone_achievement was called but failed
                mock_worker.add_standalone_achievement.assert_called_once()
                
                # Assert that update_achievement was called and succeeded
                mock_worker.update_achievement.assert_called_once_with(
                    'existing_achievement',
                    title='Updated Title',
                    description='Updated Description',
                    date='2023-12-31',
                    url='http://updated.com',
                    state=1,
                    achievement_order=2
                )

                # Assert that the response is a redirect to the achievements page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('achievements'))

    def test_achievements_delete_nonexistent_achievement(self):
        """
        Test deleting a non-existent achievement.
        This test verifies that when attempting to delete an achievement that doesn't exist,
        the function handles it gracefully and redirects to the achievements page.
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.delete_entry.return_value = False  # Simulate deletion failure

                response = self.client.post('/achievements', data={
                    '_delete_achievement': 'nonexistent_id'
                })

                # Assert that delete_entry was called with correct arguments
                mock_worker.delete_entry.assert_called_once_with("standalone_achievement", "nonexistent_id")

                # Assert that we are redirected to the achievements page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('achievements'))

                # Check if a flash message was set (assuming flash messages are used)
                with self.client.session_transaction() as session:
                    flash_messages = dict(session['_flashes'])
                    self.assertIn('success', flash_messages)
                    self.assertEqual(flash_messages['success'], 'Achievement deleted successfully')

    def test_ai_config_1(self):
        """
        Test case for the ai_config function.

        This test verifies that the ai_config route renders the correct template.
        """
        with patch('flask.render_template') as mock_render:
            mock_render.return_value = 'AI Config Template'
            response = self.client.get('/ai-config')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('ai_config.html')

    def test_ai_status_1_2(self):
        """
        Test that the AI status endpoint returns the correct status and message.

        This test verifies that the /api/ai-status endpoint returns a JSON response
        with 'status' set to 'ok' and 'message' indicating that Amazon Q is available.
        """
        response = self.client.get('/api/ai-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, {"status": "ok", "message": "Amazon Q is available"})

    def test_ai_status_unauthorized_access(self):
        """
        Test that the ai_status endpoint returns a 401 Unauthorized error when accessed without authentication.
        """
        response = self.client.get('/api/ai-status')
        self.assertEqual(response.status_code, 401)

    def test_certifications_1_2(self):
        """
        Test the certifications route when deleting a certification.

        This test verifies that when a POST request is made to the certifications route
        with a '_delete' parameter in the form data, the route properly handles the deletion
        and redirects to the certifications page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/certifications', data={
                '_delete': '123'  # Simulating deletion of certification with ID 123
            })

            # Assert that delete_entry was called with correct arguments
            mock_worker.delete_entry.assert_called_once_with("certification", "123")

            # Assert that the response is a redirect to the certifications page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/certifications')

    def test_certifications_delete_nonexistent_certification(self):
        """
        Test deleting a non-existent certification.
        This tests the edge case where the delete operation is attempted on a certification ID that doesn't exist.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = False

            response = self.client.post('/certifications', data={
                '_delete': 'nonexistent_id'
            })

            mock_worker.delete_entry.assert_called_once_with("certification", "nonexistent_id")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('certifications'))

    def test_certifications_exception_handling_2(self):
        """
        Test exception handling in the certifications route.
        This verifies that when an exception occurs, the route returns a 500 error with the error message.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            MockWorker.side_effect = Exception("Test exception")

            response = self.client.get('/certifications')

            self.assertEqual(response.status_code, 500)
            self.assertIn("Error: Test exception", response.get_data(as_text=True))

    def test_education_post_3_2(self):
        """
        Test case for education_post() when adding a new school with focus areas.

        This test covers the following path constraints:
        - "_delete" not in form_data
        - "_" in key
        - "focus_" in key
        - school_id not in focus_data initially
        - len(focus_parts) > 1
        - "enabled" in data
        - "rowid" in data
        - school_id.startswith("new")
        - "name" in data
        - school_id in focus_data
        - focus["description"].strip() is truthy

        Expected result: Redirect to the education page after successful addition.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.add_school.return_value = "new_school_id"

            form_data = {
                "new1_name": "Test School",
                "new1_degree": "Test Degree",
                "new1_graddate": "2023",
                "new1_enabled": "on",
                "new1_rowid": "1",
                "new1_focus_1": "Test Focus Area"
            }

            response = self.client.post('/education', data=form_data)

            # Assert that add_school was called with correct parameters
            mock_worker.add_school.assert_called_once_with(
                name="Test School",
                degree="Test Degree",
                graddate="2023"
            )

            # Assert that add_focus was called with correct parameters
            mock_worker.add_focus.assert_called_once_with("new_school_id", "Test Focus Area")

            # Assert that the response is a redirect to the education page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/education')

    def test_education_post_delete_nonexistent_school_2(self):
        """
        Test deleting a non-existent school ID.
        This test verifies that when attempting to delete a school with an ID that doesn't exist,
        the function handles it gracefully and redirects to the education page without error.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = False  # Simulating failed deletion

            response = self.client.post('/education', data={
                '_delete': 'nonexistent_school_id'
            })

            # Assert that delete_entry was called with correct arguments
            mock_worker.delete_entry.assert_called_once_with("school", "nonexistent_school_id")

            # Assert that the response is a redirect to the education page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('education'))

            # Check that no success flash message was set
            with self.client.session_transaction() as session:
                self.assertNotIn('_flashes', session)

    def test_employment_1(self):
        """
        Test deleting an achievement in the employment route.

        This test verifies that when a POST request is made to delete an achievement,
        the achievement is successfully deleted and the user is redirected to the
        employment page.

        Path constraints:
        - request.method == "POST"
        - "_delete_achievement" in form_data
        - achievement_id and not achievement_id.startswith("new-achievement-")
        - achievement_id.startswith("achievement_")
        - success (deletion is successful)

        Expected return: redirect(url_for("employment"))
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.delete_entry.return_value = True

                response = self.client.post('/employment', data={
                    '_delete_achievement': 'achievement_123'
                })

                # Assert that delete_entry was called with correct arguments
                mock_worker.delete_entry.assert_called_once_with("achievement", "123")

                # Assert that a success flash message was set
                with self.client.session_transaction() as session:
                    flashes = dict(session['_flashes'])
                    self.assertIn('Achievement deleted successfully', flashes.values())

                # Assert that the response is a redirect to the employment page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('employment'))

    def test_employment_2(self):
        """
        Test deleting an achievement in the employment route.

        This test verifies that when a POST request is made to delete an achievement
        that doesn't start with "new-achievement-" or "achievement_", the achievement
        is successfully deleted and the user is redirected to the employment page.
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.delete_entry.return_value = True

                response = self.client.post('/employment', data={
                    '_delete_achievement': 'valid_achievement_id'
                })

                mock_worker.delete_entry.assert_called_once_with("achievement", "valid_achievement_id")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('employment'))

    def test_employment_3_2(self):
        """
        Test deleting an existing achievement that fails to delete.

        This test verifies that when attempting to delete an existing achievement
        with an ID starting with "achievement_", and the deletion fails, the function
        flashes an error message and redirects to the employment page.
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.delete_entry.return_value = False

                form_data = {'_delete_achievement': 'achievement_123'}
                response = self.client.post('/employment', data=form_data)

                # Assert that delete_entry was called with correct arguments
                mock_worker.delete_entry.assert_called_once_with("achievement", "123")

                # Check if the appropriate error message was flashed
                with self.client.session_transaction() as session:
                    flashed_messages = session['_flashes']
                    self.assertIn(('danger', 'Error deleting achievement'), flashed_messages)

                # Check if the response is a redirect to the employment page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('employment'))

    def test_employment_delete_nonexistent_achievement_2(self):
        """
        Test deleting a non-existent achievement in the employment route.
        This tests the edge case where the achievement ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.delete_entry.return_value = False

            response = self.client.post('/employment', data={
                '_delete_achievement': 'nonexistent_id'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting achievement', response.data)
            mock_worker_instance.delete_entry.assert_called_once_with("achievement", "nonexistent_id")

    def test_employment_delete_nonexistent_employer_2(self):
        """
        Test deleting a non-existent employer in the employment route.
        This tests the edge case where the employer ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.delete_entry.return_value = False
            mock_worker_instance.query.get_related_items.return_value = []

            response = self.client.post('/employment', data={
                '_delete_employer': 'nonexistent_id'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting employer', response.data)
            mock_worker_instance.delete_entry.assert_called_once_with("employer", "nonexistent_id")

    def test_employment_delete_nonexistent_position_2(self):
        """
        Test deleting a non-existent position in the employment route.
        This tests the edge case where the position ID doesn't exist in the database.
        """
        with patch('pylaform.database.templateWorker.Worker') as mock_worker:
            mock_worker_instance = mock_worker.return_value
            mock_worker_instance.delete_entry.return_value = False

            response = self.client.post('/employment', data={
                '_delete_position': 'nonexistent_id'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error deleting position', response.data)
            mock_worker_instance.delete_entry.assert_called_once_with("position", "nonexistent_id")

    def test_employment_iter_1(self):
        """
        Test the employment_iter route to ensure it renders the correct template with expected default values.

        This test verifies that:
        1. The route responds to GET requests.
        2. The correct template is rendered.
        3. The template is passed the expected default values for a new employer.
        """
        with self.app.test_request_context('/employment_iter?employer_id=test_id'):
            response = self.client.get('/employment_iter')

            self.assertEqual(response.status_code, 200)

            # Check if the correct template is used
            self.assertIn('employment_iter.html', response.get_data(as_text=True))

            # Check if the default values are passed to the template
            self.assertIn('id=test_id', response.get_data(as_text=True))
            self.assertIn('name=""', response.get_data(as_text=True))
            self.assertIn('location=""', response.get_data(as_text=True))
            self.assertIn('state=True', response.get_data(as_text=True))
            self.assertIn('positions=[]', response.get_data(as_text=True))

    def test_get_secret_key_1(self):
        """
        Test case for get_secret_key function when AWS_LAMBDA_FUNCTION_NAME is in os.environ.

        This test verifies that the function correctly retrieves the secret key from AWS Secrets Manager
        when running in a Lambda environment.
        """
        with patch('os.environ', {'AWS_LAMBDA_FUNCTION_NAME': 'test_function'}), \
             patch('boto3.client') as mock_boto3_client, \
             patch('json.loads') as mock_json_loads:

            # Mock the AWS Secrets Manager client
            mock_secrets_client = MagicMock()
            mock_boto3_client.return_value = mock_secrets_client

            # Mock the get_secret_value response
            mock_secrets_client.get_secret_value.return_value = {
                'SecretString': '{"FLASK_SECRET_KEY": "test_secret_key"}'
            }

            # Mock json.loads to return a dictionary
            mock_json_loads.return_value = {"FLASK_SECRET_KEY": "test_secret_key"}

            # Import the function after mocking

            # Call the function
            result = get_secret_key()

            # Assert that the correct secret key is returned
            self.assertEqual(result, "test_secret_key")

            # Assert that boto3.client was called with the correct arguments
            mock_boto3_client.assert_called_once_with('secretsmanager', region_name='us-west-2')

            # Assert that get_secret_value was called with the correct arguments
            mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="pylaform/flask-secret")

            # Assert that json.loads was called with the correct argument
            mock_json_loads.assert_called_once_with('{"FLASK_SECRET_KEY": "test_secret_key"}')

    def test_get_secret_key_2(self):
        """
        Test get_secret_key() when not running in AWS Lambda environment.

        This test verifies that the function returns the FLASK_SECRET_KEY from
        the environment variables if set, or the default 'dev-secret-key' if not set.
        """
        with patch.dict(os.environ, {}, clear=True):
            # Test when FLASK_SECRET_KEY is not set
            self.assertEqual(get_secret_key(), 'dev-secret-key')

        with patch.dict(os.environ, {'FLASK_SECRET_KEY': 'test-secret-key'}, clear=True):
            # Test when FLASK_SECRET_KEY is set
            self.assertEqual(get_secret_key(), 'test-secret-key')

    def test_get_summary_form_group_1(self):
        """
        Test that the get_summary_form_group route returns the correct template
        with the expected context variables.
        """
        with self.app.test_request_context():
            with patch('app.render_template') as mock_render:
                response = self.client.get('/get_summary_form_group/test_id')

                mock_render.assert_called_once_with(
                    "summary_iter.html",
                    form_group=True,
                    id="test_id",
                    shortdesc="",
                    longdesc="",
                    state=True
                )

                self.assertEqual(response.status_code, 200)

    def test_glossary_empty_terms(self):
        """
        Test the glossary route when no terms are returned by the worker.
        This tests the edge case where the glossary is empty.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.get_glossary.return_value = []

            response = self.client.get('/glossary')

            self.assertEqual(response.status_code, 200)
            mock_worker.get_glossary.assert_called_once()
            self.assertIn(b'glossary_index.html', response.data)
            self.assertIn(b'[]', response.data)  # Empty payload

    def test_glossary_post_1_2(self):
        """
        Test case for glossary_post() when deleting a new glossary item.

        This test verifies that when a POST request is made to delete a new glossary item
        (i.e., an item with an ID starting with "new"), the application correctly handles
        the request by not performing any database operation and redirecting to the
        glossary page.

        Path constraints:
        - "_delete" in form_data
        - delete_id exists
        - delete_id.startswith("new")

        Expected outcome:
        - No database operation is performed
        - Redirect to the glossary page
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker_instance = MockWorker.return_value

            response = self.client.post('/glossary', data={
                '_delete': 'new1'
            })

            # Assert that delete_entry was not called
            mock_worker_instance.delete_entry.assert_not_called()

            # Assert that we get redirected to the glossary page
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('glossary'))

    def test_improve_text_1_2(self):
        """
        Test the improve_text API endpoint with valid input data.

        This test verifies that the API returns the expected response
        when provided with valid text and improvement type.
        """
        # Prepare test data
        test_data = {
            "text": "Original text",
            "type": "grammar"
        }

        # Make a POST request to the API endpoint
        response = self.app.post('/api/improve-text',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response'], f"Improved text would appear here. Type: {test_data['type']}")

    def test_improve_text_with_invalid_json(self):
        """
        Test the improve_text function with invalid JSON input.

        This test verifies that the function handles the case where the request
        contains invalid JSON data, which is an exception explicitly handled in
        the focal method's implementation.
        """
        response = self.client.post('/api/improve-text',
                                    data='invalid json',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertTrue(isinstance(data['error'], str))

    def test_index_1_2(self):
        """
        Test that the index route returns the index.html template.

        This test verifies that when the root URL ("/") is accessed,
        the index function renders and returns the "index.html" template.
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'index.html', response.data)

    def test_index_nonexistent_template(self):
        """
        Test that the index route handles the case where the template file does not exist.
        This tests an edge case that is implicitly handled by Flask's render_template function.
        """
        # Temporarily change the template folder to a non-existent directory
        original_folder = self.app.template_folder
        self.app.template_folder = 'nonexistent_folder'

        response = self.client.get('/')

        # Restore the original template folder
        self.app.template_folder = original_folder

        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Template Not Found', response.data)

    def test_information_2_2(self):
        """
        Test case for the information route when a POST request is made and the worker's identification method fails.

        This test verifies that:
        1. The route handles POST requests correctly.
        2. The worker's identification method is called with the form data.
        3. An error flash message is set when the identification fails.
        4. The template is rendered with the correct data.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.identification.return_value = False
            mock_worker.get_identification.return_value = {"test": "data"}

            response = self.client.post('/information', data={'key': 'value'})

            self.assertEqual(response.status_code, 200)
            mock_worker.identification.assert_called_once_with({'key': 'value'})
            mock_worker.get_identification.assert_called_once()

            # Check if the error flash message is set
            with self.client.session_transaction() as session:
                flash_messages = session['_flashes']
                self.assertIn(('danger', 'Error updating contact information'), flash_messages)

            # Check if the template is rendered with the correct data
            self.assertTrue(b'test' in response.data and b'data' in response.data)
            self.assertTrue(b'debug' in response.data)

    def test_information_exception_handling_2(self):
        """
        Test that the information route properly handles exceptions and returns an error page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            MockWorker.side_effect = Exception("Test exception")
            
            response = self.client.get('/information')

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Error loading information page", response.data)
            self.assertIn(b"Test exception", response.data)
            self.assertIn(b"Go back to home", response.data)

    def test_landing_1(self):
        """
        Test that the landing route renders the correct template.

        This test verifies that when the /landing route is accessed,
        it returns a response with the "landing.html" template.
        """
        with patch('app.render_template') as mock_render_template:
            mock_render_template.return_value = 'Mocked landing template'
            response = self.client.get('/landing')
            self.assertEqual(response.status_code, 200)
            mock_render_template.assert_called_once_with("landing.html")

    def test_linkedin_import_page_1_2(self):
        """
        Test that the LinkedIn import page loads correctly and renders the expected template.

        This test verifies that:
        1. The /linkedin-import route returns a 200 OK status code.
        2. The response contains the rendered linkedin_import.html template.
        """
        response = self.client.get('/linkedin-import')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'linkedin_import.html', response.data)

    def test_linkedin_settings_1_2(self):
        """
        Test that the LinkedIn settings route renders the correct template.

        This test verifies that when accessing the /linkedin-settings route,
        the function returns the rendered 'linkedin_settings.html' template.
        """
        with self.app.test_request_context():
            response = self.client.get('/linkedin-settings')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'linkedin_settings.html', response.data)

    def test_login_1(self):
        """
        Test login route when POST request is made with invalid email.

        This test verifies that when a POST request is made to the login route
        with an email that doesn't exist in the database, the function flashes
        an error message and renders the login template again.
        """
        with patch('app.db') as mock_db:
            mock_table = MagicMock()
            mock_table.query.return_value = {'Items': []}
            mock_db.return_value = mock_table

            response = self.client.post('/login', data={
                'email': 'nonexistent@example.com',
                'password': 'testpassword'
            })

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid email or password', response.data)
            self.assertIn(b'login.html', response.data)

    def test_login_2(self):
        """
        Test login functionality when the user exists but the password is incorrect.

        This test verifies that:
        1. A POST request is made to the login route
        2. The user exists in the database
        3. The provided password is incorrect
        4. The login fails and the user is redirected back to the login page with an error message
        """
        with patch('app.db') as mock_db, \
             patch('app.verify_password') as mock_verify_password:

            # Mock the database query response
            mock_table = MagicMock()
            mock_db.return_value = mock_table
            mock_table.query.return_value = {
                'Items': [{'PK': 'USER#123', 'password': 'hashed_password'}]
            }

            # Mock the password verification to return False
            mock_verify_password.return_value = False

            # Make a POST request to the login route
            response = self.client.post('/login', data={
                'email': 'test@example.com',
                'password': 'incorrect_password'
            }, follow_redirects=True)

            # Assert that the response status code is 200 (OK)
            self.assertEqual(response.status_code, 200)

            # Assert that the login page is rendered again
            self.assertIn(b'login.html', response.data)

            # Assert that the error message is displayed
            self.assertIn(b'Invalid email or password', response.data)

            # Assert that the verify_password function was called
            mock_verify_password.assert_called_once()

    def test_login_3(self):
        """
        Test successful login with valid credentials and redirection.

        This test verifies that when a POST request is made to the login route
        with valid email and password, the user is successfully authenticated
        and redirected to the appropriate page.
        """
        with self.client as client:
            with patch('app.db') as mock_db, \
                 patch('app.verify_password') as mock_verify_password, \
                 patch('app.create_session') as mock_create_session:

                mock_table = MagicMock()
                mock_db.return_value = mock_table
                mock_table.query.return_value = {
                    'Items': [{
                        'PK': 'USER#123',
                        'password': 'hashed_password',
                        'name': 'Test User'
                    }]
                }
                mock_verify_password.return_value = True
                mock_create_session.return_value = 'session_id'

                response = client.post('/login', data={
                    'email': 'test@example.com',
                    'password': 'valid_password'
                })

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('landing'))

                with client.session_transaction() as session:
                    self.assertEqual(session['user_id'], '123')
                    self.assertEqual(session['session_id'], 'session_id')
                    self.assertEqual(session['user_name'], 'Test User')

    def test_login_invalid_email(self):
        """
        Test login with an invalid email address.
        This test verifies that the login function properly handles the case
        when an email address is not found in the database.
        """
        with patch('app.db') as mock_db:
            mock_table = MagicMock()
            mock_db.return_value = mock_table
            mock_table.query.return_value = {'Items': []}

            response = self.client.post('/login', data={
                'email': 'nonexistent@example.com',
                'password': 'somepassword'
            })

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid email or password', response.data)

    def test_login_invalid_password(self):
        """
        Test login with an invalid password for an existing email.
        This test verifies that the login function properly handles the case
        when the provided password does not match the stored password for a valid email.
        """
        with patch('app.db') as mock_db, patch('app.verify_password') as mock_verify:
            mock_table = MagicMock()
            mock_db.return_value = mock_table
            mock_table.query.return_value = {'Items': [{'PK': 'user#123', 'password': 'hashedpassword'}]}
            mock_verify.return_value = False

            response = self.client.post('/login', data={
                'email': 'valid@example.com',
                'password': 'wrongpassword'
            })

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid email or password', response.data)

    def test_logout_1(self):
        """
        Test that the logout function clears the session and redirects to the login page.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = '123'  # Set a session variable

            response = c.get('/logout')

            self.assertEqual(response.status_code, 302)  # Check for redirect
            self.assertEqual(response.location, '/login')  # Check redirect location

            # Check that the session has been cleared
            with c.session_transaction() as sess:
                self.assertNotIn('user_id', sess)

    def test_register_1(self):
        """
        Testcase 1 for def register():
        Path constraints: request.method == 'POST', not is_valid
        returns: render_template('register.html',
                                   email=email,
                                   first_name=first_name,
                                   last_name=last_name)
        """
        with patch('app.validate_password', return_value=(False, 'Invalid password')) as mock_validate:
            response = self.client.post('/register', data={
                'email': 'test@example.com',
                'password': 'invalid_password',
                'first_name': 'John',
                'last_name': 'Doe'
            })

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid password', response.data)
            self.assertIn(b'register.html', response.data)
            self.assertIn(b'test@example.com', response.data)
            self.assertIn(b'John', response.data)
            self.assertIn(b'Doe', response.data)

    def test_register_2(self):
        """
        Test case for registration when password validation passes but user creation fails.

        This test verifies that when a POST request is made to the register route,
        and the password validation passes but user creation fails, the function
        renders the register template with an error flash message and the submitted data.
        """
        with patch('app.validate_password', return_value=(True, "")):
            with patch('app.create_user', return_value=None):
                response = self.client.post('/register', data={
                    'email': 'test@example.com',
                    'password': 'password123',
                    'first_name': 'John',
                    'last_name': 'Doe'
                })

                self.assertEqual(response.status_code, 200)
                self.assertIn(b'register.html', response.data)
                self.assertIn(b'Email already registered', response.data)
                self.assertIn(b'test@example.com', response.data)
                self.assertIn(b'John', response.data)
                self.assertIn(b'Doe', response.data)

    def test_register_3(self):
        """
        Test successful user registration with valid input.

        This test verifies that when a POST request is made to the register route
        with valid user data, the user is successfully registered, a session is
        created, and the user is redirected to the index page.

        Path constraints:
        - request.method == 'POST'
        - Password is valid (is_valid is True)
        - User creation is successful (result is truthy)
        - Session creation is successful (session_id is truthy)

        Expected outcome: Redirect to the index page
        """
        with self.client as client:
            with patch('app.validate_password', return_value=(True, "")) as mock_validate:
                with patch('app.create_user', return_value="new_user_id") as mock_create_user:
                    with patch('app.create_session', return_value="new_session_id") as mock_create_session:
                        response = client.post('/register', data={
                            'email': 'test@example.com',
                            'password': 'ValidPassword123!',
                            'first_name': 'John',
                            'last_name': 'Doe'
                        })

                        mock_validate.assert_called_once()
                        mock_create_user.assert_called_once()
                        mock_create_session.assert_called_once()

                        self.assertEqual(response.status_code, 302)
                        self.assertEqual(response.location, url_for('index'))

                        with client.session_transaction() as session:
                            self.assertEqual(session['user_id'], "new_user_id")
                            self.assertEqual(session['session_id'], "new_session_id")

    def test_register_invalid_password(self):
        """
        Test the register function with an invalid password.
        This test verifies that when an invalid password is provided,
        the function flashes an error message and re-renders the registration form.
        """
        with patch('app.validate_password') as mock_validate_password:
            mock_validate_password.return_value = (False, "Invalid password")

            response = self.client.post('/register', data={
                'email': 'test@example.com',
                'password': 'invalid',
                'first_name': 'Test',
                'last_name': 'User'
            })

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Invalid password", response.data)
            self.assertIn(b'register.html', response.data)

    def test_skills_1(self):
        """
        Test the skills route when a POST request is made with no data.

        This test verifies that when a POST request is made to the skills route
        without any data, it returns a JSON response indicating failure and a 400 status code.
        """
        response = self.client.post('/skills', json=None)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'No data received')

    def test_skills_2_2(self):
        """
        Test the skills route when a valid POST request is made with data.
        
        This test verifies that when a POST request is made to the skills route
        with valid data, and the process_skills_form method is successful,
        the route returns a JSON response indicating success.
        """
        with patch('app.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.process_skills_form.return_value = (True, "Success message")

            test_data = {"skill": "Python", "level": "Expert"}
            response = self.client.post('/skills', 
                                        data=json.dumps(test_data),
                                        content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data, {'success': True, 'message': 'Skills updated successfully'})
            mock_worker.process_skills_form.assert_called_once_with(test_data)

    def test_skills_3(self):
        """
        Test the skills route when a POST request is made with valid data,
        but the worker.process_skills_form method returns False.

        This test verifies that:
        1. The route handles POST requests correctly.
        2. The worker's process_skills_form method is called with the correct data.
        3. When process_skills_form returns False, the route returns a JSON response
           with success set to False and the correct error message and status code.
        """
        test_data = {"skill": "Python", "level": "Expert"}

        with patch('app.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.process_skills_form.return_value = (False, "Error processing skills")

            response = self.client.post('/skills', 
                                        data=json.dumps(test_data),
                                        content_type='application/json')

            self.assertEqual(response.status_code, 400)
            response_data = json.loads(response.data)
            self.assertFalse(response_data['success'])
            self.assertEqual(response_data['message'], "Error processing skills")

            mock_worker.process_skills_form.assert_called_once_with(test_data)

    def test_skills_empty_json_data(self):
        """
        Test the skills route when POST request is made with empty JSON data.
        This should return a 400 error with a specific error message.
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                response = self.client.post('/skills', 
                                            data=json.dumps({}),
                                            content_type='application/json')

                self.assertEqual(response.status_code, 400)
                data = json.loads(response.data)
                self.assertEqual(data, {'success': False, 'message': 'No data received'})

    def test_skills_worker_exception(self):
        """
        Test the skills route when the Worker throws an exception.
        This should return a 500 error with the exception message.
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.process_skills_form.side_effect = Exception("Test exception")

                response = self.client.post('/skills', 
                                            data=json.dumps({"test": "data"}),
                                            content_type='application/json')

                self.assertEqual(response.status_code, 500)
                data = json.loads(response.data)
                self.assertEqual(data, {'success': False, 'message': 'Test exception'})

    def test_summary_1_2(self):
        """
        Test case for the summary route when deleting an item.

        This test verifies that when a POST request is made to the summary route
        with a '_delete' parameter in the form data, the corresponding item is
        deleted and the user is redirected to the summary page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = True

            response = self.client.post('/summary', data={'_delete': 'test_summary_id'})

            mock_worker.delete_entry.assert_called_once_with("summary", "test_summary_id")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/summary')

    def test_summary_2_2(self):
        """
        Test the summary route for updating existing summaries and adding new ones.

        This test verifies that when a POST request is made to the summary route:
        1. Existing summaries are updated
        2. New summaries are added
        3. The route redirects to the summary page after processing the updates
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.update_summary.return_value = True
                mock_worker.add_summary.return_value = True

                form_data = {
                    'existing_uuid_shortdesc': 'Updated Short Description',
                    'existing_uuid_longdesc': 'Updated Long Description',
                    'existing_uuid_summaryorder': '1',
                    'new1_shortdesc': 'New Short Description',
                    'new1_longdesc': 'New Long Description',
                    'new1_summaryorder': '2'
                }

                response = self.client.post('/summary', data=form_data)

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('summary'))

                mock_worker.update_summary.assert_called()
                mock_worker.add_summary.assert_called()

    def test_summary_3_2(self):
        """
        Test case for updating existing summaries and adding new ones in the summary route.

        This test verifies that when a POST request is made to the summary route:
        1. Existing summaries are updated correctly
        2. New summaries are added successfully
        3. The function redirects to the summary page after processing

        Path constraints covered:
        - request.method == 'POST'
        - not ('_delete' in form_data)
        - "_shortdesc" in key and len(key.split("_")[0]) == 36 (for existing summaries)
        - "_shortdesc" in key and len(key.split("_")[0]) != 36 (for new summaries)
        - shortdesc.strip() or longdesc.strip() (for new summaries)
        - success (for both update and add operations)
        - updates_made is True
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.update_summary.return_value = True
                mock_worker.add_summary.return_value = True

                form_data = {
                    # Existing summary (UUID length is 36)
                    '12345678-1234-5678-1234-567812345678_shortdesc': 'Updated Short Description',
                    '12345678-1234-5678-1234-567812345678_longdesc': 'Updated Long Description',
                    '12345678-1234-5678-1234-567812345678_summaryorder': '1',
                    
                    # New summary (key doesn't start with UUID)
                    'new1_shortdesc': 'New Short Description',
                    'new1_longdesc': 'New Long Description',
                    'new1_summaryorder': '2'
                }

                response = self.client.post('/summary', data=form_data)

                # Assert that update_summary was called for existing summary
                mock_worker.update_summary.assert_called_with(
                    '12345678-1234-5678-1234-567812345678',
                    shortdesc='Updated Short Description',
                    longdesc='Updated Long Description',
                    summaryorder=1
                )

                # Assert that add_summary was called for new summary
                mock_worker.add_summary.assert_called_with(
                    shortdesc='New Short Description',
                    longdesc='New Long Description',
                    summaryorder=2
                )

                # Assert that the response is a redirect to the summary page
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('summary'))

    def test_update_skills_1(self):
        """
        Test case for update_skills function when the skills are successfully updated.

        This test verifies that when the skills are successfully updated:
        1. The function redirects to the skills index page
        2. A success flash message is set
        """
        with self.app.test_request_context():
            with patch('pylaform.database.templateWorker.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.process_skills_form.return_value = (True, "Success message")

                response = self.client.post('/skills/update', data={'some': 'data'})

                mock_worker.process_skills_form.assert_called_once_with({'some': 'data'})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('skills.index'))

                # Check if the success flash message is set
                with self.client.session_transaction() as session:
                    flash_messages = session['_flashes']
                    self.assertIn(('success', 'Skills updated successfully'), flash_messages)

    def test_update_skills_2(self):
        """
        Test case for update_skills() when the update is unsuccessful.

        This test verifies that when the worker.process_skills_form() returns False,
        indicating an unsuccessful update, the function flashes an error message
        and redirects to the skills index page.
        """
        with self.app.test_request_context():
            with patch('app.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.process_skills_form.return_value = (False, "Error updating skills")

                response = self.client.post('/skills/update', data={'skill': 'test'})

                mock_worker.process_skills_form.assert_called_once_with({'skill': 'test'})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, url_for('skills.index'))

                with self.client.session_transaction() as session:
                    flash_messages = dict(session['_flashes'])
                    self.assertEqual(flash_messages['error'], 'Error updating skills')


if __name__ == '__main__':
    unittest.main()


class TestGetSecretKey(unittest.TestCase):

    def test_get_secret_key_aws_exception(self):
        """
        Test get_secret_key when an exception occurs during AWS Secrets Manager retrieval.
        This test verifies that the function falls back to the environment variable when 
        an exception is raised while trying to retrieve the secret from AWS Secrets Manager.
        """
        with patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test_lambda', 'FLASK_SECRET_KEY': 'fallback_key'}):
            with patch('boto3.client') as mock_boto3_client:
                mock_boto3_client.return_value.get_secret_value.side_effect = Exception('AWS Error')

                result = get_secret_key()

                self.assertEqual(result, 'fallback_key')



class TestUpdateSkills(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_update_skills_form_processing_failure(self):
        """
        Test the update_skills function when form processing fails.
        This tests the negative case where the worker.process_skills_form method returns False.
        """
        with self.app.test_request_context('/skills/update', method='POST'):
            with patch('app.Worker') as MockWorker:
                mock_worker = MockWorker.return_value
                mock_worker.process_skills_form.return_value = (False, "Error processing form")

                with patch('app.flash') as mock_flash, \
                     patch('app.redirect') as mock_redirect, \
                     patch('app.url_for') as mock_url_for:


                    response = update_skills()

                    mock_worker.process_skills_form.assert_called_once_with(request.form)
                    mock_flash.assert_called_once_with("Error processing form", "error")
                    mock_url_for.assert_called_once_with('skills.index')
                    mock_redirect.assert_called_once_with(mock_url_for.return_value)



class GlossaryPostTest(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_glossary_post_delete_nonexistent_entry(self):
        """
        Test deleting a non-existent glossary entry.
        This test verifies that when trying to delete a glossary entry that doesn't exist,
        the method handles it gracefully and redirects to the glossary page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.delete_entry.return_value = False  # Simulating failure to delete

            response = self.app.post('/glossary', data={'_delete': 'nonexistent_id'})

            mock_worker.delete_entry.assert_called_once_with("glossary", "nonexistent_id")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('glossary'))

    def test_glossary_post_empty_new_term(self):
        """
        Test adding a new glossary term with empty fields.
        This test verifies that when trying to add a new glossary term with empty
        term or definition, the method skips adding it and redirects to the glossary page.
        """
        with patch('pylaform.database.templateWorker.Worker') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.add_glossary.return_value = None  # Should not be called

            response = self.app.post('/glossary', data={
                'new1_term': '',
                'new1_definition': ''
            })

            mock_worker.add_glossary.assert_not_called()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, url_for('glossary'))
