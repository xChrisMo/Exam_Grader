#!/usr/bin/env python3
"""
Test script to verify the utils.guide_verification import works correctly.
"""

import sys
from pathlib import Path

# Add project root to Python path (same as in exam_grader_app.py)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print(f"Project root: {project_root}")
print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries

try:
    from utils import is_guide_in_use
    print("✅ SUCCESS: Successfully imported is_guide_in_use from utils")
    print(f"Function location: {is_guide_in_use.__module__}")
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
    
    # Try alternative import
    try:
        from utils.guide_verification import is_guide_in_use
        print("✅ SUCCESS: Direct import from utils.guide_verification works")
    except ImportError as e2:
        print(f"❌ DIRECT IMPORT ERROR: {e2}")
        
        # Check if files exist
        utils_init = project_root / "utils" / "__init__.py"
        guide_verification = project_root / "utils" / "guide_verification.py"
        
        print(f"\nFile existence check:")
        print(f"utils/__init__.py exists: {utils_init.exists()}")
        print(f"utils/guide_verification.py exists: {guide_verification.exists()}")
        
        if utils_init.exists():
            with open(utils_init, 'r') as f:
                content = f.read()
                print(f"\nutils/__init__.py content:")
                print(content)