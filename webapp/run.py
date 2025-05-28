#!/usr/bin/env python3
"""
Run script for Exam Grader Flask Web Application
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import from src/
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import the Flask app
from exam_grader_app import app

if __name__ == '__main__':
    # Set environment variables for development
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')
    
    print("🚀 Starting Exam Grader Web Application...")
    print("📊 Dashboard: http://127.0.0.1:5000")
    print("🔧 Debug mode: ON")
    print("📁 Static files: /static/")
    print("📄 Templates: /templates/")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)
