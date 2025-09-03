#!/usr/bin/env python3
"""
Database migration to add comprehensive settings fields to UserSettings table.
This migration adds all the new configuration options for controlling the entire website.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from webapp.app_factory import create_app
from src.database.models import db
from utils.logger import logger


def upgrade():
    """Add new settings columns to user_settings table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we need to run this migration
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            # List of new columns to add
            new_columns = [
                # Processing & Performance settings
                ('default_processing_method', 'VARCHAR(50) DEFAULT "traditional_ocr"'),
                ('processing_timeout', 'INTEGER DEFAULT 300'),
                ('max_retry_attempts', 'INTEGER DEFAULT 3'),
                ('enable_processing_fallback', 'BOOLEAN DEFAULT 1'),
                
                # Grading & AI settings
                ('llm_strict_mode', 'BOOLEAN DEFAULT 0'),
                ('llm_require_json_response', 'BOOLEAN DEFAULT 1'),
                ('grading_confidence_threshold', 'INTEGER DEFAULT 75'),
                ('auto_grade_threshold', 'INTEGER DEFAULT 80'),
                
                # Security & Privacy settings
                ('session_timeout', 'INTEGER DEFAULT 120'),
                ('auto_delete_after_days', 'INTEGER DEFAULT 30'),
                ('enable_audit_logging', 'BOOLEAN DEFAULT 0'),
                ('encrypt_stored_files', 'BOOLEAN DEFAULT 0'),
                
                # Monitoring & Logging settings
                ('log_level', 'VARCHAR(20) DEFAULT "INFO"'),
                ('enable_performance_monitoring', 'BOOLEAN DEFAULT 1'),
                ('enable_error_reporting', 'BOOLEAN DEFAULT 1'),
                ('metrics_retention_days', 'INTEGER DEFAULT 90'),
                
                # Email & Notification settings
                ('notification_email', 'VARCHAR(255)'),
                ('webhook_url', 'VARCHAR(500)'),
                
                # Cache & Storage settings
                ('cache_type', 'VARCHAR(20) DEFAULT "simple"'),
                ('cache_ttl_hours', 'INTEGER DEFAULT 24'),
                ('enable_cache_warming', 'BOOLEAN DEFAULT 0'),
                ('auto_cleanup_storage', 'BOOLEAN DEFAULT 1'),
                
                # Advanced System settings
                ('debug_mode', 'BOOLEAN DEFAULT 0'),
                ('maintenance_mode', 'BOOLEAN DEFAULT 0'),
                ('max_concurrent_processes', 'INTEGER DEFAULT 4'),
                ('memory_limit_gb', 'INTEGER DEFAULT 4'),
            ]
            
            # Add missing columns
            columns_added = 0
            for column_name, column_def in new_columns:
                if column_name not in columns:
                    try:
                        sql = f'ALTER TABLE user_settings ADD COLUMN {column_name} {column_def}'
                        with db.engine.connect() as conn:
                            conn.execute(db.text(sql))
                            conn.commit()
                        logger.info(f"Added column: {column_name}")
                        columns_added += 1
                    except Exception as e:
                        logger.error(f"Failed to add column {column_name}: {e}")
                        raise
                else:
                    logger.info(f"Column {column_name} already exists, skipping")
            
            if columns_added > 0:
                logger.info(f"Migration completed successfully. Added {columns_added} new columns.")
            else:
                logger.info("No migration needed - all columns already exist.")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


def downgrade():
    """Remove the added settings columns (if needed)."""
    app = create_app()
    
    with app.app_context():
        try:
            # List of columns to remove (in reverse order)
            columns_to_remove = [
                'memory_limit_gb', 'max_concurrent_processes', 'maintenance_mode', 'debug_mode',
                'auto_cleanup_storage', 'enable_cache_warming', 'cache_ttl_hours', 'cache_type',
                'webhook_url', 'notification_email',
                'metrics_retention_days', 'enable_error_reporting', 'enable_performance_monitoring', 'log_level',
                'encrypt_stored_files', 'enable_audit_logging', 'auto_delete_after_days', 'session_timeout',
                'auto_grade_threshold', 'grading_confidence_threshold', 'llm_require_json_response', 'llm_strict_mode',
                'enable_processing_fallback', 'max_retry_attempts', 'processing_timeout', 'default_processing_method'
            ]
            
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user_settings')]
            
            columns_removed = 0
            for column_name in columns_to_remove:
                if column_name in existing_columns:
                    try:
                        # Note: SQLite doesn't support DROP COLUMN, so this would need a table recreation
                        # For now, we'll just log what would be removed
                        logger.info(f"Would remove column: {column_name}")
                        columns_removed += 1
                    except Exception as e:
                        logger.error(f"Failed to remove column {column_name}: {e}")
            
            logger.info(f"Downgrade completed. Would remove {columns_removed} columns.")
            logger.warning("Note: SQLite doesn't support DROP COLUMN. Manual table recreation needed for full downgrade.")
            
        except Exception as e:
            logger.error(f"Downgrade failed: {e}")
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration for comprehensive settings")
    parser.add_argument("--downgrade", action="store_true", help="Run downgrade instead of upgrade")
    
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade()