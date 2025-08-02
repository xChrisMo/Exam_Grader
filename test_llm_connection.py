#!/usr/bin/env python3
"""
Test script to verify LLM training frontend-backend connection
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER = {
    "username": "test_user",
    "password": "test_password"
}

def test_api_endpoints():
    """Test the LLM training API endpoints"""
    
    print("🧪 Testing LLM Training API Connection...")
    
    # Create a session for maintaining cookies
    session = requests.Session()
    
    try:
        # Test 1: Check if LLM training page loads
        print("\n1. Testing LLM training page access...")
        response = session.get(f"{BASE_URL}/llm-training/")
        if response.status_code == 200:
            print("✅ LLM training page loads successfully")
        else:
            print(f"❌ LLM training page failed: {response.status_code}")
            return False
        
        # Test 2: Check training guides endpoint
        print("\n2. Testing training guides endpoint...")
        response = session.get(f"{BASE_URL}/llm-training/api/training-guides")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Training guides endpoint works: {len(data.get('guides', []))} guides found")
        else:
            print(f"❌ Training guides endpoint failed: {response.status_code}")
            if response.status_code == 401:
                print("   (This is expected if not logged in)")
        
        # Test 3: Check training jobs endpoint
        print("\n3. Testing training jobs endpoint...")
        response = session.get(f"{BASE_URL}/llm-training/api/training-jobs")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Training jobs endpoint works: {len(data.get('jobs', []))} jobs found")
        else:
            print(f"❌ Training jobs endpoint failed: {response.status_code}")
            if response.status_code == 401:
                print("   (This is expected if not logged in)")
        
        # Test 4: Check test submissions endpoint
        print("\n4. Testing test submissions endpoint...")
        response = session.get(f"{BASE_URL}/llm-training/api/test-submissions")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test submissions endpoint works: {len(data.get('submissions', []))} submissions found")
        else:
            print(f"❌ Test submissions endpoint failed: {response.status_code}")
            if response.status_code == 401:
                print("   (This is expected if not logged in)")
        
        # Test 5: Check reports endpoint
        print("\n5. Testing reports endpoint...")
        response = session.get(f"{BASE_URL}/llm-training/api/reports")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Reports endpoint works: {len(data.get('reports', []))} reports found")
        else:
            print(f"❌ Reports endpoint failed: {response.status_code}")
            if response.status_code == 401:
                print("   (This is expected if not logged in)")
        
        print("\n🎉 API endpoint connectivity test completed!")
        print("\nNote: 401 errors are expected when not logged in.")
        print("The important thing is that endpoints are reachable and return proper JSON responses.")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the server. Make sure the Flask app is running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_javascript_endpoints():
    """Check if JavaScript endpoints match backend routes"""
    
    print("\n🔍 Checking JavaScript-Backend endpoint alignment...")
    
    # Read the JavaScript file
    js_file = project_root / "webapp" / "static" / "js" / "llm-training.js"
    
    if not js_file.exists():
        print("❌ JavaScript file not found")
        return False
    
    with open(js_file, 'r') as f:
        js_content = f.read()
    
    # Expected endpoints from JavaScript
    expected_endpoints = [
        "/llm-training/api/training-guides/upload",
        "/llm-training/api/training-jobs",
        "/llm-training/api/test-submissions/upload",
        "/llm-training/api/reports",
        "/llm-training/api/training-guides",
        "/llm-training/api/test-submissions"
    ]
    
    print("Checking JavaScript endpoints:")
    for endpoint in expected_endpoints:
        if endpoint in js_content:
            print(f"✅ {endpoint}")
        else:
            print(f"❌ {endpoint} - NOT FOUND")
    
    return True

def main():
    """Main test function"""
    print("🚀 LLM Training Frontend-Backend Connection Test")
    print("=" * 50)
    
    # Check JavaScript endpoints
    check_javascript_endpoints()
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("✨ Test completed! Check the results above.")
    print("\nTo fully test the connection:")
    print("1. Make sure the Flask app is running: python run_app.py")
    print("2. Open http://127.0.0.1:5000/llm-training/ in your browser")
    print("3. Check the browser console for any JavaScript errors")
    print("4. Try uploading a training guide to test the full workflow")

if __name__ == "__main__":
    main()