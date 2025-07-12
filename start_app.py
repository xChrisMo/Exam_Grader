#!/usr/bin/env python3
"""
Robust Application Starter for Exam Grader
This script ensures clean imports and correct path setup.
"""

import os
import sys
from pathlib import Path

def clear_cached_imports():
    """Clear any cached imports that might cause conflicts."""
    modules_to_clear = []
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('utils') or module_name.startswith('src'):
            modules_to_clear.append(module_name)
    
    for module_name in modules_to_clear:
        del sys.modules[module_name]
        print(f"Cleared cached module: {module_name}")

def setup_environment():
    """Set up the environment for the application."""
    # Get the directory containing this script
    project_root = Path(__file__).parent.absolute()
    
    print(f"Project root: {project_root}")
    print(f"Current working directory: {Path.cwd()}")
    
    # Clear any existing PYTHONPATH that might interfere
    if 'PYTHONPATH' in os.environ:
        old_pythonpath = os.environ['PYTHONPATH']
        print(f"Clearing existing PYTHONPATH: {old_pythonpath}")
        del os.environ['PYTHONPATH']
    
    # Clear sys.path of any conflicting entries
    paths_to_remove = []
    for path in sys.path:
        if 'projects' in path and 'Exam_Grader' in path:
            paths_to_remove.append(path)
    
    for path in paths_to_remove:
        sys.path.remove(path)
        print(f"Removed conflicting path: {path}")
    
    # Add the correct project root to the beginning of sys.path
    if str(project_root) in sys.path:
        sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))
    
    print(f"Added to sys.path: {project_root}")
    print(f"First 3 sys.path entries: {sys.path[:3]}")
    
    return project_root

def test_imports():
    """Test critical imports before starting the application."""
    print("\nTesting imports...")
    
    try:
        from utils import is_guide_in_use
        print("✅ Successfully imported is_guide_in_use")
        print(f"Function module: {is_guide_in_use.__module__}")
    except ImportError as e:
        print(f"❌ Failed to import is_guide_in_use: {e}")
        return False
    
    try:
        from utils import logger
        print("✅ Successfully imported logger")
    except ImportError as e:
        print(f"⚠️  Warning: Could not import logger: {e}")
    
    return True

def start_application():
    """Start the Flask application."""
    print("\nStarting Exam Grader application...")
    print("=" * 50)
    
    try:
        # Import and run the application
        from webapp.exam_grader_app import app
        
        # Get configuration
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "5000"))
        debug = os.getenv("DEBUG", "True").lower() == "true"
        
        print(f"Starting server on {host}:{port}")
        print(f"Debug mode: {debug}")
        print("\nPress Ctrl+C to stop the server")
        
        app.run(host=host, port=port, debug=debug)
        
    except ImportError as e:
        print(f"❌ Failed to import Flask application: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False
    
    return True

def main():
    """Main function."""
    print("Exam Grader Application Starter")
    print("=" * 40)
    
    # Clear any cached imports
    clear_cached_imports()
    
    # Set up environment
    project_root = setup_environment()
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed. Cannot start application.")
        return False
    
    # Start the application
    return start_application()

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)