#!/usr/bin/env python3
"""
Exam Grader Application Runner
Comprehensive startup script for the Flask Exam Grader application.
"""

import argparse
import os
import subprocess
import sys
import signal
from pathlib import Path
from flask import Flask
import codecs
try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from dotenv import load_dotenv
from src.utils import logging_config


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n[STOP] Application stopped by user (Ctrl+C)")
    print("[INFO] Shutting down gracefully...")
    # Force exit to ensure the application terminates
    os._exit(0)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("[ERROR] Error: Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"[OK] Python version: {sys.version.split()[0]}")


def check_virtual_environment():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print(f"[OK] Virtual environment: {sys.prefix}")
    else:
        print("[WARNING]  Warning: Not running in a virtual environment")
        print("   Consider using: python -m venv venv && source venv/bin/activate")


def install_requirements(requirements_file: str = "webapp/requirements.txt"):
    """Install required packages."""
    if not os.path.exists(requirements_file):
        print(f"[ERROR] Requirements file not found: {requirements_file}")
        return False

    print(f"[PACKAGE] Installing requirements from {requirements_file}...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        )
        print("[OK] Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install requirements: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ["flask", "werkzeug", "jinja2"]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"[ERROR] Missing required packages: {', '.join(missing_packages)}")
        return False

    print("[OK] All required dependencies are installed")
    return True


def check_version_compatibility():
    """Check for version compatibility between key packages."""
    try:
        import flask
        import flask_babel
        import werkzeug
        
        # Use importlib.metadata for version checking
        try:
            flask_version = version('flask')
            print(f"[INFO] Flask version: {flask_version}")
        except Exception:
            flask_version = getattr(flask, '__version__', 'unknown')
            print(f"[INFO] Flask version: {flask_version}")
        
        # Handle Flask-Babel version check
        try:
            babel_version = version('flask-babel')
            print(f"[INFO] Flask-Babel version: {babel_version}")
        except Exception:
            babel_version = getattr(flask_babel, '__version__', 'unknown')
            print(f"[INFO] Flask-Babel version: {babel_version}")
            
        # Handle Werkzeug version check
        try:
            werkzeug_version = version('werkzeug')
            print(f"[INFO] Werkzeug version: {werkzeug_version}")
        except Exception:
            werkzeug_version = getattr(werkzeug, '__version__', 'unknown')
            print(f"[INFO] Werkzeug version: {werkzeug_version}")
        
        # Check Flask and Flask-Babel compatibility
        if flask_version != 'unknown':
            flask_major, flask_minor = map(int, flask_version.split('.')[:2])
        else:
            flask_major, flask_minor = 2, 3  # Default assumption
        
        # Flask 3.x changed how extensions register functions
        if flask_major >= 3:
            print("[WARNING] Flask 3.x detected. Make sure Flask-Babel initialization uses the new API.")
            print("          Check webapp/exam_grader_app.py for proper initialization.")
        elif flask_major == 2 and flask_minor >= 3:
            # Current compatible setup
            print("[OK] Flask 2.3.x detected - compatible with current Flask-Babel setup")
        
        return True
    except (ImportError, AttributeError) as e:
        print(f"[ERROR] Version compatibility check failed: {e}")
        return False


def setup_environment():
    """Set up environment variables and paths."""
    # Add project root to Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Set environment variables
    os.environ.setdefault("FLASK_APP", "webapp.exam_grader_app")
    os.environ.setdefault("FLASK_ENV", "development")
    if os.environ.get("FLASK_ENV") == "development":
        os.environ["LOG_LEVEL"] = "DEBUG"

    print(f"[OK] Project root: {project_root}")
    print(f"[OK] FLASK_APP: {os.environ.get('FLASK_APP')}")
    print(f"[DEBUG] LOG_LEVEL environment variable: {os.getenv('LOG_LEVEL')}")


def create_directories():
    """Create necessary directories."""
    directories = ["temp", "output", "logs", "webapp/static/uploads"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    print("[OK] Created necessary directories")


def run_application(host: str = None, port: int = None, debug: bool = None):
    """Run the Flask application with configuration from .env file."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Load environment variables from instance/.env first, then fallback to root .env
        project_root = Path(__file__).parent
        instance_env_path = project_root / "instance" / ".env"

        if instance_env_path.exists():
            load_dotenv(instance_env_path, override=True)
            print(f"[OK] Loaded environment from: {instance_env_path}")
        else:
            load_dotenv(".env", override=True)
            print("[WARNING]  Loaded environment from root .env file")
            
        # Check version compatibility between Flask and Flask-Babel
        print("\n📦 Checking package version compatibility...")
        check_version_compatibility()
        print("")

        # Use .env values if not provided as arguments
        if host is None:
            host = os.getenv("HOST", "127.0.0.1")
        if port is None:
            port = int(os.getenv("PORT", "8501"))
        if debug is None:
            debug = os.getenv("DEBUG", "False").lower() == "true"

        # Suppress verbose logging during startup
        import logging
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

        # Set environment variable to suppress verbose startup messages
        os.environ['SUPPRESS_STARTUP_LOGS'] = 'true'

        print("\n🚀 Initializing Exam Grader...")

        # Import the Flask app (this will trigger initialization)
        from webapp.exam_grader_app import app
        from src.database.migrations import MigrationManager
        from src.config.unified_config import UnifiedConfig

        # Initialize and run database migrations
        config = UnifiedConfig()
        db_url = config.database.database_url
        print(f"[DEBUG] Database URL: {db_url}")
        print(f"[DEBUG] Database URL type: {type(db_url)}")
        
        if db_url:
            # Ensure app context is available for database operations
            from src.database.models import db  # Add proper DB import
            
            with app.app_context():
                try:
                    # Check if db engine is available
                    if hasattr(db, 'engine') and db.engine is not None:
                        print(f"[DEBUG] Using db.engine.url: {db.engine.url}")
                        MigrationManager(str(db.engine.url)).migrate()
                    else:
                        # Use the database URL directly if engine is not available
                        print(f"[DEBUG] Using config database URL: {db_url}")
                        MigrationManager(str(db_url)).migrate()
                except Exception as e:
                    print(f"[ERROR] Migration failed: {e}")
                    print(f"[DEBUG] Exception type: {type(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print("[ERROR] Database URL not found in configuration. Exiting.")
            sys.exit(1)

        print("\n" + "=" * 50)
        print("🎓 EXAM GRADER - AI-POWERED ASSESSMENT PLATFORM")
        print("=" * 50)
        # Initialize logging_config after UnifiedConfig is available
        # This ensures log_dir and log_level can be read from config
        from src.utils.logging_config import setup_application_logging
        app_logging_config = setup_application_logging()

        # Handle case where logging config might be None
        if app_logging_config and hasattr(app_logging_config, 'create_startup_summary'):
            print(app_logging_config.create_startup_summary(host=host, port=port))
        else:
            print(f"🚀 Server starting on {host}:{port}")
            print(f"📝 Logging: Basic configuration active")
        print(f"🔧 Debug mode: {'ON' if debug else 'OFF'}")
        print("📁 Storage: temp/ & output/")
        print(f"📊 Max file size: {os.getenv('MAX_FILE_SIZE_MB', '20')}MB")

        # Check API keys status
        ocr_key = os.getenv('HANDWRITING_OCR_API_KEY')
        llm_key = os.getenv('DEEPSEEK_API_KEY')
        api_status = "✅ READY" if (ocr_key and llm_key) else "⚠️  LIMITED"
        print(f"🔑 API Services: {api_status}")

        print("=" * 50)
        print("Press Ctrl+C to stop the server")
        print("=" * 50)

        # Run the application with reloader disabled to prevent double initialization
        os.environ['LOG_LEVEL'] = 'DEBUG'
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader to prevent double initialization
        )

    except ImportError as e:
        print(f"[ERROR] Failed to import Flask application: {e}")
        print("   Make sure all dependencies are installed")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"[ERROR] Port {port} is already in use")
            print(f"   Try a different port: python run_app.py --port {port + 1}")
        else:
            print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[STOP] Application stopped by user")
        print("[INFO] Shutting down gracefully...")
        os._exit(0)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Exam Grader Flask Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_app.py                    # Run with default settings
  python run_app.py --port 8080        # Run on port 8080
  python run_app.py --host 0.0.0.0     # Run on all interfaces
  python run_app.py --no-debug         # Run without debug mode
  python run_app.py --install          # Install requirements first
  python run_app.py --check            # Check setup only
        """,
    )

    # Load environment variables to get defaults from instance folder
    project_root = Path(__file__).parent
    instance_env_path = project_root / "instance" / ".env"

    if instance_env_path.exists():
        load_dotenv(instance_env_path, override=True)
    else:
        load_dotenv(".env", override=True)

    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
        help=f'Host to bind to (default: {os.getenv("HOST", "127.0.0.1")})',
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8501")),
        help=f'Port to bind to (default: {os.getenv("PORT", "8501")})',
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help=f'Disable debug mode (default debug: {os.getenv("DEBUG", "False")})',
    )
    parser.add_argument(
        "--install", action="store_true", help="Install requirements before running"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check setup and dependencies only"
    )

    args = parser.parse_args()

    print("Checking system requirements...")

    # Check Python version
    check_python_version()

    # Check virtual environment
    check_virtual_environment()

    # Set up environment
    setup_environment()

    if args.install:
        if not install_requirements():
            sys.exit(1)

    if args.check:
        if not check_dependencies():
            sys.exit(1)
        print("\nSetup check complete. You can now run the application.")
        sys.exit(0)

    # Run the application
    run_application(host=args.host, port=args.port, debug=not args.no_debug)


if __name__ == "__main__":
    main()
