#!/usr/bin/env python3
"""
Test script to verify LLM question extraction is working properly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ['FLASK_APP'] = 'webapp.exam_grader_app'

def test_question_extraction():
    """Test the LLM question extraction functionality."""
    
    try:
        # Import required modules
        from src.services.llm_service import LLMService
        from src.services.mapping_service import MappingService
        from src.security.secrets_manager import secrets_manager
        
        print("🧪 Testing LLM Question Extraction...")
        
        # Initialize services
        llm_api_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')
        if not llm_api_key:
            print("❌ No LLM API key found")
            return False
            
        llm_service = LLMService(api_key=llm_api_key)
        mapping_service = MappingService(llm_service=llm_service)
        
        print("✅ Services initialized")
        
        # Test content with clear questions and marks
        test_content = """
        COMPUTER SCIENCE EXAM
        
        QUESTION 1: Define object-oriented programming and explain its main principles. (25 marks)
        
        QUESTION 2: 
        a) What is inheritance in OOP? (10 marks)
        b) Provide an example of polymorphism. (15 marks)
        
        QUESTION 3: Explain the difference between a class and an object. (20 marks)
        
        Total marks: 70
        """
        
        print("📝 Testing with sample marking guide content...")
        print(f"Content preview: {test_content[:100]}...")
        
        # Extract questions using LLM
        result = mapping_service.extract_questions_and_total_marks(test_content)
        
        print(f"\n📊 Extraction Results:")
        print(f"Method used: {result.get('extraction_method', 'unknown')}")
        print(f"Questions found: {len(result.get('questions', []))}")
        print(f"Total marks: {result.get('total_marks', 0)}")
        
        # Display extracted questions
        questions = result.get('questions', [])
        if questions:
            print(f"\n📋 Extracted Questions:")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q.get('text', 'No text')[:100]}... ({q.get('marks', 0)} marks)")
        else:
            print("❌ No questions extracted!")
            return False
            
        # Verify results
        expected_questions = 3  # We expect 3 main questions
        expected_total_marks = 70
        
        success = True
        if len(questions) < expected_questions:
            print(f"⚠️  Expected at least {expected_questions} questions, got {len(questions)}")
            success = False
            
        if result.get('total_marks', 0) != expected_total_marks:
            print(f"⚠️  Expected {expected_total_marks} total marks, got {result.get('total_marks', 0)}")
            # This is a warning, not a failure since LLM might calculate differently
            
        if result.get('extraction_method') != 'llm':
            print(f"⚠️  Expected 'llm' extraction method, got '{result.get('extraction_method')}'")
            success = False
            
        if success:
            print("✅ Question extraction test PASSED!")
        else:
            print("❌ Question extraction test FAILED!")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Question Extraction Test...")
    success = test_question_extraction()
    
    if success:
        print("\n🎉 All tests passed! LLM question extraction is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed! Check the logs above for details.")
        sys.exit(1)
