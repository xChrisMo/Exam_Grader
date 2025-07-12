#!/usr/bin/env python3
"""
Migration script to add content_hash columns for duplicate detection.

This script adds content_hash columns to submissions and marking_guides tables
to enable duplicate file detection based on content rather than filename.
"""

import sys
import os
import hashlib
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.models import db, Submission, MarkingGuide
from webapp.exam_grader_app import create_app
from utils.logger import logger


def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing."""
    if not text:
        return ""
    
    # Convert to lowercase and remove extra whitespace
    normalized = ' '.join(text.lower().split())
    
    # Remove common punctuation that doesn't affect content meaning
    chars_to_remove = '.,;:!?"\''
    for char in chars_to_remove:
        normalized = normalized.replace(char, '')
    
    return normalized.strip()


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of normalized text content."""
    normalized_text = normalize_text(text)
    return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()


def add_content_hash_columns():
    """Add content_hash columns to submissions and marking_guides tables."""
    try:
        logger.info("Starting content_hash migration...")
        
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        
        # Check submissions table
        submissions_columns = [col['name'] for col in inspector.get_columns('submissions')]
        if 'content_hash' not in submissions_columns:
            logger.info("Adding content_hash column to submissions table...")
            with db.engine.connect() as connection:
                with connection.begin():
                    if db.engine.dialect.name == 'sqlite':
                        connection.execute(db.text("ALTER TABLE submissions ADD COLUMN content_hash VARCHAR(64)"))
                    elif db.engine.dialect.name == 'postgresql':
                        connection.execute(db.text("ALTER TABLE submissions ADD COLUMN content_hash VARCHAR(64)"))
            logger.info("✓ Added content_hash column to submissions table")
        else:
            logger.info("✓ content_hash column already exists in submissions table")
        
        # Check marking_guides table
        guides_columns = [col['name'] for col in inspector.get_columns('marking_guides')]
        if 'content_hash' not in guides_columns:
            logger.info("Adding content_hash column to marking_guides table...")
            with db.engine.connect() as connection:
                with connection.begin():
                    if db.engine.dialect.name == 'sqlite':
                        connection.execute(db.text("ALTER TABLE marking_guides ADD COLUMN content_hash VARCHAR(64)"))
                    elif db.engine.dialect.name == 'postgresql':
                        connection.execute(db.text("ALTER TABLE marking_guides ADD COLUMN content_hash VARCHAR(64)"))
            logger.info("✓ Added content_hash column to marking_guides table")
        else:
            logger.info("✓ content_hash column already exists in marking_guides table")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to add content_hash columns: {e}")
        return False


def create_indexes():
    """Create indexes on content_hash columns for fast duplicate lookup."""
    try:
        logger.info("Creating indexes on content_hash columns...")
        
        with db.engine.connect() as connection:
            with connection.begin():
                # Index for submissions content_hash
                try:
                    connection.execute(db.text("CREATE INDEX IF NOT EXISTS idx_submissions_content_hash ON submissions(content_hash)"))
                    logger.info("✓ Created index on submissions.content_hash")
                except Exception as e:
                    logger.warning(f"Index on submissions.content_hash may already exist: {e}")
                
                # Index for marking_guides content_hash
                try:
                    connection.execute(db.text("CREATE INDEX IF NOT EXISTS idx_marking_guides_content_hash ON marking_guides(content_hash)"))
                    logger.info("✓ Created index on marking_guides.content_hash")
                except Exception as e:
                    logger.warning(f"Index on marking_guides.content_hash may already exist: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        return False


def populate_existing_hashes():
    """Populate content_hash for existing records."""
    try:
        logger.info("Populating content_hash for existing records...")
        
        # Update submissions
        submissions = db.session.query(Submission).filter(
            Submission.content_hash.is_(None),
            Submission.content_text.isnot(None)
        ).all()
        
        updated_submissions = 0
        for submission in submissions:
            if submission.content_text:
                submission.content_hash = compute_content_hash(submission.content_text)
                updated_submissions += 1
        
        # Update marking guides
        guides = db.session.query(MarkingGuide).filter(
            MarkingGuide.content_hash.is_(None),
            MarkingGuide.content_text.isnot(None)
        ).all()
        
        updated_guides = 0
        for guide in guides:
            if guide.content_text:
                guide.content_hash = compute_content_hash(guide.content_text)
                updated_guides += 1
        
        db.session.commit()
        
        logger.info(f"✓ Updated content_hash for {updated_submissions} submissions")
        logger.info(f"✓ Updated content_hash for {updated_guides} marking guides")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to populate content hashes: {e}")
        db.session.rollback()
        return False


def verify_migration():
    """Verify the migration was successful."""
    try:
        logger.info("Verifying content_hash migration...")
        
        inspector = db.inspect(db.engine)
        
        # Check submissions table
        submissions_columns = [col['name'] for col in inspector.get_columns('submissions')]
        if 'content_hash' not in submissions_columns:
            logger.error("❌ content_hash column missing from submissions table")
            return False
        
        # Check marking_guides table
        guides_columns = [col['name'] for col in inspector.get_columns('marking_guides')]
        if 'content_hash' not in guides_columns:
            logger.error("❌ content_hash column missing from marking_guides table")
            return False
        
        # Check indexes exist
        submissions_indexes = [idx['name'] for idx in inspector.get_indexes('submissions')]
        guides_indexes = [idx['name'] for idx in inspector.get_indexes('marking_guides')]
        
        if 'idx_submissions_content_hash' not in submissions_indexes:
            logger.warning("⚠️ Index on submissions.content_hash not found")
        
        if 'idx_marking_guides_content_hash' not in guides_indexes:
            logger.warning("⚠️ Index on marking_guides.content_hash not found")
        
        logger.info("✅ Content hash migration verification completed")
        return True
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False


def main():
    """Main migration function."""
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            logger.info("=== Content Hash Migration Started ===")
            
            # Step 1: Add columns
            if not add_content_hash_columns():
                logger.error("Failed to add content_hash columns")
                return False
            
            # Step 2: Create indexes
            if not create_indexes():
                logger.error("Failed to create indexes")
                return False
            
            # Step 3: Populate existing records
            if not populate_existing_hashes():
                logger.error("Failed to populate existing hashes")
                return False
            
            # Step 4: Verify migration
            if not verify_migration():
                logger.error("Migration verification failed")
                return False
            
            logger.info("=== Content Hash Migration Completed Successfully ===")
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)