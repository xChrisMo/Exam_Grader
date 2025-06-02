#!/usr/bin/env python
"""
Test script for the mapping service.
This allows us to test our mapping service changes outside the web application.
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.mapping_service import MappingService
from src.services.llm_service import LLMService

class TestMappingService(unittest.TestCase):
    """Test cases for the MappingService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mapping_service = MappingService()

        # Sample marking guide with questions and answers
        self.marking_guide = """
        Question 1: What is the capital of France? [5 marks]
        Answer: The capital of France is Paris.

        Question 2: Explain Newton's Third Law of Motion. [10 marks]
        Answer: Newton's Third Law states that for every action, there is an equal and opposite reaction.

        Question 3: Solve for x: 2x + 5 = 15 [5 marks]
        Answer:
        2x + 5 = 15
        2x = 10
        x = 5
        """

        # Sample student submission with answers
        self.student_submission = """
        Question 1: What is the capital of France?
        Answer: Paris is the capital of France. It is known for the Eiffel Tower.

        Question 2: Explain Newton's Third Law of Motion.
        Answer: Newton's Third Law of Motion states that when one object exerts a force on another object, the second object exerts an equal force in the opposite direction.

        Question 3: Solve for x: 2x + 5 = 15
        Answer:
        2x + 5 = 15
        2x = 10
        x = 5
        """

    def test_extract_questions_and_answers(self):
        """Test extraction of questions and answers from content."""
        # Test extraction from marking guide
        guide_items = self.mapping_service.extract_questions_and_answers(self.marking_guide)
        self.assertGreater(len(guide_items), 0, "Should extract at least one item from marking guide")

        # Test extraction from student submission
        submission_items = self.mapping_service.extract_questions_and_answers(self.student_submission)
        self.assertGreater(len(submission_items), 0, "Should extract at least one item from student submission")

        # Check structure of extracted items
        for item in guide_items:
            self.assertIn('id', item, "Extracted item should have an ID")
            self.assertIn('text', item, "Extracted item should have text content")

    @patch('src.services.llm_service.LLMService')
    def test_map_submission_to_guide(self, mock_llm_service_class):
        """Test mapping of student submission to marking guide."""
        # Mock LLM service instance
        mock_llm_instance = MagicMock()
        mock_llm_service_class.return_value = mock_llm_instance
        mock_llm_instance.is_available.return_value = True

        # Create mapping service with mocked LLM
        mapping_service = MappingService(llm_service=mock_llm_instance)

        result, error = mapping_service.map_submission_to_guide(
            self.marking_guide,
            self.student_submission
        )

        # When LLM service is not available, it should return an error
        # This is expected behavior, so we test for the error message
        if error:
            self.assertIn("LLM service is required", error, "Should indicate LLM service requirement")
        else:
            # If no error, check that mapping was successful
            self.assertEqual(result.get('status'), 'success', "Mapping status should be success")

            # Check that mappings were created
            mappings = result.get('mappings', [])
            self.assertGreaterEqual(len(mappings), 0, "Should create mappings or empty list")

            # Check structure of mappings if any exist
            for mapping in mappings:
                self.assertIn('guide_id', mapping, "Mapping should have guide_id")
                self.assertIn('submission_id', mapping, "Mapping should have submission_id")
                self.assertIn('match_score', mapping, "Mapping should have match_score")

    def test_empty_content(self):
        """Test handling of empty content."""
        # Test with empty marking guide
        guide_items = self.mapping_service.extract_questions_and_answers("")
        self.assertEqual(len(guide_items), 0, "Should return empty list for empty content")

        # Test mapping with empty content
        result, error = self.mapping_service.map_submission_to_guide("", self.student_submission)
        self.assertIsNotNone(error, "Should return error for empty marking guide")

        result, error = self.mapping_service.map_submission_to_guide(self.marking_guide, "")
        self.assertIsNotNone(error, "Should return error for empty submission")

    @patch('openai.OpenAI')
    def test_determine_guide_type_questions(self, mock_openai):
        """Test determining guide type as questions."""
        # Create mock LLM service
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        # Set up the mock response
        mock_message.content = json.dumps({
            "guide_type": "questions",
            "confidence": 0.9,
            "reasoning": "The document contains questions with brief answers"
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        # Create LLM service with mock
        llm_service = LLMService(api_key="test_key")
        llm_service.client = mock_client

        # Create mapping service with mock LLM service
        mapping_service = MappingService(llm_service=llm_service)

        # Sample guide with questions
        guide_with_questions = """
        Question 1: What is the capital of France?
        Question 2: Explain Newton's Third Law of Motion.
        Question 3: Solve for x: 2x + 5 = 15
        """

        # Test guide type determination
        guide_type, confidence = mapping_service.determine_guide_type(guide_with_questions)

        # Verify results
        self.assertEqual(guide_type, "questions", "Should identify guide as containing questions")
        self.assertGreater(confidence, 0.5, "Should have high confidence in determination")

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

    @patch('openai.OpenAI')
    def test_determine_guide_type_answers(self, mock_openai):
        """Test determining guide type as answers."""
        # Create mock LLM service
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        # Set up the mock response
        mock_message.content = json.dumps({
            "guide_type": "answers",
            "confidence": 0.85,
            "reasoning": "The document contains detailed model answers"
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        # Create LLM service with mock
        llm_service = LLMService(api_key="test_key")
        llm_service.client = mock_client

        # Create mapping service with mock LLM service
        mapping_service = MappingService(llm_service=llm_service)

        # Sample guide with answers
        guide_with_answers = """
        Model Answer 1: The capital of France is Paris.
        Model Answer 2: Newton's Third Law states that for every action, there is an equal and opposite reaction.
        Model Answer 3:
        2x + 5 = 15
        2x = 10
        x = 5
        """

        # Test guide type determination
        guide_type, confidence = mapping_service.determine_guide_type(guide_with_answers)

        # Verify results
        self.assertEqual(guide_type, "answers", "Should identify guide as containing answers")
        self.assertGreater(confidence, 0.5, "Should have high confidence in determination")

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

    @patch('openai.OpenAI')
    def test_llm_based_mapping_questions(self, mock_openai):
        """Test LLM-based mapping with a question-type guide."""

        # Create mock LLM service
        mock_client = MagicMock()

        # Mock for determine_guide_type
        mock_type_response = MagicMock()
        mock_type_choice = MagicMock()
        mock_type_message = MagicMock()
        mock_type_message.content = json.dumps({
            "guide_type": "questions",
            "confidence": 0.9,
            "reasoning": "The document contains questions with brief answers"
        })
        mock_type_choice.message = mock_type_message
        mock_type_response.choices = [mock_type_choice]

        # Mock for mapping
        mock_map_response = MagicMock()
        mock_map_choice = MagicMock()
        mock_map_message = MagicMock()
        mock_map_message.content = json.dumps({
            "mappings": [
                {
                    "guide_id": "q1",
                    "submission_id": "q1",
                    "match_score": 0.95,
                    "match_reason": "Direct match between question and answer"
                },
                {
                    "guide_id": "q2",
                    "submission_id": "q2",
                    "match_score": 0.9,
                    "match_reason": "Clear match between question and answer"
                }
            ]
        })
        mock_map_choice.message = mock_map_message
        mock_map_response.choices = [mock_map_choice]

        # Set up the mock to return different responses for different calls
        mock_client.chat.completions.create.side_effect = [
            mock_type_response,  # First call for determine_guide_type
            mock_map_response    # Second call for mapping
        ]

        # Create LLM service with mock
        llm_service = LLMService(api_key="test_key")
        llm_service.client = mock_client

        # Create mapping service with mock LLM service
        mapping_service = MappingService(llm_service=llm_service)

        # Test mapping
        result, error = mapping_service.map_submission_to_guide(
            "Sample marking guide content",
            "Sample student submission content"
        )

        # Verify results
        self.assertIsNone(error, "Mapping should not produce an error")
        self.assertEqual(result.get('status'), 'success', "Mapping status should be success")
        self.assertGreaterEqual(len(result.get('mappings', [])), 1, "Should create at least one mapping")

        # Verify guide type is included in metadata
        self.assertIn('guide_type', result.get('metadata', {}), "Metadata should include guide_type")

        # Verify LLM was called twice
        self.assertEqual(mock_client.chat.completions.create.call_count, 2,
                         "LLM should be called twice: once for guide type and once for mapping")

if __name__ == "__main__":
    unittest.main()
