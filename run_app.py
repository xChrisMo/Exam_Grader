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

def run_application(host: str = '127.0.0.1', port: int = 5000, debug: bool = True):
    """Run the Flask application."""
    try:
        # Import the Flask app
        from webapp.exam_grader_app import app
        
        print("\n" + "="*50)
        print("🚀 Starting Exam Grader Web Application")
        print("="*50)
        print(f"📊 Dashboard: http://{host}:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"🌐 Host: {host}")
        print(f"🔌 Port: {port}")
        print("="*50)
        print("Press Ctrl+C to stop the server")
        print("="*50)
        
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
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
    
    parser.add_argument(
        '--host', 
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--no-debug', 
        action='store_true',
        help='Disable debug mode'
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
    
    # Create directories
    create_directories()
    
    # Install requirements if requested
    if args.install:
        if not install_requirements():
            sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Try running: python run_app.py --install")
        sys.exit(1)
    
    # If only checking, exit here
    if args.check:
        print("\n✅ All checks passed! Ready to run the application.")
        return
    
    # Run the application
    debug_mode = not args.no_debug
    run_application(args.host, args.port, debug_mode)

if __name__ == '__main__':
    main()
