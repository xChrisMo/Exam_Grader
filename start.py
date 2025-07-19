#!/usr/bin/env python3
"""
Exam Grader Application Starter
Clean, simple startup script with proper error handling and shutdown.
"""

import os
import sys
import signal
from pathlib import Path
from dotenv import load_dotenv

def setup_signal_handler():
    """Setup signal handler for clean shutdown."""
    def signal_handler(sig, frame):
        print("\n[STOP] Shutting down server...")
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

def setup_environment():
    """Setup environment and paths."""
    # Load environment variables
    load_dotenv()
    
    # Add project root to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Set Flask environment
    os.environ.setdefault("FLASK_APP", "webapp.exam_grader_app")
    os.environ.setdefault("FLASK_ENV", "development")

def main():
    """Main application entry point."""
    print("🚀 Starting Exam Grader...")
    
    # Setup
    setup_signal_handler()
    setup_environment()
    
    # Get configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8501"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"🌐 Server: http://{host}:{port}")
    print(f"🔧 Debug: {'ON' if debug else 'OFF'}")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Import and run application
        from webapp.exam_grader_app import app
        from src.services.realtime_service import socketio
        
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"Try a different port: PORT={port + 1} python start.py")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()