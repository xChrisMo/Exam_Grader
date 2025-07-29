"""
Clean Main Application File

This is the new, streamlined main application file that replaces the
monolithic exam_grader_app.py with a clean, maintainable structure.
"""

import os
import sys
import signal
import atexit
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from webapp.app_factory import create_app, create_database_tables, cleanup_services
from utils.logger import logger

def setup_signal_handlers(app):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        cleanup_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main application entry point."""
    try:
        # Create Flask application
        app = create_app()
        
        # Create database tables
        create_database_tables(app)
        
        # Set up signal handlers
        setup_signal_handlers(app)
        
        # Register cleanup function
        atexit.register(cleanup_services)
        
        logger.info("Application started successfully")
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

# Create application instance
app = main()

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '8501'))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,
        threaded=True
    )