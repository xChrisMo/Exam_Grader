"""
Database migration for LLM training enhancements and model testing

This migration adds:
1. Enhanced validation fields to existing LLM tables
2. New model testing tables (llm_model_tests, llm_test_submissions)
3. Additional indexes for performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite, postgresql
import json

# revision identifiers
revision = 'llm_testing_enhancements'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Apply the migration"""
    
    # Add enhanced fields to llm_documents table
    try:
        op.add_column('llm_documents', sa.Column('validation_status', sa.String(50), default='pending'))
        op.add_column('llm_documents', sa.Column('validation_errors', sa.JSON))
        op.add_column('llm_documents', sa.Column('processing_retries', sa.Integer, default=0))
        op.add_column('llm_documents', sa.Column('content_quality_score', sa.Float))
        op.add_column('llm_documents', sa.Column('extraction_method', sa.String(50)))
        op.add_column('llm_documents', sa.Column('processing_duration_ms', sa.Integer))
        print("✓ Enhanced llm_documents table")
    except Exception as e:
        print(f"Warning: Could not enhance llm_documents table: {e}")
    
    # Add enhanced fields to llm_training_jobs table
    try:
        op.add_column('llm_training_jobs', sa.Column('validation_results', sa.JSON))
        op.add_column('llm_training_jobs', sa.Column('health_metrics', sa.JSON))
        op.add_column('llm_training_jobs', sa.Column('resume_count', sa.Integer, default=0))
        op.add_column('llm_training_jobs', sa.Column('quality_score', sa.Float))
        print("✓ Enhanced llm_training_jobs table")
    except Exception as e:
        print(f"Warning: Could not enhance llm_training_jobs table: {e}")
    
    # Create llm_model_tests table
    try:
        op.create_table(
            'llm_model_tests',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
            sa.Column('training_job_id', sa.String(36), sa.ForeignKey('llm_training_jobs.id'), nullable=False, index=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text),
            sa.Column('status', sa.String(50), default='pending'),
            sa.Column('progress', sa.Float, default=0.0),
            sa.Column('config', sa.JSON),
            sa.Column('grading_criteria', sa.JSON),
            sa.Column('confidence_threshold', sa.Float, default=0.8),
            sa.Column('comparison_mode', sa.String(50), default='strict'),
            sa.Column('feedback_level', sa.String(50), default='detailed'),
            sa.Column('results', sa.JSON),
            sa.Column('performance_metrics', sa.JSON),
            sa.Column('accuracy_score', sa.Float),
            sa.Column('average_confidence', sa.Float),
            sa.Column('total_submissions', sa.Integer, default=0),
            sa.Column('processed_submissions', sa.Integer, default=0),
            sa.Column('started_at', sa.DateTime),
            sa.Column('completed_at', sa.DateTime),
            sa.Column('processing_duration_ms', sa.Integer),
            sa.Column('error_message', sa.Text),
            sa.Column('error_details', sa.JSON),
            sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp())
        )
        print("✓ Created llm_model_tests table")
    except Exception as e:
        print(f"Warning: Could not create llm_model_tests table: {e}")
    
    # Create llm_test_submissions table
    try:
        op.create_table(
            'llm_test_submissions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('test_id', sa.String(36), sa.ForeignKey('llm_model_tests.id'), nullable=False, index=True),
            sa.Column('original_name', sa.String(255), nullable=False),
            sa.Column('stored_name', sa.String(255), nullable=False),
            sa.Column('file_path', sa.String(500), nullable=False),
            sa.Column('file_size', sa.Integer, nullable=False),
            sa.Column('file_type', sa.String(50), nullable=False),
            sa.Column('text_content', sa.Text),
            sa.Column('word_count', sa.Integer, default=0),
            sa.Column('processing_status', sa.String(50), default='pending'),
            sa.Column('processing_error', sa.Text),
            sa.Column('processing_duration_ms', sa.Integer),
            sa.Column('expected_grade', sa.Float),
            sa.Column('expected_feedback', sa.Text),
            sa.Column('model_grade', sa.Float),
            sa.Column('model_feedback', sa.Text),
            sa.Column('confidence_score', sa.Float),
            sa.Column('grade_difference', sa.Float),
            sa.Column('grade_accuracy', sa.Boolean),
            sa.Column('feedback_similarity', sa.Float),
            sa.Column('detailed_results', sa.JSON),
            sa.Column('comparison_analysis', sa.JSON),
            sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp())
        )
        print("✓ Created llm_test_submissions table")
    except Exception as e:
        print(f"Warning: Could not create llm_test_submissions table: {e}")
    
    # Add indexes for performance
    try:
        op.create_index('idx_model_tests_user_status', 'llm_model_tests', ['user_id', 'status'])
        op.create_index('idx_model_tests_job_status', 'llm_model_tests', ['training_job_id', 'status'])
        op.create_index('idx_test_submissions_status', 'llm_test_submissions', ['test_id', 'processing_status'])
        print("✓ Created performance indexes")
    except Exception as e:
        print(f"Warning: Could not create indexes: {e}")


def downgrade():
    """Reverse the migration"""
    
    # Drop indexes
    try:
        op.drop_index('idx_test_submissions_status')
        op.drop_index('idx_model_tests_job_status')
        op.drop_index('idx_model_tests_user_status')
        print("✓ Dropped performance indexes")
    except Exception as e:
        print(f"Warning: Could not drop indexes: {e}")
    
    # Drop tables
    try:
        op.drop_table('llm_test_submissions')
        print("✓ Dropped llm_test_submissions table")
    except Exception as e:
        print(f"Warning: Could not drop llm_test_submissions table: {e}")
    
    try:
        op.drop_table('llm_model_tests')
        print("✓ Dropped llm_model_tests table")
    except Exception as e:
        print(f"Warning: Could not drop llm_model_tests table: {e}")
    
    # Remove enhanced fields from llm_training_jobs
    try:
        op.drop_column('llm_training_jobs', 'quality_score')
        op.drop_column('llm_training_jobs', 'resume_count')
        op.drop_column('llm_training_jobs', 'health_metrics')
        op.drop_column('llm_training_jobs', 'validation_results')
        print("✓ Removed enhanced fields from llm_training_jobs")
    except Exception as e:
        print(f"Warning: Could not remove enhanced fields from llm_training_jobs: {e}")
    
    # Remove enhanced fields from llm_documents
    try:
        op.drop_column('llm_documents', 'processing_duration_ms')
        op.drop_column('llm_documents', 'extraction_method')
        op.drop_column('llm_documents', 'content_quality_score')
        op.drop_column('llm_documents', 'processing_retries')
        op.drop_column('llm_documents', 'validation_errors')
        op.drop_column('llm_documents', 'validation_status')
        print("✓ Removed enhanced fields from llm_documents")
    except Exception as e:
        print(f"Warning: Could not remove enhanced fields from llm_documents: {e}")


if __name__ == '__main__':
    """Run migration directly for testing"""
    print("Running LLM training enhancements migration...")
    upgrade()
    print("Migration completed successfully!")