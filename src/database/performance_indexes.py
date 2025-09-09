"""Database performance indexes for faster queries."""

from sqlalchemy import Index
from src.database.models import db, MarkingGuide, Submission, User, GradingResult

def create_performance_indexes():
    """Create database indexes for better query performance."""
    try:
        # Index for user-based queries on MarkingGuide
        Index('idx_marking_guide_user_created', MarkingGuide.user_id, MarkingGuide.created_at).create(db.engine, checkfirst=True)
        Index('idx_marking_guide_user_active', MarkingGuide.user_id, MarkingGuide.is_active).create(db.engine, checkfirst=True)

        # Index for user-based queries on Submission
        Index('idx_submission_user_created', Submission.user_id, Submission.created_at).create(db.engine, checkfirst=True)
        Index('idx_submission_user_status', Submission.user_id, Submission.processing_status).create(db.engine, checkfirst=True)
        Index('idx_submission_guide_user', Submission.marking_guide_id, Submission.user_id).create(db.engine, checkfirst=True)

        # Index for grading results
        Index('idx_grading_result_submission', GradingResult.submission_id).create(db.engine, checkfirst=True)

        # Content hash indexes for duplicate detection
        Index('idx_marking_guide_content_hash', MarkingGuide.content_hash).create(db.engine, checkfirst=True)
        Index('idx_submission_content_hash', Submission.content_hash).create(db.engine, checkfirst=True)

        print("Performance indexes created successfully")

    except Exception as e:
        print(f"Error creating indexes: {e}")
        # Indexes might already exist, which is fine
        pass