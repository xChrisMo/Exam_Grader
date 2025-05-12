#!/usr/bin/env python
"""
Test script for LLM and OCR services.
This script tests both services to ensure they're working correctly.
"""

import os
import sys
from pathlib import Path
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.services.llm_service import LLMService
from src.services.ocr_service import OCRService
from utils.logger import Logger

# Initialize logger
logger = Logger().get_logger()

def test_llm_service():
    """Test the LLM service."""
    print("\n=== Testing LLM Service ===")
    try:
        # Initialize LLM service with DeepSeek configuration
        llm_service = LLMService(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url=os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com')
        )
        
        # Test simple completion
        test_prompt = "What is 2+2? Answer in one word."
        print(f"\nTest prompt: {test_prompt}")
        
        response = llm_service.client.chat.completions.create(
            model=llm_service.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": test_prompt}
            ],
            temperature=0.0
        )
        
        result = response.choices[0].message.content
        print(f"Response: {result}")
        
        print("\nLLM Service Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\nLLM Service Test: FAILED")
        print(f"Error: {str(e)}")
        return False

def test_ocr_service():
    """Test the OCR service."""
    print("\n=== Testing OCR Service ===")
    try:
        # Initialize OCR service with HandwritingOCR configuration
        ocr_service = OCRService(
            api_key=os.getenv('HANDWRITING_OCR_API_KEY'),
            base_url=os.getenv('HANDWRITING_OCR_API_URL')
        )
        
        # Test file validation
        print("\nTesting file validation...")
        test_file = "test.jpg"
        if not os.path.exists(test_file):
            print(f"Test file {test_file} not found. Please provide a test image.")
            return False
            
        # Test document upload and text extraction
        print("\nTesting document upload and text extraction...")
        extracted_text = ocr_service.extract_text_from_image(test_file)
        print(f"Extracted text: {extracted_text[:200]}...")  # Show first 200 chars
        
        print("\nOCR Service Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\nOCR Service Test: FAILED")
        print(f"Error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("Starting service tests...")
    
    # Test LLM service
    llm_success = test_llm_service()
    
    # Test OCR service
    ocr_success = test_ocr_service()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"LLM Service: {'PASSED' if llm_success else 'FAILED'}")
    print(f"OCR Service: {'PASSED' if ocr_success else 'FAILED'}")
    
    if llm_success and ocr_success:
        print("\nAll tests passed successfully!")
        return 0
    else:
        print("\nSome tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 