# test_ai_service.py

import unittest
from unittest.mock import patch, MagicMock
import json
import requests
from pylaform.services.ai_service import OllamaService


class TestAIService(unittest.TestCase):
    """Test the AI service module for resume improvements"""

    def setUp(self):
        """Set up test environment"""
        # Use host and port instead of base_url
        self.service = OllamaService(host="test-ollama-server", port="11434")
        self.service.model = "test-model"

    @patch('requests.post')
    def test_generate_improvement_success(self, mock_post):
        """Test successful text improvement generation"""
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Improved text here"}
        mock_post.return_value = mock_response

        # Call the service function
        result = self.service.generate_improvement("Original text", "tenet")

        # Verify the request was made properly
        mock_post.assert_called_once()

        # Check URL
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://test-ollama-server:11434/api/generate")

        # Check payload
        payload = json.loads(call_args[1]['data'])
        self.assertEqual(payload['model'], "test-model")
        self.assertIn("Original text", payload['prompt'])
        self.assertIn("expert resume coach", payload['prompt'].lower())

        # Check result
        self.assertEqual(result, {"response": "Improved text here"})

    @patch('requests.post')
    def test_generate_improvement_api_error(self, mock_post):
        """Test handling of API errors"""
        # Setup the mock to simulate an API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # Call the service function
        result = self.service.generate_improvement("Original text", "tenet")

        # Verify the result contains error information
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API Error: 500")
        self.assertEqual(result["details"], "Internal Server Error")

    @patch('requests.post')
    def test_generate_improvement_connection_error(self, mock_post):
        """Test handling of connection errors"""
        # Setup the mock to simulate a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Call the service function
        result = self.service.generate_improvement("Original text", "tenet")

        # Verify the result contains error information
        self.assertIn("error", result)
        self.assertIn("Connection error", result["error"])
        self.assertIn("Connection refused", result["error"])

    def test_invalid_improvement_type(self):
        """Test handling of invalid improvement type"""
        # Call the service with an invalid improvement type
        result = self.service.generate_improvement("Original text", "invalid_type")

        # Verify the result indicates an error
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Invalid improvement type")