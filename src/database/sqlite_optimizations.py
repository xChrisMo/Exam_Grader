"""
SQLite Database Optimizations for Exam Grader Application.

This module provides SQLite-specific optimizations to reduce database locking
and improve concurrent access performance.
"""

from pathlib import Path
import logging
import sqlite3

logger = logging.getLogger(__name__)

class SQLiteOptimizer:
    """Handles SQLite database optimizations and WAL mode setup."""

    @staticmethod
    def enable_wal_mode(database_path: str) -> bool:
        """
        Enable WAL (Write-Ahead Logging) mode for SQLite database.

        WAL mode allows multiple readers to access the database while one writer
        is active, significantly reducing database locking issues.

        Args:
            database_path: Path to the SQLite database file

        Returns:
            True if WAL mode was successfully enabled, False otherwise
        """
        try:
            # Convert to absolute path
            db_path = Path(database_path).resolve()

            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            conn = sqlite3.connect(str(db_path), timeout=30)
            cursor = conn.cursor()

            # Check current journal mode
            cursor.execute("PRAGMA journal_mode;")
            current_mode = cursor.fetchone()[0]
            logger.info(f"Current journal mode: {current_mode}")

            if current_mode.upper() != "WAL":
                # Enable WAL mode
                cursor.execute("PRAGMA journal_mode=WAL;")
                new_mode = cursor.fetchone()[0]
                logger.info(f"Changed journal mode to: {new_mode}")

                if new_mode.upper() == "WAL":
                    logger.info("Successfully enabled WAL mode")
                else:
                    logger.warning(
                        f"Failed to enable WAL mode, current mode: {new_mode}"
                    )
                    return False
            else:
                logger.info("WAL mode already enabled")

            # Apply additional optimizations
            SQLiteOptimizer._apply_performance_optimizations(cursor)

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Failed to enable WAL mode: {str(e)}")
            return False

    @staticmethod
    def _apply_performance_optimizations(cursor: sqlite3.Cursor):
        """Apply additional SQLite performance optimizations."""
        try:
            cursor.execute("PRAGMA synchronous=NORMAL;")

            # Increase cache size (negative value means KB, positive means pages)
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache

            cursor.execute("PRAGMA temp_store=MEMORY;")

            # Set busy timeout to 30 seconds
            cursor.execute("PRAGMA busy_timeout=30000;")

            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON;")

            logger.info("Applied SQLite performance optimizations")

        except Exception as e:
            logger.warning(f"Failed to apply some performance optimizations: {str(e)}")

    @staticmethod
    def check_wal_status(database_path: str) -> dict:
        """
        Check the current WAL mode status and related settings.

        Args:
            database_path: Path to the SQLite database file

        Returns:
            Dictionary containing WAL status information
        """
        try:
            conn = sqlite3.connect(database_path, timeout=30)
            cursor = conn.cursor()

            # Get various PRAGMA settings
            status = {}

            cursor.execute("PRAGMA journal_mode;")
            status["journal_mode"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA synchronous;")
            status["synchronous"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA cache_size;")
            status["cache_size"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA temp_store;")
            status["temp_store"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA busy_timeout;")
            status["busy_timeout"] = cursor.fetchone()[0]

            cursor.execute("PRAGMA foreign_keys;")
            status["foreign_keys"] = cursor.fetchone()[0]

            db_path = Path(database_path)
            wal_file = db_path.with_suffix(db_path.suffix + "-wal")
            shm_file = db_path.with_suffix(db_path.suffix + "-shm")

            status["wal_file_exists"] = wal_file.exists()
            status["shm_file_exists"] = shm_file.exists()

            if wal_file.exists():
                status["wal_file_size"] = wal_file.stat().st_size

            conn.close()

            return status

        except Exception as e:
            logger.error(f"Failed to check WAL status: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def optimize_database_on_startup(database_url: str) -> bool:
        """
        Optimize SQLite database on application startup.

        Args:
            database_url: SQLAlchemy database URL

        Returns:
            True if optimization was successful, False otherwise
        """
        try:
            if not database_url.startswith("sqlite:///"):
                logger.info("Not a SQLite database, skipping optimizations")
                return True

            db_path = database_url.replace("sqlite:///", "")

            logger.info(f"Optimizing SQLite database: {db_path}")

            # Enable WAL mode and optimizations
            success = SQLiteOptimizer.enable_wal_mode(db_path)

            if success:
                # Check and log status
                status = SQLiteOptimizer.check_wal_status(db_path)
                logger.info(f"Database optimization status: {status}")

            return success

        except Exception as e:
            logger.error(f"Failed to optimize database on startup: {str(e)}")
            return False

def initialize_sqlite_optimizations(database_url: str) -> bool:
    """
    Initialize SQLite optimizations for the application.

    This function should be called during application startup to enable
    WAL mode and other performance optimizations.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        True if initialization was successful, False otherwise
    """
    logger.info("Initializing SQLite optimizations...")

    success = SQLiteOptimizer.optimize_database_on_startup(database_url)

    if success:
        logger.info("SQLite optimizations initialized successfully")
    else:
        logger.warning("SQLite optimizations failed to initialize")

    return success
