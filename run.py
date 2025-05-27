#!/usr/bin/env python3
"""
Exam Grader - Application Runner

This script starts the Flask web application with proper configuration
for development or production environments.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point for running the application."""
    try:
        # Import the Flask app
        from app import ExamGraderApp

        # Create the application instance
        exam_grader = ExamGraderApp()

        # Get configuration from environment or use defaults
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

        print(f"Starting Exam Grader Web Application...")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Debug: {debug}")
        print(f"URL: http://{host}:{port}")
        print("-" * 50)

        # Run the application
        exam_grader.run(host=host, port=port, debug=debug)

    except ImportError as e:
        print(f"Error importing application: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
