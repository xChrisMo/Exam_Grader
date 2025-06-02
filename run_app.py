#!/usr/bin/env python3
"""
Exam Grader Application Runner
Comprehensive startup script for the Flask Exam Grader application.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_virtual_environment():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print(f"✅ Virtual environment: {sys.prefix}")
    else:
        print("⚠️  Warning: Not running in a virtual environment")
        print("   Consider using: python -m venv venv && source venv/bin/activate")

def install_requirements(requirements_file: str = "webapp/requirements.txt"):
    """Install required packages."""
    if not os.path.exists(requirements_file):
        print(f"❌ Requirements file not found: {requirements_file}")
        return False

    print(f"📦 Installing requirements from {requirements_file}...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'flask',
        'werkzeug',
        'jinja2'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        return False

    print("✅ All required dependencies are installed")
    return True

def setup_environment():
    """Set up environment variables and paths."""
    # Add project root to Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Set environment variables
    os.environ.setdefault('FLASK_APP', 'webapp.exam_grader_app')
    os.environ.setdefault('FLASK_ENV', 'development')

    print(f"✅ Project root: {project_root}")
    print(f"✅ FLASK_APP: {os.environ.get('FLASK_APP')}")

def create_directories():
    """Create necessary directories."""
    directories = [
        'temp',
        'output',
        'logs',
        'webapp/static/uploads'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    print("✅ Created necessary directories")

def run_application(host: str = None, port: int = None, debug: bool = None):
    """Run the Flask application with configuration from .env file."""
    try:
        # Load environment variables from .env
        load_dotenv('.env', override=True)

        # Use .env values if not provided as arguments
        if host is None:
            host = os.getenv('HOST', '127.0.0.1')
        if port is None:
            port = int(os.getenv('PORT', '8501'))
        if debug is None:
            debug = os.getenv('DEBUG', 'False').lower() == 'true'

        # Import the Flask app
        from webapp.exam_grader_app import app

        print("\n" + "="*50)
        print("🚀 Starting Exam Grader Web Application")
        print("="*50)
        print(f"📊 Dashboard: http://{host}:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"🌐 Host: {host}")
        print(f"🔌 Port: {port}")
        print(f"📁 Temp Dir: {os.getenv('TEMP_DIR', 'temp')}")
        print(f"📂 Output Dir: {os.getenv('OUTPUT_DIR', 'output')}")
        print(f"📊 Max File Size: {os.getenv('MAX_FILE_SIZE_MB', '20')}MB")
        print(f"🔑 API Keys: {'✅' if os.getenv('HANDWRITING_OCR_API_KEY') else '❌'}")
        print("="*50)
        print("Press Ctrl+C to stop the server")
        print("="*50)

        # Run the application with reloader disabled to prevent double initialization
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader to prevent double initialization
            threaded=True
        )

    except ImportError as e:
        print(f"❌ Failed to import Flask application: {e}")
        print("   Make sure all dependencies are installed")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"   Try a different port: python run_app.py --port {port + 1}")
        else:
            print(f"❌ Failed to start server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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
        """
    )

    # Load environment variables to get defaults
    load_dotenv('.env', override=True)

    parser.add_argument(
        '--host',
        default=os.getenv('HOST', '127.0.0.1'),
        help=f'Host to bind to (default: {os.getenv("HOST", "127.0.0.1")})'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('PORT', '8501')),
        help=f'Port to bind to (default: {os.getenv("PORT", "8501")})'
    )
    parser.add_argument(
        '--no-debug',
        action='store_true',
        help=f'Disable debug mode (default debug: {os.getenv("DEBUG", "False")})'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install requirements before running'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check setup and dependencies only'
    )

    args = parser.parse_args()

    print("🔍 Checking system requirements...")

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
        print("\n✅ Setup check complete. You can now run the application.")
        sys.exit(0)

    # Run the application
    run_application(host=args.host, port=args.port, debug=not args.no_debug)

if __name__ == "__main__":
    main()
