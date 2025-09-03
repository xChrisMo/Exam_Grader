"""
Database migration for error tracking and monitoring models.

This migration adds the new models for comprehensive error tracking,
service health monitoring, and performance metrics collection.
"""

from flask import current_app
from src.database.models import db
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Apply the migration - create new tables for error tracking and monitoring."""
    try:
        logger.info("Starting migration: add_error_tracking_models")
        
        # Create all tables defined in models
        # This will create the new tables while leaving existing ones unchanged
        db.create_all()
        
        logger.info("Successfully created error tracking and monitoring tables:")
        logger.info("- processing_errors: For detailed error tracking with categorization")
        logger.info("- service_health: For service health status and diagnostics")
        logger.info("- performance_metrics: For enhanced performance monitoring")
        logger.info("- system_alerts: For system alerts and notifications")
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            'processing_errors',
            'service_health', 
            'performance_metrics',
            'system_alerts'
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.warning(f"Some tables were not created: {missing_tables}")
        else:
            logger.info("All required tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def downgrade():
    """Reverse the migration - drop the new tables."""
    try:
        logger.info("Starting downgrade: add_error_tracking_models")
        
        # Drop the new tables in reverse order to handle foreign key constraints
        tables_to_drop = [
            'system_alerts',
            'performance_metrics', 
            'service_health',
            'processing_errors'
        ]
        
        for table_name in tables_to_drop:
            try:
                db.engine.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"Dropped table: {table_name}")
            except Exception as e:
                logger.warning(f"Could not drop table {table_name}: {e}")
        
        logger.info("Migration downgrade completed")
        return True
        
    except Exception as e:
        logger.error(f"Migration downgrade failed: {e}")
        return False


def run_migration():
    """Run the migration with proper Flask app context."""
    try:
        with current_app.app_context():
            success = upgrade()
            if success:
                logger.info("Error tracking models migration completed successfully")
            else:
                logger.error("Error tracking models migration failed")
            return success
    except Exception as e:
        logger.error(f"Failed to run migration: {e}")
        return False


if __name__ == "__main__":
    # Allow running migration directly
    from webapp.app_factory import create_app
    
    app = create_app()
    with app.app_context():
        success = upgrade()
        if success:
            print("Migration completed successfully")
        else:
            print("Migration failed")