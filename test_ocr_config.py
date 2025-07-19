#!/usr/bin/env python3
"""
Simple test script to verify OCR service configuration and connectivity.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.consolidated_ocr_service import ConsolidatedOCRService, OCRServiceError
from utils.logger import logger

def test_ocr_service():
    """Test OCR service configuration and basic functionality."""
    print("Testing OCR Service Configuration...")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv("HANDWRITING_OCR_API_KEY")
    api_url = os.getenv("HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3")
    
    print(f"API Key configured: {'Yes' if api_key else 'No'}")
    print(f"API URL: {api_url}")
    print()
    
    # Initialize OCR service
    try:
        ocr_service = ConsolidatedOCRService(
            api_key=api_key,
            base_url=api_url,
            allow_no_key=True
        )
        print("✓ OCR service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OCR service: {e}")
        return False
    
    # Test service availability
    try:
        is_available = ocr_service.is_available()
        print(f"Service available: {'Yes' if is_available else 'No'}")
        
        if not is_available and not api_key:
            print("Note: Service is not available because no API key is configured.")
            print("To enable OCR functionality, set the HANDWRITING_OCR_API_KEY environment variable.")
        elif not is_available and api_key:
            print("Warning: API key is configured but service is not reachable.")
            print("Please check your internet connection and API key validity.")
            
    except Exception as e:
        print(f"✗ Error checking service availability: {e}")
        return False
    
    # Test health check
    try:
        health = ocr_service.health_check()
        print(f"Health check: {'Pass' if health else 'Fail'}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    print()
    print("Configuration Summary:")
    print("-" * 30)
    
    if api_key:
        print("✓ OCR service is configured and ready for use")
        print("  - Text extraction from images will use OCR")
        print("  - PDF fallback to OCR is available")
    else:
        print("⚠ OCR service is not fully configured")
        print("  - Only direct text extraction will work")
        print("  - Image files and scanned PDFs cannot be processed")
        print("  - To enable full functionality, configure HANDWRITING_OCR_API_KEY")
    
    return True

if __name__ == "__main__":
    try:
        test_ocr_service()
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)