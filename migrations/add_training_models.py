"""
Database migration for LLM Training Page models

This migration adds the training-related tables for the LLM Training Page feature:
- training_sessions: Main training session management
- training_guides: Uploaded marking guides for training
- training_questions: Extracted questions and criteria
- training_results: Training outcomes and metrics
- test_submissions: Model validation test data
"""

from datetime import datetime
from src.database.models import db
import uuid


def upgrade():
    """Create training-related tables"""
    
    # Create training_sessions table
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS training_sessions (
            id VARCHAR(36) PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            user_id VARCHAR(36) NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'created',
            max_questions_to_answer INTEGER,
            use_in_main_app BOOLEAN NOT NULL DEFAULT 0,
            confidence_threshold FLOAT NOT NULL DEFAULT 0.6,
            total_guides INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            average_confidence FLOAT,
            training_duration_seconds INTEGER,
            current_step VARCHAR(100),
            progress_percentage FLOAT DEFAULT 0.0,
            error_message TEXT,
            model_data JSON,
            is_active BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """))
    
    # Create training_guides table
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS training_guides (
            id VARCHAR(36) PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            session_id VARCHAR(36) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size INTEGER NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            guide_type VARCHAR(50) NOT NULL,
            content_text TEXT,
            content_hash VARCHAR(64),
            processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
            processing_error TEXT,
            confidence_score FLOAT,
            question_count INTEGER DEFAULT 0,
            total_marks FLOAT DEFAULT 0.0,
            format_confidence FLOAT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES training_sessions (id)
        )
    """))
    
    # Create training_questions table
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS training_questions (
            id VARCHAR(36) PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            guide_id VARCHAR(36) NOT NULL,
            question_number VARCHAR(50) NOT NULL,
            question_text TEXT NOT NULL,
            expected_answer TEXT,
            point_value FLOAT NOT NULL,
            rubric_details JSON,
            visual_elements JSON,
            context TEXT,
            extraction_confidence FLOAT,
            manual_review_required BOOLEAN DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (guide_id) REFERENCES training_guides (id)
        )
    """))
    
    # Create training_results table
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS training_results (
            id VARCHAR(36) PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            session_id VARCHAR(36) NOT NULL,
            total_processing_time FLOAT NOT NULL,
            questions_processed INTEGER NOT NULL,
            questions_with_high_confidence INTEGER DEFAULT 0,
            questions_requiring_review INTEGER DEFAULT 0,
            average_confidence_score FLOAT,
            predicted_accuracy FLOAT,
            training_metadata JSON,
            model_parameters JSON,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES training_sessions (id)
        )
    """))
    
    # Create test_submissions table
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS test_submissions (
            id VARCHAR(36) PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            session_id VARCHAR(36) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            extracted_text TEXT,
            ocr_confidence FLOAT,
            predicted_score FLOAT,
            confidence_score FLOAT,
            matched_questions JSON,
            misalignments JSON,
            processing_status VARCHAR(50) DEFAULT 'pending',
            processing_error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES training_sessions (id)
        )
    """))
    
    # Create indexes for performance
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_session_user_status ON training_sessions (user_id, status)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_session_created ON training_sessions (created_at)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_session_active ON training_sessions (is_active)"))
    
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_guide_session ON training_guides (session_id)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_guide_status ON training_guides (processing_status)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_guide_hash ON training_guides (content_hash)"))
    
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_question_guide ON training_questions (guide_id)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_question_confidence ON training_questions (extraction_confidence)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_question_review ON training_questions (manual_review_required)"))
    
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_result_session ON training_results (session_id)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_training_result_confidence ON training_results (average_confidence_score)"))
    
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_test_submission_session ON test_submissions (session_id)"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS idx_test_submission_status ON test_submissions (processing_status)"))
    
    print("Training tables created successfully")


def downgrade():
    """Drop training-related tables"""
    
    # Drop tables in reverse order due to foreign key constraints
    db.session.execute(db.text("DROP TABLE IF EXISTS test_submissions"))
    db.session.execute(db.text("DROP TABLE IF EXISTS training_results"))
    db.session.execute(db.text("DROP TABLE IF EXISTS training_questions"))
    db.session.execute(db.text("DROP TABLE IF EXISTS training_guides"))
    db.session.execute(db.text("DROP TABLE IF EXISTS training_sessions"))
    
    print("Training tables dropped successfully")


if __name__ == "__main__":
    # Run migration directly
    from webapp.app import app
    
    with app.app_context():
        upgrade()