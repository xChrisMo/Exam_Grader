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
    
    def test_map_submission_to_guide(self):
        """Test mapping of student submission to marking guide."""
        result, error = self.mapping_service.map_submission_to_guide(
            self.marking_guide, 
            self.student_submission
        )
        
        # Check that mapping was successful
        self.assertIsNone(error, "Mapping should not produce an error")
        self.assertEqual(result.get('status'), 'success', "Mapping status should be success")
        
        # Check that mappings were created
        mappings = result.get('mappings', [])
        self.assertGreater(len(mappings), 0, "Should create at least one mapping")
        
        # Check structure of mappings
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

if __name__ == "__main__":
    unittest.main()
