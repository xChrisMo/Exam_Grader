"""
Utils package for common utilities.
"""

import sys
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.logger import Logger, logger, setup_logger
except ImportError as e:
    print(f"Warning: Could not import logger utilities: {e}")
    # Create dummy logger for fallback
    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    
    logger = DummyLogger()
    Logger = DummyLogger
    setup_logger = lambda: None

try:
    from utils.guide_verification import is_guide_in_use
except ImportError as e:
    print(f"Warning: Could not import guide_verification: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}...")
    
    # Create a fallback function
    def is_guide_in_use(guide_id):
        """Fallback function when guide_verification cannot be imported."""
        print(f"Warning: Using fallback is_guide_in_use function for guide {guide_id}")
        return False

__all__ = ["Logger", "logger", "setup_logger", "is_guide_in_use"]
