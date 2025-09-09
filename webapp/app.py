"""
Clean Main Application File

This is the new, streamlined main application file that replaces the
monolithic exam_grader_app.py with a clean, maintainable structure.
"""

import os
import sys
from pathlib import Path
import atexit
import signal

from utils.project_init import init_project
project_root = init_project(__file__, levels_up=2)

from src.constants import (
    DEFAULT_DEBUG,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENV_DEBUG,
    ENV_HOST,
    ENV_PORT,
    SUCCESS_INITIALIZED,
)
from utils.logger import logger
from webapp.app_factory import cleanup_services, create_app, create_database_tables

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

        logger.info(SUCCESS_INITIALIZED)

        return app

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

# Create application instance
app = main()

if __name__ == "__main__":
    host = os.getenv(ENV_HOST, DEFAULT_HOST)
    port = int(os.getenv(ENV_PORT, DEFAULT_PORT))
    debug = os.getenv(ENV_DEBUG, DEFAULT_DEBUG).lower() == "true"

    logger.info(f"Starting server on {host}:{port} (debug={debug})")

    app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)
