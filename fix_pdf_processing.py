#!/usr/bin/env python3
"""
Comprehensive fix for PDF processing issues.
This script addresses both logging and OCR problems.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_logging_config():
    """Fix logging configuration to handle Windows file locking issues."""
    print("Fixing logging configuration...")
    
    # The logging fix has already been applied to utils/logger.py
    # Let's verify it works by testing log creation
    try:
        from utils.logger import logger
        logger.info("Testing logging configuration after fix")
        print("✓ Logging configuration is working")
        return True
    except Exception as e:
        print(f"✗ Logging configuration still has issues: {e}")
        return False

def create_fallback_ocr_service():
    """Create a fallback OCR service that handles API unavailability gracefully."""
    
    fallback_service_path = Path("src/services/fallback_ocr_service.py")
    
    fallback_code = '''"""
Fallback OCR service for when the main OCR API is unavailable.
This service provides basic text extraction without external dependencies.
"""

import logging
from typing import Union, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FallbackOCRService:
    """Fallback OCR service that provides basic functionality when API is unavailable."""
    
    def __init__(self):
        """Initialize fallback OCR service."""
        self.available = True
        logger.info("Fallback OCR service initialized")
    
    def is_available(self) -> bool:
        """Check if fallback service is available."""
        return self.available
    
    def extract_text_from_image(self, file_path: Union[str, Path]) -> str:
        """
        Attempt basic text extraction without external OCR API.
        
        Args:
            file_path: Path to the image or PDF file
            
        Returns:
            str: Empty string (fallback doesn't actually extract text)
            
        Raises:
            Exception: Always raises exception explaining limitation
        """
        logger.warning(f"Fallback OCR service cannot extract text from {file_path}")
        raise Exception(
            "OCR service is not available. This document appears to contain "
            "image-based content that requires OCR processing. Please check "
            "your OCR service configuration or try with a text-based document."
        )
'''
    
    try:
        with open(fallback_service_path, 'w', encoding='utf-8') as f:
            f.write(fallback_code)
        print(f"✓ Created fallback OCR service at {fallback_service_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to create fallback OCR service: {e}")
        return False

def improve_error_handling():
    """Improve error handling in the main parsing module."""
    
    # The error handling improvements have already been applied
    # Let's create an additional helper function for better user feedback
    
    helper_path = Path("src/parsing/pdf_helper.py")
    
    helper_code = '''"""
PDF processing helper functions with improved error handling.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

def analyze_pdf_content(file_path: str) -> Tuple[bool, str, dict]:
    """
    Analyze PDF content to provide better error messages.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (success, message, analysis_data)
    """
    try:
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}", {}
        
        doc = fitz.open(file_path)
        
        if doc.page_count == 0:
            doc.close()
            return False, "PDF document has no pages", {}
        
        analysis = {
            'page_count': doc.page_count,
            'has_text': False,
            'has_images': False,
            'total_text_length': 0,
            'pages_with_text': 0,
            'pages_with_images': 0
        }
        
        for page_num, page in enumerate(doc, 1):
            try:
                # Check for text
                page_text = page.get_text()
                text_length = len(page_text.strip())
                analysis['total_text_length'] += text_length
                
                if text_length > 0:
                    analysis['has_text'] = True
                    analysis['pages_with_text'] += 1
                
                # Check for images
                image_list = page.get_images()
                if image_list:
                    analysis['has_images'] = True
                    analysis['pages_with_images'] += 1
                    
            except Exception as e:
                logger.warning(f"Error analyzing page {page_num}: {e}")
        
        doc.close()
        
        # Generate helpful message
        if analysis['total_text_length'] == 0:
            if analysis['has_images']:
                message = (
                    "This PDF appears to be image-based (scanned document). "
                    "OCR processing is required but the OCR service is currently unavailable. "
                    "Please check your OCR configuration or try with a text-based PDF."
                )
            else:
                message = (
                    "This PDF contains no readable text content. "
                    "The document may be empty, corrupted, or require special processing."
                )
        elif analysis['total_text_length'] < 50:
            message = (
                f"This PDF contains very little text ({analysis['total_text_length']} characters). "
                "The document may be mostly images or have formatting issues."
            )
        else:
            message = f"PDF analysis successful. Contains {analysis['total_text_length']} characters of text."
        
        return True, message, analysis
        
    except Exception as e:
        return False, f"Error analyzing PDF: {str(e)}", {}

def get_helpful_error_message(file_path: str, original_error: str) -> str:
    """
    Generate a helpful error message based on PDF analysis.
    
    Args:
        file_path: Path to the PDF file
        original_error: Original error message
        
    Returns:
        str: Helpful error message for the user
    """
    try:
        success, analysis_message, analysis_data = analyze_pdf_content(file_path)
        
        if success:
            return f"{analysis_message} Original error: {original_error}"
        else:
            return f"{analysis_message} Original error: {original_error}"
            
    except Exception:
        return f"Unable to process PDF file. Original error: {original_error}"
'''
    
    try:
        with open(helper_path, 'w', encoding='utf-8') as f:
            f.write(helper_code)
        print(f"✓ Created PDF helper at {helper_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to create PDF helper: {e}")
        return False

def create_ocr_troubleshooting_guide():
    """Create a troubleshooting guide for OCR issues."""
    
    guide_path = Path("OCR_TROUBLESHOOTING.md")
    
    guide_content = '''# OCR Troubleshooting Guide

## Current Issue
The OCR service is configured but not reachable, causing PDF processing failures.

## Quick Fixes

### 1. Check OCR Service Status
Run the diagnostic script:
```bash
python test_ocr_config.py
```

### 2. Verify API Configuration
Check these environment variables:
- `HANDWRITING_OCR_API_KEY`: Your OCR API key
- `HANDWRITING_OCR_API_URL`: API endpoint (default: https://www.handwritingocr.com/api/v3)

### 3. Test Network Connectivity
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://www.handwritingocr.com/api/v3/documents
```

### 4. Common Solutions

#### API Key Issues
- Verify your API key is valid and active
- Check if you have sufficient API credits
- Ensure the key has proper permissions

#### Network Issues
- Check firewall settings
- Verify internet connectivity
- Try accessing the API from a different network

#### Service Unavailability
- The OCR service may be temporarily down
- Check the service status page
- Try again later

### 5. Temporary Workarounds

#### For Text-Based PDFs
- Ensure PDFs contain selectable text (not scanned images)
- Try converting scanned PDFs to text-based PDFs using other tools

#### For Image-Based Documents
- Convert images to text using local OCR tools
- Use online OCR services as a temporary solution
- Process documents in smaller batches

### 6. Alternative OCR Services
If the current service remains unavailable, consider:
- Google Cloud Vision API
- AWS Textract
- Azure Computer Vision
- Local OCR solutions (Tesseract)

## Error Messages and Solutions

### "OCR service not available"
- Check API key configuration
- Verify network connectivity
- Test API endpoint accessibility

### "No text content could be extracted"
- Document may be image-based and require OCR
- Try with a text-based PDF first
- Check document quality and format

### "Network error during OCR processing"
- Check internet connection
- Verify firewall settings
- Try again after a few minutes

## Getting Help
1. Run the diagnostic script: `python test_ocr_config.py`
2. Check the application logs in `logs/app.log`
3. Test with a simple text-based PDF first
4. Contact support with diagnostic results
'''
    
    try:
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        print(f"✓ Created troubleshooting guide at {guide_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to create troubleshooting guide: {e}")
        return False

def main():
    """Main fix function."""
    print("PDF Processing Fix Tool")
    print("=" * 50)
    
    success_count = 0
    total_fixes = 4
    
    # Fix 1: Logging configuration
    if fix_logging_config():
        success_count += 1
    
    # Fix 2: Create fallback OCR service
    if create_fallback_ocr_service():
        success_count += 1
    
    # Fix 3: Improve error handling
    if improve_error_handling():
        success_count += 1
    
    # Fix 4: Create troubleshooting guide
    if create_ocr_troubleshooting_guide():
        success_count += 1
    
    print(f"\nFix Summary: {success_count}/{total_fixes} fixes applied successfully")
    
    if success_count == total_fixes:
        print("✓ All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test with a simple text-based PDF")
        print("3. Check OCR configuration if image-based PDFs are needed")
        print("4. Review OCR_TROUBLESHOOTING.md for detailed guidance")
    else:
        print("⚠ Some fixes failed. Check the error messages above.")
    
    return success_count == total_fixes

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fix script failed with error: {e}")
        sys.exit(1)