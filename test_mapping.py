#!/usr/bin/env python
"""
Test script for the mapping service.
This allows us to test our mapping service changes outside the web application.
"""

import sys
import os
import json

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.services.mapping_service import MappingService

def print_section(title, char="="):
    """Print a section header"""
    print(f"\n{char * 80}")
    print(f"{title.center(80)}")
    print(f"{char * 80}\n")

def print_item(item, prefix=""):
    """Print an extracted item"""
    print(f"{prefix}ID: {item.get('id', '')}")
    print(f"{prefix}Number: {item.get('number', '')}")
    print(f"{prefix}Type: {item.get('type', '')}")
    print(f"{prefix}Max Score: {item.get('max_score', '')}")
    print(f"{prefix}Text (truncated): {item.get('text', '')[:100]}...")
    if 'answer' in item and item['answer']:
        print(f"{prefix}Answer (truncated): {item.get('answer', '')[:100]}...")
    print(f"{prefix}{'-' * 40}")

def print_mapping(mapping):
    """Pretty print a mapping entry"""
    print(f"Guide Question: {mapping.get('guide_text', '')[:100]}...")
    print(f"Guide Answer: {mapping.get('guide_answer', '')[:100]}...")
    print(f"Submission Answer: {mapping.get('submission_answer', '')[:100]}...")
    print(f"Match Score: {mapping.get('match_score', 0)}")
    print("-" * 40)

def main():
    """Test the mapping service"""
    print_section("MAPPING SERVICE TEST")
    
    # Sample marking guide with questions and answers - properly formatted with questions separated
    marking_guide = """
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
    
    # Sample student submission with answers - properly formatted with questions separated
    student_submission = """
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
    
    # Create the mapping service
    mapping_service = MappingService()
    
    # Test extraction first
    print_section("EXTRACTION TEST", "-")
    print("Extracting questions and answers from marking guide...")
    guide_items = mapping_service.extract_questions_and_answers(marking_guide)
    print(f"Found {len(guide_items)} items in the marking guide:")
    for i, item in enumerate(guide_items):
        print(f"\nGuide Item #{i+1}:")
        print_item(item, "  ")
    
    print("\nExtracting questions and answers from student submission...")
    submission_items = mapping_service.extract_questions_and_answers(student_submission)
    print(f"Found {len(submission_items)} items in the student submission:")
    for i, item in enumerate(submission_items):
        print(f"\nSubmission Item #{i+1}:")
        print_item(item, "  ")
    
    # Map the submission to the guide
    print_section("MAPPING TEST", "-")
    print("Mapping submission to guide...")
    result, error = mapping_service.map_submission_to_guide(marking_guide, student_submission)
    
    if error:
        print(f"ERROR: {error}")
        return
    
    print(f"Mapping successful - {result.get('metadata', {}).get('mapping_count', 0)} items mapped")
    
    # Print the mapping results
    print_section("MAPPED ITEMS", "-")
    for mapping in result.get('mappings', []):
        print_mapping(mapping)
    
    # Print unmapped guide items
    print_section("UNMAPPED GUIDE ITEMS", "-")
    for item in result.get('unmapped_guide_items', []):
        print_item(item)
    
    # Print unmapped submission items
    print_section("UNMAPPED SUBMISSION ITEMS", "-")
    for item in result.get('unmapped_submission_items', []):
        print_item(item)
    
    # Save the result to a file for debugging
    with open('mapping_test_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to mapping_test_result.json")

if __name__ == "__main__":
    main() 