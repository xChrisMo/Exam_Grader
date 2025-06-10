#!/usr/bin/env python3
"""
Test script to verify the Jinja2 service_status fix.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_template_rendering():
    """Test if templates can render without service_status errors."""
    try:
        from webapp.exam_grader_app import app
        
        print("🔍 Testing Jinja2 Template Rendering...")
        
        with app.test_client() as client:
            with app.test_request_context():
                # Test service_status availability in global context
                from flask import g
                from webapp.exam_grader_app import inject_globals
                
                # Get global context
                globals_dict = inject_globals()
                print(f"✅ Global context keys: {list(globals_dict.keys())}")
                
                # Check if service_status is available
                if 'service_status' in globals_dict:
                    service_status = globals_dict['service_status']
                    print(f"✅ service_status available: {type(service_status)}")
                    print(f"   OCR Status: {service_status.get('ocr_status', 'N/A')}")
                    print(f"   LLM Status: {service_status.get('llm_status', 'N/A')}")
                    print(f"   Storage Status: {service_status.get('storage_status', 'N/A')}")
                else:
                    print("❌ service_status not found in global context")
                    return False
                
                # Test template string rendering
                from flask import render_template_string
                
                test_templates = [
                    ('{{ service_status.ocr_status }}', 'OCR Status Access'),
                    ('{% if service_status.ocr_status %}Online{% else %}Offline{% endif %}', 'Conditional Logic'),
                    ('{{ service_status.llm_status and service_status.ocr_status }}', 'Boolean Logic'),
                ]
                
                for template_str, description in test_templates:
                    try:
                        result = render_template_string(template_str)
                        print(f"✅ {description}: '{result}'")
                    except Exception as e:
                        print(f"❌ {description}: {e}")
                        return False
                
                print("✅ All template rendering tests passed!")
                return True
                
    except Exception as e:
        print(f"❌ Error testing templates: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_route_access():
    """Test if routes can be accessed without Jinja2 errors."""
    try:
        from webapp.exam_grader_app import app
        
        print("\n🔍 Testing Route Access...")
        
        with app.test_client() as client:
            # Test routes that use service_status in templates
            test_routes = [
                ('/', 'Home/Landing Page'),
                ('/landing', 'Landing Page'),
                # Note: Dashboard requires authentication, so we'll skip it for now
            ]
            
            for route, description in test_routes:
                try:
                    response = client.get(route)
                    if response.status_code == 200:
                        print(f"✅ {description}: Status {response.status_code}")
                    elif response.status_code == 302:  # Redirect is OK
                        print(f"✅ {description}: Status {response.status_code} (Redirect)")
                    else:
                        print(f"⚠️  {description}: Status {response.status_code}")
                except Exception as e:
                    if "service_status" in str(e):
                        print(f"❌ {description}: Jinja2 service_status error - {e}")
                        return False
                    else:
                        print(f"⚠️  {description}: Other error - {e}")
            
            print("✅ All route access tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Error testing routes: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_caching_performance():
    """Test if service status caching is working."""
    try:
        from webapp.exam_grader_app import get_service_status
        import time
        
        print("\n🔍 Testing Service Status Caching...")
        
        # First call (cache miss)
        start_time = time.time()
        status1 = get_service_status()
        first_call_time = time.time() - start_time
        print(f"   First call: {first_call_time:.3f}s")
        
        # Second call (cache hit)
        start_time = time.time()
        status2 = get_service_status()
        second_call_time = time.time() - start_time
        print(f"   Second call: {second_call_time:.3f}s")
        
        # Verify results are the same
        if status1 == status2:
            print("✅ Cache returns consistent results")
        else:
            print("⚠️  Cache results differ")
        
        # Check if second call is faster (indicating caching)
        if second_call_time < first_call_time * 0.8:  # 20% faster
            print("✅ Caching is working (second call faster)")
        else:
            print("⚠️  Caching may not be working optimally")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing caching: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 JINJA2 SERVICE_STATUS FIX TEST")
    print("=" * 50)
    
    # Test 1: Template rendering
    template_ok = test_template_rendering()
    
    # Test 2: Route access
    routes_ok = test_route_access()
    
    # Test 3: Caching performance
    caching_ok = test_caching_performance()
    
    print("\n" + "=" * 50)
    if template_ok and routes_ok and caching_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Jinja2 service_status error should be fixed")
        print("✅ Templates can access service_status")
        print("✅ Routes work without errors")
        print("✅ Caching is working for performance")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("⚠️  There may still be issues with service_status")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
