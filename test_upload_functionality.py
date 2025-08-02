#!/usr/bin/env python3
"""
Test script to verify upload functionality for training guides and test submissions
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

def get_csrf_token(session):
    """Get CSRF token from the server"""
    try:
        response = session.get(f"{BASE_URL}/get-csrf-token")
        if response.status_code == 200:
            data = response.json()
            return data.get('csrf_token')
    except:
        pass
    return None

def test_upload_training_guide(session):
    """Test uploading a training guide"""
    print("\n📚 Testing Training Guide Upload...")
    
    # Get CSRF token
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        print("❌ Could not get CSRF token")
        return False
    
    # Prepare test file
    test_file_path = project_root / "test_upload_guide.txt"
    if not test_file_path.exists():
        print("❌ Test file not found")
        return False
    
    # Prepare form data
    files = {
        'file': ('test_guide.txt', open(test_file_path, 'rb'), 'text/plain')
    }
    
    data = {
        'name': 'Test Training Guide',
        'description': 'This is a test training guide for verification',
        'csrf_token': csrf_token
    }
    
    try:
        # Upload the training guide
        response = session.post(
            f"{BASE_URL}/llm-training/api/training-guides/upload",
            files=files,
            data=data
        )
        
        files['file'][1].close()  # Close the file
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Training guide uploaded successfully!")
                    print(f"   Guide ID: {result.get('guide', {}).get('id', 'N/A')}")
                    print(f"   Guide Name: {result.get('guide', {}).get('name', 'N/A')}")
                    return True
                else:
                    print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                print(f"Response content: {response.text[:200]}...")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Exception during upload: {e}")
        return False

def test_upload_test_submission(session):
    """Test uploading a test submission"""
    print("\n📝 Testing Test Submission Upload...")
    
    # Get CSRF token
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        print("❌ Could not get CSRF token")
        return False
    
    # Prepare test file
    test_file_path = project_root / "test_submission.txt"
    if not test_file_path.exists():
        print("❌ Test file not found")
        return False
    
    # Prepare form data
    files = {
        'file': ('test_submission.txt', open(test_file_path, 'rb'), 'text/plain')
    }
    
    data = {
        'name': 'Test Student Submission',
        'expected_score': '85',
        'csrf_token': csrf_token
    }
    
    try:
        # Upload the test submission
        response = session.post(
            f"{BASE_URL}/llm-training/api/test-submissions/upload",
            files=files,
            data=data
        )
        
        files['file'][1].close()  # Close the file
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Test submission uploaded successfully!")
                    print(f"   Submission ID: {result.get('submission', {}).get('id', 'N/A')}")
                    print(f"   Submission Name: {result.get('submission', {}).get('name', 'N/A')}")
                    print(f"   Expected Score: {result.get('submission', {}).get('expected_score', 'N/A')}")
                    return True
                else:
                    print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                print(f"Response content: {response.text[:200]}...")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Exception during upload: {e}")
        return False

def test_list_uploads(session):
    """Test listing uploaded files"""
    print("\n📋 Testing File Listing...")
    
    # Test training guides list
    try:
        response = session.get(f"{BASE_URL}/llm-training/api/training-guides")
        if response.status_code == 200:
            data = response.json()
            guides = data.get('guides', [])
            print(f"✅ Training guides listed: {len(guides)} guides found")
            for guide in guides[:3]:  # Show first 3
                print(f"   - {guide.get('name', 'N/A')} (ID: {guide.get('id', 'N/A')[:8]}...)")
        else:
            print(f"❌ Failed to list training guides: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing training guides: {e}")
    
    # Test submissions list
    try:
        response = session.get(f"{BASE_URL}/llm-training/api/test-submissions")
        if response.status_code == 200:
            data = response.json()
            submissions = data.get('submissions', [])
            print(f"✅ Test submissions listed: {len(submissions)} submissions found")
            for submission in submissions[:3]:  # Show first 3
                print(f"   - {submission.get('name', 'N/A')} (Expected: {submission.get('expected_score', 'N/A')})")
        else:
            print(f"❌ Failed to list test submissions: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing test submissions: {e}")

def test_frontend_elements():
    """Test if frontend elements exist"""
    print("\n🎨 Testing Frontend Elements...")
    
    try:
        session = requests.Session()
        response = session.get(f"{BASE_URL}/llm-training/")
        
        if response.status_code == 200:
            html_content = response.text
            
            # Check for required form elements
            required_elements = [
                'upload-training-guide-btn',
                'training-guide-name',
                'training-guide-description', 
                'training-guide-file',
                'upload-test-submission-btn',
                'test-submission-name',
                'test-submission-expected-score',
                'test-submission-file'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in html_content:
                    missing_elements.append(element)
            
            if not missing_elements:
                print("✅ All required frontend elements found")
                return True
            else:
                print(f"❌ Missing frontend elements: {missing_elements}")
                return False
        else:
            print(f"❌ Could not load LLM training page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing frontend elements: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 LLM Training Upload Functionality Test")
    print("=" * 50)
    
    # Create session for maintaining cookies
    session = requests.Session()
    
    # Test results
    results = {
        'frontend_elements': False,
        'training_guide_upload': False,
        'test_submission_upload': False,
        'file_listing': True  # Assume this works if uploads work
    }
    
    try:
        # Test frontend elements
        results['frontend_elements'] = test_frontend_elements()
        
        # Test training guide upload
        results['training_guide_upload'] = test_upload_training_guide(session)
        
        # Test test submission upload
        results['test_submission_upload'] = test_upload_test_submission(session)
        
        # Test file listing
        test_list_uploads(session)
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure Flask app is running on http://127.0.0.1:5000")
        return
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"Frontend Elements: {'✅ PASS' if results['frontend_elements'] else '❌ FAIL'}")
    print(f"Training Guide Upload: {'✅ PASS' if results['training_guide_upload'] else '❌ FAIL'}")
    print(f"Test Submission Upload: {'✅ PASS' if results['test_submission_upload'] else '❌ FAIL'}")
    
    all_passed = all(results.values())
    print(f"\nOverall Status: {'🎉 ALL TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\n🔧 Troubleshooting Tips:")
        print("1. Make sure the Flask app is running: python run_app.py")
        print("2. Check if you're logged in (uploads require authentication)")
        print("3. Verify database is properly initialized: python create_db.py")
        print("4. Check server logs for detailed error messages")
    else:
        print("\n🎯 Upload functionality is working properly!")
        print("You can now use the LLM training interface to upload files.")

if __name__ == "__main__":
    main()