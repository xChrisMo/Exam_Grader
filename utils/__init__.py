"""
Utils package for common utilities.
"""

import logging
import sys
from pathlib import Path

# Set up basic logging first
logging.basicConfig(level=logging.INFO)

# Ensure the project root is in the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can safely import project modules
try:
    from utils.project_init import ensure_project_imports
    ensure_project_imports()
except ImportError as e:
    logging.warning(f"Could not import project_init: {e}")

try:
    from utils.logger import Logger, logger, setup_logger
except ImportError as e:
    logging.warning(f"Could not import logger utilities: {e}")

    class DummyLogger:
        def info(self, msg):
            logging.info(msg)

        def warning(self, msg):
            logging.warning(msg)

        def error(self, msg):
            logging.error(msg)

    logger = DummyLogger()
    Logger = DummyLogger
    setup_logger = lambda: None

try:
    from utils.guide_verification import is_guide_in_use
except ImportError as e:
    logging.warning(f"Could not import guide_verification: {e}")
    logging.debug(f"Current working directory: {Path.cwd()}")
    logging.debug(f"Project root: {project_root}")
    logging.debug(f"Python path: {sys.path[:3]}...")

    # Create a fallback function
    def is_guide_in_use(guide_id):
        """Fallback function when guide_verification cannot be imported."""
        logging.warning(f"Using fallback is_guide_in_use function for guide {guide_id}")
        return False

__all__ = ["Logger", "logger", "setup_logger", "is_guide_in_use"]
