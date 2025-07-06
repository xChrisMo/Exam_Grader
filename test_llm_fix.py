#!/usr/bin/env python
"""
Test script to verify the LLM service JSON extraction fix.
"""

import sys
import json
from src.services.llm_service import LLMService
from src.services.mapping_service import MappingService
from utils.logger import logger

def test_llm_response():
    """Test the _get_llm_response method"""
    try:
        # Initialize LLM service
        logger.info("Initializing LLM service...")
        llm_service = LLMService()
        
        # Test the _get_llm_response method
        logger.info("Testing _get_llm_response method...")
        test_prompt = "Return a simple JSON with keys 'status' and 'message'"
        response = llm_service._get_llm_response(test_prompt)
        logger.info(f"Raw LLM response: {response}")
        
        # Test the _get_structured_response method
        logger.info("Testing _get_structured_response method...")
        unstructured_text = "The score is 8 out of 10. Feedback: Good work but needs improvement."
        structured_response = llm_service._get_structured_response(unstructured_text)
        logger.info(f"Structured response: {structured_response}")
        
        # Try to parse the structured response
        try:
            parsed_json = json.loads(structured_response)
            logger.info(f"Successfully parsed JSON: {parsed_json}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return False
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return False

def test_mapping_service():
    """Test the mapping service with the fixed LLM service"""
    try:
        # Initialize services
        logger.info("Initializing services...")
        llm_service = LLMService()
        mapping_service = MappingService(llm_service=llm_service)
        
        # Test a simple mapping operation
        logger.info("Testing mapping service...")
        test_content = """Question 1: What is the capital of France? (10 marks)
Answer: Paris is the capital of France.

Question 2: Explain the water cycle. (20 marks)
Answer: The water cycle involves evaporation, condensation, and precipitation."""
        
        # Extract questions and answers
        result = mapping_service.extract_questions_and_answers(test_content)
        logger.info(f"Extraction result: {result}")
        
        return len(result) > 0
    
    except Exception as e:
        logger.error(f"Mapping service test failed with error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting LLM service fix test...")
    
    llm_test_result = test_llm_response()
    logger.info(f"LLM response test {'passed' if llm_test_result else 'failed'}")
    
    mapping_test_result = test_mapping_service()
    logger.info(f"Mapping service test {'passed' if mapping_test_result else 'failed'}")
    
    if llm_test_result and mapping_test_result:
        logger.info("All tests passed! The fix was successful.")
        sys.exit(0)
    else:
        logger.error("Some tests failed. The fix may not be complete.")
        sys.exit(1)