#!/usr/bin/env python3
"""
Exam Grader Web Application Launcher

This script launches the Flask web application for the Exam Grader.
It provides a convenient way to start the web interface with proper
configuration and error handling.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import ExamGraderApp
from utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Exam Grader Web Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_web.py                    # Run with default settings
  python run_web.py --host 0.0.0.0    # Run on all interfaces
  python run_web.py --port 8080       # Run on port 8080
  python run_web.py --debug           # Run in debug mode
  python run_web.py --production       # Run in production mode
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        help='Host to bind to (default: from config)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Port to bind to (default: from config)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )
    
    parser.add_argument(
        '--production',
        action='store_true',
        help='Run in production mode (disables debug)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker processes (for production)'
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import flask
        import flask_socketio
        import flask_session
        import flask_cors
        logger.info("All web dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install web dependencies with: pip install -r requirements.txt")
        return False


def setup_environment():
    """Setup environment variables and directories."""
    # Ensure required directories exist
    directories = ['temp', 'logs', 'output', 'results']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Set default environment variables if not set
    env_defaults = {
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': '1',
        'SECRET_KEY': 'dev-secret-key-change-in-production'
    }
    
    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value


def run_development_server(app, host=None, port=None, debug=None):
    """Run the development server."""
    logger.info("Starting Exam Grader web application in development mode")
    logger.info(f"Access the application at: http://{host or app.config_manager.config.host}:{port or app.config_manager.config.port}")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


def run_production_server(app, host=None, port=None, workers=1):
    """Run the production server using Gunicorn."""
    try:
        import gunicorn.app.wsgiapp as wsgi
        
        # Prepare Gunicorn arguments
        host = host or app.config_manager.config.host
        port = port or app.config_manager.config.port
        
        sys.argv = [
            'gunicorn',
            '--bind', f'{host}:{port}',
            '--workers', str(workers),
            '--worker-class', 'eventlet',
            '--timeout', '120',
            '--keepalive', '5',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--access-logfile', 'logs/access.log',
            '--error-logfile', 'logs/error.log',
            '--log-level', 'info',
            'app:create_app()'
        ]
        
        logger.info(f"Starting Exam Grader web application in production mode")
        logger.info(f"Server: http://{host}:{port}")
        logger.info(f"Workers: {workers}")
        
        wsgi.run()
        
    except ImportError:
        logger.error("Gunicorn not available. Install with: pip install gunicorn")
        logger.info("Falling back to development server...")
        run_development_server(app, host, port, debug=False)
    except Exception as e:
        logger.error(f"Production server error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    try:
        # Create application instance
        logger.info("Initializing Exam Grader web application...")
        app = ExamGraderApp()
        
        # Determine debug mode
        debug = None
        if args.debug:
            debug = True
        elif args.production:
            debug = False
        
        # Run appropriate server
        if args.production:
            run_production_server(
                app, 
                host=args.host, 
                port=args.port, 
                workers=args.workers
            )
        else:
            run_development_server(
                app, 
                host=args.host, 
                port=args.port, 
                debug=debug
            )
            
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
