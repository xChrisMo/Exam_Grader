#!/usr/bin/env python3
"""
Simple Exam Grader Application Runner
Minimal startup script for the Flask Exam Grader application.
"""

import os
import sys
import signal
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

# Set up UTF-8 encoding for Windows compatibility
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Set default environment variables
os.environ.setdefault("FLASK_APP", "webapp.exam_grader_app")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "8501")
os.environ.setdefault("DEBUG", "True")

def shutdown_handler(sig=None, frame=None):
    """Handle graceful shutdown of all services."""
    import threading
    import time
    
    def force_exit():
        """Force exit after timeout."""
        time.sleep(8)  # Give 8 seconds for graceful shutdown
        print("⏰ Shutdown timeout reached, forcing exit...")
        os._exit(1)
    
    # Start force exit timer
    force_exit_thread = threading.Thread(target=force_exit, daemon=True)
    force_exit_thread.start()
    
    try:
        print("\n🛑 Initiating graceful shutdown...")
        
        # Import cleanup functions
        try:
            from webapp.exam_grader_app import cleanup_services
            cleanup_services()
        except ImportError:
            print("⚠️  No cleanup services found")
        except Exception as e:
            print(f"⚠️  Error in cleanup services: {e}")
        
        # Close database connections
        try:
            from src.database import db
            from webapp.exam_grader_app import app
            try:
                with app.app_context():
                    db.session.close()
            except RuntimeError:
                # If app context not available, try direct cleanup
                try:
                    db.session.close()
                except:
                    pass
            print("✅ Database connections closed")
        except ImportError:
            print("⚠️  No database connections to close")
        except Exception as e:
            print(f"⚠️  Error closing database: {e}")
        
        # Stop background services
        try:
            from src.services.file_cleanup_service import stop_cleanup_service
            stop_cleanup_service()
            print("✅ Background services stopped")
        except ImportError:
            print("⚠️  No background services to stop")
        except Exception as e:
            print(f"⚠️  Error stopping background services: {e}")
        
        print("✅ Graceful shutdown completed")
        
        # Give a moment for cleanup to complete
        time.sleep(1)
        
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")
    finally:
        # Force exit the application
        print("👋 Exiting application...")
        os._exit(0)

def main():
    """Main entry point."""
    try:
        print("🚀 Starting Exam Grader...")
        
        # Set up signal handlers for graceful shutdown
        import signal
        signal.signal(signal.SIGINT, lambda sig, frame: shutdown_handler())
        signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_handler())
        
        # Import the Flask app
        from webapp.exam_grader_app import app
        
        # Get configuration from environment
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8501"))
        debug = os.getenv("DEBUG", "True").lower() == "true"
        
        print(f"📍 Server: http://{host}:{port}")
        print(f"🔧 Debug mode: {'ON' if debug else 'OFF'}")
        print("Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Run the application
        try:
            app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
                threaded=True
            )
        except KeyboardInterrupt:
            print("\n👋 Shutting down server...")
            shutdown_handler()
            raise
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"Try a different port: PORT=8502 python run_app.py")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error: {e}")
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()