#!/usr/bin/env python3
"""
Test Service Status Fix

This script tests if the service status check functions work correctly
after fixing the UserSettings attribute errors.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import create_app

def test_service_status():
    """Test the service status check functions"""
    print("🔧 Testing Service Status Fix...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Import the service status functions
            from webapp.routes.main_routes import check_llm_service_status, check_ocr_service_status, check_service_status
            
            print("\n📊 Testing LLM Service Status...")
            try:
                llm_status = check_llm_service_status()
                print(f"   ✅ LLM Service Status: {'Available' if llm_status else 'Not Available'}")
            except Exception as e:
                print(f"   ❌ LLM Service Status Error: {e}")
                return False
            
            print("\n📊 Testing OCR Service Status...")
            try:
                ocr_status = check_ocr_service_status()
                print(f"   ✅ OCR Service Status: {'Available' if ocr_status else 'Not Available'}")
            except Exception as e:
                print(f"   ❌ OCR Service Status Error: {e}")
                return False
            
            print("\n📊 Testing Overall Service Status...")
            try:
                service_status = check_service_status()
                print(f"   ✅ Service Status Check: Success")
                print(f"   📋 Services: {list(service_status.keys())}")
            except Exception as e:
                print(f"   ❌ Service Status Error: {e}")
                return False
            
            print("\n🎉 All service status checks passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error testing service status: {e}")
            return False

if __name__ == "__main__":
    print("🔧 Service Status Fix Test...")
    
    if test_service_status():
        print("✨ Service status fix test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Service status fix test failed!")
        sys.exit(1)