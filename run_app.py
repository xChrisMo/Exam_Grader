#!/usr/bin/env python3
"""
Runner script for Exam Grader web application.
This script ensures the proper Python path is set up before running the app.
"""

import os
import sys
from pathlib import Path

def main():
    """
    Set up the Python path and run the web application.
    """
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root to the Python path
    sys.path.insert(0, project_root)
    
    # Create required directories if they don't exist
    required_dirs = ["temp", "temp/uploads", "output", "logs", "results", "data/nltk_data"]
    for directory in required_dirs:
        dir_path = Path(os.path.join(project_root, directory))
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")
    
    # Initialize system resources
    from utils.setup import setup_system
    setup_system()
    
    print("Starting Exam Grader web application...")
    
    # Import and run the Flask app
    from webapp.app import create_app
    
    app = create_app()
    
    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 8501)
    debug = app.config.get("DEBUG", True)
    
    print(f"Server starting at http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main() 