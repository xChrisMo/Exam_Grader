#!/usr/bin/env python3
"""
Setup Verification Script for Exam Grader Application
Run this script before starting the application to ensure everything is configured correctly.
"""

import os
import sys
from pathlib import Path

def main():
    print("Exam Grader Setup Verification")
    print("=" * 50)
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check if we're in the right directory
    expected_files = ['run_app.py', 'webapp/exam_grader_app.py', 'utils/__init__.py']
    missing_files = []
    
    for file_path in expected_files:
        if not (current_dir / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("\n❌ ERROR: You're not in the correct directory!")
        print(f"Missing files: {', '.join(missing_files)}")
        print("\nPlease navigate to the Exam_Grader project root directory.")
        print("The correct directory should contain:")
        for file_path in expected_files:
            print(f"  - {file_path}")
        return False
    
    print("\n✅ Directory check passed")
    
    # Test imports
    print("\nTesting imports...")
    
    # Add current directory to Python path
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    try:
        from utils import is_guide_in_use
        print("✅ Successfully imported is_guide_in_use")
    except Exception as e:
        print(f"❌ Failed to import is_guide_in_use: {e}")
        return False
    
    try:
        from utils import logger
        print("✅ Successfully imported logger")
    except Exception as e:
        print(f"⚠️  Warning: Could not import logger: {e}")
    
    # Check environment file
    env_files = ['.env', 'instance/.env']
    env_found = False
    for env_file in env_files:
        if (current_dir / env_file).exists():
            print(f"✅ Found environment file: {env_file}")
            env_found = True
            break
    
    if not env_found:
        print("⚠️  Warning: No .env file found. You may need to create one.")
    
    print("\n" + "=" * 50)
    print("✅ Setup verification completed successfully!")
    print("\nYou can now start the application using:")
    print("  python run_app.py")
    print("\nOr run the Flask app directly:")
    print("  python webapp/exam_grader_app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup verification failed. Please fix the issues above.")
        sys.exit(1)