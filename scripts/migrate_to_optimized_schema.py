#!/usr/bin/env python3
"""Migration script to upgrade database schema to optimized models.

This script handles the migration from the current database schema
to the optimized schema with improved indexes, constraints, and validation.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema_migrations import MigrationManager
from src.database.optimized_models import db
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def backup_database(db_path: str) -> str:
    """Create a backup of the current database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Path to the backup file
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database file {db_path} does not exist")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        raise


def verify_migration_prerequisites() -> bool:
    """Verify that all prerequisites for migration are met.
    
    Returns:
        True if prerequisites are met, False otherwise
    """
    logger.info("Verifying migration prerequisites...")
    
    # Check if required modules are available
    try:
        import sqlalchemy
        import sqlite3
        logger.info(f"SQLAlchemy version: {sqlalchemy.__version__}")
    except ImportError as e:
        logger.error(f"Required module not available: {e}")
        return False
    
    # Check if database file exists and is accessible
    config = Config()
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    
    if os.path.exists(db_path):
        if not os.access(db_path, os.R_OK | os.W_OK):
            logger.error(f"Database file {db_path} is not readable/writable")
            return False
        logger.info(f"Database file found: {db_path}")
    else:
        logger.info(f"Database file {db_path} does not exist - will be created")
    
    return True


def run_migration() -> bool:
    """Run the database migration.
    
    Returns:
        True if migration was successful, False otherwise
    """
    try:
        logger.info("Starting database migration...")
        
        # Initialize migration manager
        migration_manager = MigrationManager()
        
        # Get current migration status
        status = migration_manager.get_migration_status()
        logger.info(f"Current migration status: {status}")
        
        # Apply pending migrations
        if status['pending_migrations']:
            logger.info(f"Applying {len(status['pending_migrations'])} pending migrations...")
            
            for migration_version in status['pending_migrations']:
                logger.info(f"Applying migration {migration_version}...")
                success = migration_manager.apply_migration(migration_version)
                
                if success:
                    logger.info(f"Migration {migration_version} applied successfully")
                else:
                    logger.error(f"Migration {migration_version} failed")
                    return False
            
            logger.info("All migrations applied successfully")
        else:
            logger.info("No pending migrations found")
        
        # Verify final status
        final_status = migration_manager.get_migration_status()
        logger.info(f"Final migration status: {final_status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def validate_migrated_schema() -> bool:
    """Validate that the migrated schema is correct.
    
    Returns:
        True if schema is valid, False otherwise
    """
    try:
        logger.info("Validating migrated schema...")
        
        from sqlalchemy import create_engine, inspect
        
        config = Config()
        engine = create_engine(config.DATABASE_URL)
        inspector = inspect(engine)
        
        # Check that all expected tables exist
        expected_tables = [
            'users', 'marking_guides', 'submissions', 
            'mappings', 'grading_results', 'sessions', 
            'grading_sessions', 'schema_migrations'
        ]
        
        existing_tables = inspector.get_table_names()
        
        for table in expected_tables:
            if table not in existing_tables:
                logger.error(f"Expected table '{table}' not found")
                return False
            logger.info(f"Table '{table}' exists")
        
        # Check that key indexes exist
        expected_indexes = {
            'users': ['ix_users_username', 'ix_users_email', 'ix_users_created_at'],
            'submissions': ['ix_submissions_content_hash', 'ix_submissions_processing_status'],
            'marking_guides': ['ix_marking_guides_user_id', 'ix_marking_guides_created_at']
        }
        
        for table, indexes in expected_indexes.items():
            table_indexes = [idx['name'] for idx in inspector.get_indexes(table)]
            
            for index in indexes:
                if index not in table_indexes:
                    logger.warning(f"Expected index '{index}' not found in table '{table}'")
                else:
                    logger.info(f"Index '{index}' exists in table '{table}'")
        
        logger.info("Schema validation completed")
        return True
        
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False


def main():
    """Main migration function."""
    logger.info("=" * 60)
    logger.info("Starting Exam Grader Database Migration")
    logger.info("=" * 60)
    
    try:
        # Step 1: Verify prerequisites
        if not verify_migration_prerequisites():
            logger.error("Migration prerequisites not met")
            sys.exit(1)
        
        # Step 2: Backup database
        config = Config()
        db_path = config.DATABASE_URL.replace('sqlite:///', '')
        
        if os.path.exists(db_path):
            backup_path = backup_database(db_path)
            if backup_path:
                logger.info(f"Database backup created: {backup_path}")
        
        # Step 3: Run migration
        if not run_migration():
            logger.error("Migration failed")
            sys.exit(1)
        
        # Step 4: Validate schema
        if not validate_migrated_schema():
            logger.error("Schema validation failed")
            sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("Database migration completed successfully!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()