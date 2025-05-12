#!/usr/bin/env python
"""
Test script for LLM and OCR services.
This script tests both services to ensure they're working correctly.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.llm_service import LLMService, LLMServiceError
from src.services.ocr_service import OCRService, OCRServiceError

class TestLLMService(unittest.TestCase):
    """Test cases for the LLMService class."""
    
    @patch('openai.OpenAI')
    def setUp(self, mock_openai):
        """Set up test fixtures."""
        # Mock the OpenAI client
        self.mock_client = MagicMock()
        mock_openai.return_value = self.mock_client
        
        # Create LLM service with mock API key
        self.llm_service = LLMService(api_key="test_api_key")
    
    def test_initialization(self):
        """Test LLM service initialization."""
        self.assertEqual(self.llm_service.api_key, "test_api_key")
        self.assertEqual(self.llm_service.model, "deepseek-reasoner")
        self.assertEqual(self.llm_service.temperature, 0.0)
    
    @patch('openai.OpenAI')
    def test_test_connection(self, mock_openai):
        """Test the connection test functionality."""
        # Mock the chat completions create method
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        self.mock_client.chat.completions.create.return_value = mock_response
        
        # Test the connection
        result = self.llm_service.test_connection()
        self.assertTrue(result)
        
        # Verify the API was called correctly
        self.mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_compare_answers(self, mock_openai):
        """Test the answer comparison functionality."""
        # Mock the chat completions create method
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"score": 8.5, "feedback": "Good answer"}'
        mock_response.choices = [MagicMock(message=mock_message)]
        self.mock_client.chat.completions.create.return_value = mock_response
        
        # Test answer comparison
        score, feedback = self.llm_service.compare_answers(
            "What is the capital of France?",
            "The capital of France is Paris.",
            "Paris is the capital of France.",
            10
        )
        
        # Verify results
        self.assertEqual(score, 8.5)
        self.assertEqual(feedback, "Good answer")
        
        # Verify the API was called correctly
        self.mock_client.chat.completions.create.assert_called_once()

class TestOCRService(unittest.TestCase):
    """Test cases for the OCRService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create OCR service with mock API key
        self.ocr_service = OCRService(api_key="test_api_key")
    
    def test_initialization(self):
        """Test OCR service initialization."""
        self.assertEqual(self.ocr_service.api_key, "test_api_key")
        self.assertTrue(self.ocr_service.base_url.endswith('/api/v3'))
    
    @patch('requests.post')
    def test_extract_text_from_image(self, mock_post):
        """Test the image text extraction functionality."""
        # Mock the requests.post method
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "text": "Sample extracted text"
            }
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create a temporary test file
        test_file = "test_image.jpg"
        with open(test_file, 'w') as f:
            f.write("dummy content")
        
        try:
            # Test text extraction
            result = self.ocr_service.extract_text_from_image(test_file)
            
            # Verify results
            self.assertEqual(result, "Sample extracted text")
            
            # Verify the API was called correctly
            mock_post.assert_called_once()
        finally:
            # Clean up the test file
            if os.path.exists(test_file):
                os.remove(test_file)
    
    @patch('requests.post')
    def test_extract_text_error_handling(self, mock_post):
        """Test error handling in text extraction."""
        # Mock the requests.post method to return an error
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "message": "API error"
        }
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        # Create a temporary test file
        test_file = "test_image.jpg"
        with open(test_file, 'w') as f:
            f.write("dummy content")
        
        try:
            # Test text extraction with error
            with self.assertRaises(OCRServiceError):
                self.ocr_service.extract_text_from_image(test_file)
        finally:
            # Clean up the test file
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()
