#!/usr/bin/env python3
"""
Check OCR service status and available methods.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_ocr_status():
    """Check OCR service status and available methods."""
    print("🔍 OCR Service Status Check")
    print("=" * 50)
    
    # Check environment
    print("1. Environment Check:")
    render = os.getenv("RENDER")
    ocr_enabled = os.getenv("OCR_SERVICE_ENABLED", "true")
    print(f"   RENDER: {render}")
    print(f"   OCR_SERVICE_ENABLED: {ocr_enabled}")
    
    # Check API key
    api_key = os.getenv("HANDWRITING_OCR_API_KEY")
    if api_key:
        if "your_" in api_key or "here" in api_key:
            print(f"   HANDWRITING_OCR_API_KEY: ❌ Placeholder value")
        else:
            print(f"   HANDWRITING_OCR_API_KEY: ✅ Real value")
    else:
        print(f"   HANDWRITING_OCR_API_KEY: ❌ Not set")
    
    # Check available OCR methods
    print("\n2. Available OCR Methods:")
    
    # Check Tesseract
    try:
        import pytesseract
        print("   ✅ pytesseract: Available")
        
        # Check if Tesseract binary is available
        try:
            import subprocess
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("   ✅ tesseract binary: Available")
            else:
                print("   ❌ tesseract binary: Not available")
        except Exception as e:
            print(f"   ❌ tesseract binary: Not available ({e})")
            
    except ImportError:
        print("   ❌ pytesseract: Not available")
    
    # Check EasyOCR
    try:
        import easyocr
        print("   ✅ easyocr: Available")
    except ImportError:
        print("   ❌ easyocr: Not available")
    
    # Check PIL
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        print("   ✅ PIL (Basic Processing): Available")
    except ImportError:
        print("   ❌ PIL: Not available")
    
    # Test OCR service initialization
    print("\n3. OCR Service Test:")
    try:
        from src.services.consolidated_ocr_service import ConsolidatedOCRService
        
        ocr_service = ConsolidatedOCRService()
        print(f"   ✅ OCR service initialized")
        print(f"   OCR Enabled: {ocr_service.ocr_enabled}")
        print(f"   API Key Available: {ocr_service.api_key is not None}")
        
        # Test fallback methods
        print("\n4. Fallback Methods Test:")
        
        # Create a simple test image
        from PIL import Image
        import tempfile
        
        test_image = Image.new('RGB', (100, 50), color='white')
        test_path = tempfile.mktemp(suffix='.png')
        test_image.save(test_path)
        
        # Test Tesseract
        if hasattr(ocr_service, '_extract_with_tesseract'):
            try:
                result = ocr_service._extract_with_tesseract(test_path)
                print(f"   Tesseract: ✅ Working")
            except Exception as e:
                print(f"   Tesseract: ❌ Failed ({e})")
        
        # Test EasyOCR
        if hasattr(ocr_service, '_extract_with_easyocr'):
            try:
                result = ocr_service._extract_with_easyocr(test_path)
                print(f"   EasyOCR: ✅ Working")
            except Exception as e:
                print(f"   EasyOCR: ❌ Failed ({e})")
        
        # Test Basic Processing
        if hasattr(ocr_service, '_extract_with_basic_processing'):
            try:
                result = ocr_service._extract_with_basic_processing(test_path)
                print(f"   Basic Processing: ✅ Working")
            except Exception as e:
                print(f"   Basic Processing: ❌ Failed ({e})")
        
        # Clean up
        os.unlink(test_path)
        
    except Exception as e:
        print(f"   ❌ OCR service test failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ OCR Status Check Complete!")

if __name__ == "__main__":
    check_ocr_status()
