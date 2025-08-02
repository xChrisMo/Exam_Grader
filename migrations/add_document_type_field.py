"""
Add type field to LLMDocument model for enhanced LLM training workflow

This migration adds a 'type' field to distinguish between different document types:
- 'document': Regular training documents (default)
- 'training_guide': Marking guides for training
- 'test_submission': Student submissions for testing
"""

from sqlalchemy import text
from src.database.models import db
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add type field to llm_documents table"""
    try:
        # Add the type column with default value
        db.session.execute(text("""
            ALTER TABLE llm_documents 
            ADD COLUMN type VARCHAR(50) DEFAULT 'document' NOT NULL
        """))
        
        # Add index for better query performance
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_llm_documents_type 
            ON llm_documents(type)
        """))
        
        # Add composite index for user_id and type
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_llm_documents_user_type 
            ON llm_documents(user_id, type)
        """))
        
        db.session.commit()
        logger.info("Successfully added type field to llm_documents table")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding type field to llm_documents: {e}")
        raise

def downgrade():
    """Remove type field from llm_documents table"""
    try:
        # Drop indexes first
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_llm_documents_type
        """))
        
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_llm_documents_user_type
        """))
        
        # Remove the type column
        db.session.execute(text("""
            ALTER TABLE llm_documents 
            DROP COLUMN IF EXISTS type
        """))
        
        db.session.commit()
        logger.info("Successfully removed type field from llm_documents table")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing type field from llm_documents: {e}")
        raise

if __name__ == "__main__":
    # Run the migration within Flask app context
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from webapp.app import app
    
    with app.app_context():
        upgrade()