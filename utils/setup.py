"""
Utility module for system setup tasks.
This module handles initialization of resources needed by the application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import logger

def setup_system():
    """
    Perform all system setup tasks.

    This function:
    1. Loads environment variables
    2. Initializes required directories
    3. Sets up any required resources

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Load environment variables
        load_dotenv()

        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Ensure required directories exist
        required_dirs = [
            "temp",
            "temp/uploads",
            "output",
            "logs",
            "results",
            "data/nltk_data"
        ]

        for directory in required_dirs:
            dir_path = Path(os.path.join(project_root, directory))
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")

        # Initialize services if needed
        # This is now handled in src/services/__init__.py

        logger.info("System setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"System setup failed: {str(e)}")
        return False