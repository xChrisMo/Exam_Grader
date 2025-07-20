#!/usr/bin/env python3
"""
Test script to verify fixes for the Exam Grader application.
"""

import os
import sys
import requests
from pathlib import Path

def test_csrf_token():
    """Test CSRF token generation and validation."""
    print("Testing CSRF token...")
    try:
        # Make a request to get a CSRF token
        response = requests.get("http://localhost:5000/get-csrf-token")
        if response.status_code == 200:
            data = response.json()
            if "csrf_token" in data:
                print("✅ CSRF token generation works")
                return True
            else:
                print("❌ CSRF token not found in response")
                return False
        else:
            print(f"❌ Failed to get CSRF token: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing CSRF token: {str(e)}")
        return False

def test_file_upload():
    """Test file upload with CSRF token."""
    print("Testing file upload...")
    try:
        # Get CSRF token
        response = requests.get("http://localhost:5000/get-csrf-token")
        if response.status_code != 200:
            print(f"❌ Failed to get CSRF token: {response.status_code}")
            return False
        
        csrf_token = response.json().get("csrf_token")
        if not csrf_token:
            print("❌ CSRF token not found in response")
            return False
        
        # Create a test file
        test_file_path = Path("test_upload.txt")
        with open(test_file_path, "w") as f:
            f.write("Test file for upload")
        
        # Upload the file
        with open(test_file_path, "rb") as f:
            files = {"file": f}
            data = {"csrf_token": csrf_token}
            response = requests.post(
                "http://localhost:5000/upload-guide",
                files=files,
                data=data,
                cookies={"secure_csrf_token": csrf_token}
            )
        
        # Clean up
        if test_file_path.exists():
            test_file_path.unlink()
        
        if response.status_code == 200:
            print("✅ File upload works")
            return True
        else:
            print(f"❌ Failed to upload file: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing file upload: {str(e)}")
        return False

def test_settings():
    """Test settings page."""
    print("Testing settings page...")
    try:
        response = requests.get("http://localhost:5000/settings")
        if response.status_code == 200:
            print("✅ Settings page loads successfully")
            return True
        else:
            print(f"❌ Failed to load settings page: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing settings page: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("Running tests for Exam Grader application...")
    
    # Check if the application is running
    try:
        response = requests.get("http://localhost:5000/health")
        if response.status_code != 200:
            print("❌ Application is not running or health check failed")
            return False
    except Exception:
        print("❌ Application is not running")
        return False
    
    # Run tests
    csrf_test = test_csrf_token()
    settings_test = test_settings()
    upload_test = test_file_upload()
    
    # Print summary
    print("\nTest Summary:")
    print(f"CSRF Token: {'✅ PASS' if csrf_test else '❌ FAIL'}")
    print(f"Settings Page: {'✅ PASS' if settings_test else '❌ FAIL'}")
    print(f"File Upload: {'✅ PASS' if upload_test else '❌ FAIL'}")
    
    return all([csrf_test, settings_test, upload_test])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)