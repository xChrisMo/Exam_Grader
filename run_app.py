#!/usr/bin/env python3
"""
Simple Exam Grader Application Runner
Minimal startup script for the Flask Exam Grader application.
"""

import os
import sys
import time
from pathlib import Path
import signal
import threading

from dotenv import load_dotenv

# Add project root to Python path using centralized utility
from utils.project_init import init_project
project_root = init_project(__file__)

from src.constants import (
    DEFAULT_DEBUG,
    DEFAULT_FLASK_APP,
    DEFAULT_FLASK_ENV,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_ENCODING,
    ENV_DEBUG,
    ENV_FLASK_APP,
    ENV_FLASK_ENV,
    ENV_HOST,
    ENV_PORT,
    ENV_PYTHONIOENCODING,
    UI_DEBUG_OFF,
    UI_DEBUG_ON,
    UI_PRESS_CTRL_C,
    UI_SHUTDOWN_MESSAGE,
    UI_STARTUP_MESSAGE,
)

# Set up UTF-8 encoding for Windows compatibility
os.environ[ENV_PYTHONIOENCODING] = DEFAULT_ENCODING

# Load environment variables
load_dotenv()

# Set default environment variables
os.environ.setdefault(ENV_FLASK_APP, DEFAULT_FLASK_APP)
os.environ.setdefault(ENV_FLASK_ENV, DEFAULT_FLASK_ENV)
os.environ.setdefault(ENV_HOST, DEFAULT_HOST)
os.environ.setdefault(ENV_PORT, DEFAULT_PORT)
os.environ.setdefault(ENV_DEBUG, DEFAULT_DEBUG)

def shutdown_handler(sig=None, frame=None):
    """Handle graceful shutdown of all services."""

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
            from webapp.app_factory import cleanup_services
            cleanup_services()
        except ImportError:
            print("⚠️  No cleanup services found")
        except Exception as e:
            print(f"⚠️  Error in cleanup services: {e}")

        # Close database connections
        try:
            from src.database import db
            from webapp.app import app
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
        print(UI_STARTUP_MESSAGE)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, lambda sig, frame: shutdown_handler())
        signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_handler())

        # Import the Flask app (new clean architecture)
        from webapp.app import app

        # Get configuration from environment
        host = os.getenv(ENV_HOST, DEFAULT_HOST)
        port = int(os.getenv(ENV_PORT, DEFAULT_PORT))
        debug = os.getenv(ENV_DEBUG, DEFAULT_DEBUG).lower() == "true"

        # For production deployment (Render, Heroku, etc.)
        if os.getenv('RENDER') or os.getenv('DYNO'):
            host = '0.0.0.0'
            port = int(os.getenv('PORT', port))
            debug = False

        print(f"📍 Server: http://{host}:{port}")
        print(f"🔧 Debug mode: {UI_DEBUG_ON if debug else UI_DEBUG_OFF}")
        print(UI_PRESS_CTRL_C)
        print("=" * 50)

        # Run the application
        try:
            # For production or when USE_WAITRESS env var is set, use Waitress (Windows compatible)
            if not debug or os.getenv('USE_WAITRESS', '').lower() == 'true':
                print("🚀 Starting with Waitress for better timeout handling...")
                try:
                    from waitress import serve
                    print(f"📍 Waitress server starting on http://{host}:{port}")
                    print("⏱️  Extended timeouts enabled for AI processing")
                    print("🔧 Optimized for Windows compatibility")

                    # Serve with Waitress - Windows compatible with optimized settings
                    serve(
                        app,
                        host=host,
                        port=port,
                        threads=8,  # Increased threads for better concurrency
                        connection_limit=200,  # Increased connection limit
                        cleanup_interval=10,  # More frequent cleanup
                        channel_timeout=300,  # 5 minutes (reduced from 10)
                        log_socket_errors=False,  # Reduce log noise
                        max_request_body_size=104857600,  # 100MB
                        recv_bytes=8192,  # Increased buffer size
                        send_bytes=18000,  # Increased send buffer
                        outbuf_overflow=1048576,  # 1MB overflow buffer
                        inbuf_overflow=524288,  # 512KB input overflow
                    )
                except ImportError:
                    print("⚠️  Waitress not available, falling back to Flask dev server")
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
            else:
                # Development server with extended timeout
                print("🔧 Starting Flask development server...")
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
