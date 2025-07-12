#!/usr/bin/env python3
"""
Import Fix Script for Exam Grader Application
This script ensures all imports work correctly regardless of the directory structure.
"""

import os
import sys
from pathlib import Path

def fix_python_path():
    """Add the correct project root to Python path."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Add to Python path if not already there
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
        print(f"Added to Python path: {script_dir}")
    
    return script_dir

def verify_imports():
    """Verify that all critical imports work."""
    try:
        from utils import is_guide_in_use
        print("✅ SUCCESS: is_guide_in_use imported successfully")
        return True
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        return False

def check_file_structure():
    """Check if required files exist."""
    project_root = Path(__file__).parent
    required_files = [
        "utils/__init__.py",
        "utils/guide_verification.py",
        "webapp/exam_grader_app.py",
        "src/config/unified_config.py"
    ]
    
    print("\nChecking file structure:")
    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}: {'EXISTS' if exists else 'MISSING'}")
        if not exists:
            all_exist = False
    
    return all_exist

def main():
    """Main function to fix imports and verify setup."""
    print("Exam Grader Import Fix Script")
    print("=" * 40)
    
    # Fix Python path
    project_root = fix_python_path()
    print(f"Project root: {project_root}")
    
    # Check file structure
    files_ok = check_file_structure()
    
    # Verify imports
    imports_ok = verify_imports()
    
    print("\nSummary:")
    print(f"Files structure: {'✅ OK' if files_ok else '❌ ISSUES'}")
    print(f"Imports: {'✅ OK' if imports_ok else '❌ ISSUES'}")
    
    if files_ok and imports_ok:
        print("\n🎉 All checks passed! You can now run the application.")
        print("\nTo start the application, run:")
        print("  python run_app.py")
        print("  or")
        print("  python webapp/exam_grader_app.py")
    else:
        print("\n⚠️  Issues detected. Please check the file structure and imports.")
        
        if not files_ok:
            print("\nMissing files detected. Make sure you're in the correct directory.")
            print("Expected directory structure:")
            print("  Exam_Grader/")
            print("  ├── utils/")
            print("  │   ├── __init__.py")
            print("  │   └── guide_verification.py")
            print("  ├── src/")
            print("  ├── webapp/")
            print("  └── run_app.py")

if __name__ == "__main__":
    main()