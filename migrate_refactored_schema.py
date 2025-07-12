#!/usr/bin/env python3
"""
Database Migration Script for Refactored AI Processing

Adds:
- max_questions_to_answer field to MarkingGuide table
- GradingSession table for tracking AI processing sessions
- Necessary indexes for performance
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database import db
from src.database.models import MarkingGuide, GradingSession
from webapp.exam_grader_app import app
from sqlalchemy import text, inspect
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table(table_name):
            logger.warning(f"Table {table_name} does not exist")
            return False
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error checking column {column_name} in {table_name}: {e}")
        return False

def check_table_exists(table_name):
    """Check if a table exists."""
    try:
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error checking table {table_name}: {e}")
        return False

def add_max_questions_field():
    """Add max_questions_to_answer field to MarkingGuide table."""
    try:
        if check_column_exists('marking_guides', 'max_questions_to_answer'):
            logger.info("max_questions_to_answer column already exists in marking_guides table")
            return True
        
        logger.info("Adding max_questions_to_answer column to marking_guides table...")
        
        # Add the column
        db.session.execute(text(
            "ALTER TABLE marking_guides ADD COLUMN max_questions_to_answer INTEGER DEFAULT NULL"
        ))
        db.session.commit()
        
        logger.info("Successfully added max_questions_to_answer column")
        return True
        
    except Exception as e:
        logger.error(f"Error adding max_questions_to_answer column: {e}")
        return False

def create_grading_session_table():
    """Create the GradingSession table."""
    try:
        if check_table_exists('grading_sessions'):
            logger.info("grading_sessions table already exists")
            return True
        
        logger.info("Creating grading_sessions table...")
        
        # Create the table using SQLAlchemy
        # This will create the table with its defined indexes automatically
        db.create_all()
        
        # Verify table was created
        if check_table_exists('grading_sessions'):
            logger.info("Successfully created grading_sessions table")
            return True
        else:
            logger.error("Failed to create grading_sessions table")
            return False
        
    except Exception as e:
        logger.error(f"Error creating grading_sessions table: {e}")
        return False

def create_indexes():
    """Create necessary indexes for performance (if not already created by model definition)."""
    try:
        logger.info("Checking indexes for grading_sessions table...")
        
        # The GradingSession model already defines its own indexes in __table_args__
        # So we don't need to create them manually here
        # Just verify they exist
        
        inspector = inspect(db.engine)
        if inspector.has_table('grading_sessions'):
            indexes = inspector.get_indexes('grading_sessions')
            index_names = [idx['name'] for idx in indexes]
            logger.info(f"Found {len(indexes)} indexes on grading_sessions table: {index_names}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking indexes: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful."""
    try:
        logger.info("Verifying migration...")
        
        # Check max_questions_to_answer column
        if not check_column_exists('marking_guides', 'max_questions_to_answer'):
            logger.error("max_questions_to_answer column not found in marking_guides table")
            return False
        
        # Check grading_sessions table
        if not check_table_exists('grading_sessions'):
            logger.error("grading_sessions table not found")
            return False
        
        # Test basic operations
        try:
            # Test querying the new column
            result = db.session.execute(text(
                "SELECT COUNT(*) FROM marking_guides WHERE max_questions_to_answer IS NULL"
            ))
            count = result.scalar()
            logger.info(f"Found {count} marking guides with NULL max_questions_to_answer")
            
            # Test grading_sessions table structure
            inspector = inspect(db.engine)
            columns = inspector.get_columns('grading_sessions')
            expected_columns = [
                'id', 'submission_id', 'marking_guide_id', 'user_id', 'progress_id', 'status',
                'current_step', 'total_questions_mapped', 'total_questions_graded', 
                'max_questions_limit', 'processing_start_time', 'processing_end_time',
                'error_message', 'session_data', 'created_at', 'updated_at'
            ]
            
            found_columns = [col['name'] for col in columns]
            missing_columns = [col for col in expected_columns if col not in found_columns]
            
            if missing_columns:
                logger.error(f"Missing columns in grading_sessions table: {missing_columns}")
                return False
            
            logger.info(f"grading_sessions table has all expected columns: {len(found_columns)} columns")
            
        except Exception as e:
            logger.error(f"Error testing migration: {e}")
            return False
        
        logger.info("Migration verification successful!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration: {e}")
        return False

def main():
    """Run the migration."""
    logger.info("Starting refactored AI processing schema migration...")
    
    try:
        with app.app_context():
            # Step 1: Add max_questions_to_answer field
            if not add_max_questions_field():
                logger.error("Failed to add max_questions_to_answer field")
                return False
            
            # Step 2: Create grading_session table
            if not create_grading_session_table():
                logger.error("Failed to create grading_session table")
                return False
            
            # Step 3: Create indexes
            if not create_indexes():
                logger.error("Failed to create indexes")
                return False
            
            # Step 4: Verify migration
            if not verify_migration():
                logger.error("Migration verification failed")
                return False
            
            logger.info("Migration completed successfully!")
            
            # Print summary
            print("\n" + "="*60)
            print("REFACTORED AI PROCESSING MIGRATION SUMMARY")
            print("="*60)
            print("✅ Added max_questions_to_answer field to MarkingGuide table")
            print("✅ Created GradingSession table for tracking AI processing")
            print("✅ Created performance indexes")
            print("✅ Verified migration integrity")
            print("\nThe refactored AI processing system is now ready to use!")
            print("Access it at: /refactored/ai-processing")
            print("="*60)
            
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)