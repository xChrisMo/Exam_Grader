#!/usr/bin/env python3
"""
Test script for the LLM-based answer comparison functionality.
This script demonstrates how the system evaluates how closely a student's answer
matches the model answer in a marking guide.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.grading_service import GradingService
from src.services.llm_service import LLMService


class TestAnswerComparison(unittest.TestCase):
    """Test cases for the answer comparison functionality."""

    @patch("openai.OpenAI")
    def setUp(self, mock_openai):
        """Set up test fixtures."""
        # Mock the OpenAI client
        self.mock_client = MagicMock()
        mock_openai.return_value = self.mock_client

        # Create LLM service with mock API key
        self.llm_service = LLMService(api_key="test_api_key")

        # Example question and answers for testing
        self.question = "What is the capital of France and describe its significance as a cultural center?"

        self.model_answer = """
        The capital of France is Paris. It is one of the world's most significant cultural 
        centers, known for its museums like the Louvre and Musée d'Orsay, architectural 
        landmarks like the Eiffel Tower and Notre-Dame, and its contributions to art, 
        literature, fashion, and cuisine. Paris has a rich history dating back to ancient 
        times and has been a center for philosophical and political movements like the 
        Age of Enlightenment and the French Revolution. The city continues to be a global 
        hub for the arts, education, and international affairs.
        """

        # Test case 1: Very close answer
        self.test_answer_good = """
        Paris is the capital of France. It's considered one of the most important cultural 
        centers in the world. The city is famous for its museums including the Louvre, 
        architectural landmarks like the Eiffel Tower, and its contributions to art, fashion, 
        and food. Paris has been historically important in the development of philosophy, 
        politics, and the arts. It remains a major global city for culture and international 
        relations.
        """

        # Test case 2: Partially correct answer
        self.test_answer_partial = """
        Paris is the capital of France. It has the Eiffel Tower and good food. It's a 
        popular tourist destination in Europe.
        """

        # Test case 3: Incorrect answer
        self.test_answer_incorrect = """
        The capital of France is Lyon. It's an important economic center with 
        beautiful architecture.
        """

    def test_compare_answers_good(self):
        """Test comparison with a good answer."""
        # Mock the API response for a good answer
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "score": 9.5,
                "feedback": "Excellent answer that covers all key points",
                "key_points_matched": [
                    "Paris is the capital",
                    "Cultural significance",
                    "Museums",
                    "Architecture",
                ],
                "key_points_missed": [],
            }
        )
        mock_response.choices = [MagicMock(message=mock_message)]
        self.mock_client.chat.completions.create.return_value = mock_response

        # Test the comparison
        score, feedback = self.llm_service.compare_answers(
            self.question, self.model_answer, self.test_answer_good, 10
        )

        # Verify results
        self.assertGreaterEqual(score, 9.0)
        self.assertIn("Excellent", feedback)

    def test_compare_answers_partial(self):
        """Test comparison with a partially correct answer."""
        # Mock the API response for a partially correct answer
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "score": 6.0,
                "feedback": "Partially correct but missing key details",
                "key_points_matched": ["Paris is the capital", "Eiffel Tower"],
                "key_points_missed": ["Cultural significance", "Museums", "History"],
            }
        )
        mock_response.choices = [MagicMock(message=mock_message)]
        self.mock_client.chat.completions.create.return_value = mock_response

        # Test the comparison
        score, feedback = self.llm_service.compare_answers(
            self.question, self.model_answer, self.test_answer_partial, 10
        )

        # Verify results
        self.assertLess(score, 8.0)
        self.assertGreater(score, 4.0)
        self.assertIn("Partially", feedback)

    def test_compare_answers_incorrect(self):
        """Test comparison with an incorrect answer."""
        # Mock the API response for an incorrect answer
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "score": 1.0,
                "feedback": "Incorrect answer. Paris is the capital of France, not Lyon.",
                "key_points_matched": [],
                "key_points_missed": [
                    "Paris is the capital",
                    "Cultural significance",
                    "Museums",
                    "Architecture",
                ],
            }
        )
        mock_response.choices = [MagicMock(message=mock_message)]
        self.mock_client.chat.completions.create.return_value = mock_response

        # Test the comparison
        score, feedback = self.llm_service.compare_answers(
            self.question, self.model_answer, self.test_answer_incorrect, 10
        )

        # Verify results
        self.assertLess(score, 3.0)
        self.assertIn("Incorrect", feedback)

    def test_error_handling(self):
        """Test error handling in answer comparison."""
        # Mock the API to raise an exception
        self.mock_client.chat.completions.create.side_effect = Exception("API error")

        # Test the comparison with error
        score, feedback = self.llm_service.compare_answers(
            self.question, self.model_answer, self.test_answer_good, 10
        )

        # Verify results
        self.assertEqual(score, 0)
        self.assertIn("Error", feedback)


if __name__ == "__main__":
    unittest.main()
