"""Add LLM training tables

Revision ID: add_llm_training_tables
Revises: previous_migration
Create Date: 2025-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_llm_training_tables'
down_revision = None  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create LLM training jobs table
    op.create_table('llm_training_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('dataset_id', sa.String(36), sa.ForeignKey('llm_datasets.id'), nullable=False, index=True),
        sa.Column('status', sa.String(50), default='pending', nullable=False),
        sa.Column('progress', sa.Float, default=0.0),
        sa.Column('current_epoch', sa.Integer, default=0),
        sa.Column('total_epochs', sa.Integer, default=10),
        sa.Column('accuracy', sa.Float),
        sa.Column('validation_accuracy', sa.Float),
        sa.Column('loss', sa.Float),
        sa.Column('validation_loss', sa.Float),
        sa.Column('start_time', sa.DateTime),
        sa.Column('end_time', sa.DateTime),
        sa.Column('error_message', sa.Text),
        sa.Column('config_epochs', sa.Integer, default=10),
        sa.Column('config_batch_size', sa.Integer, default=8),
        sa.Column('config_learning_rate', sa.Float, default=0.0001),
        sa.Column('config_max_tokens', sa.Integer, default=512),
        sa.Column('config_temperature', sa.Float),
        sa.Column('config_custom_parameters', sa.JSON),
        sa.Column('training_metrics', sa.JSON),
        sa.Column('evaluation_results', sa.JSON),
        sa.Column('model_output_path', sa.String(500)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )

    # Create LLM training reports table
    op.create_table('llm_training_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('job_ids', sa.JSON, nullable=False),
        sa.Column('report_type', sa.String(50), default='training_summary'),
        sa.Column('format', sa.String(20), default='html'),
        sa.Column('status', sa.String(50), default='generating'),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.Integer),
        sa.Column('include_metrics', sa.Boolean, default=True),
        sa.Column('include_logs', sa.Boolean, default=False),
        sa.Column('include_charts', sa.Boolean, default=True),
        sa.Column('chart_format', sa.String(10), default='png'),
        sa.Column('report_data', sa.JSON),
        sa.Column('generation_error', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )

    # Create indexes for better performance
    op.create_index('idx_training_jobs_user_status', 'llm_training_jobs', ['user_id', 'status'])
    op.create_index('idx_training_jobs_dataset', 'llm_training_jobs', ['dataset_id'])
    op.create_index('idx_training_jobs_created', 'llm_training_jobs', ['created_at'])
    
    op.create_index('idx_training_reports_user', 'llm_training_reports', ['user_id'])
    op.create_index('idx_training_reports_status', 'llm_training_reports', ['status'])
    op.create_index('idx_training_reports_created', 'llm_training_reports', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_training_reports_created', 'llm_training_reports')
    op.drop_index('idx_training_reports_status', 'llm_training_reports')
    op.drop_index('idx_training_reports_user', 'llm_training_reports')
    
    op.drop_index('idx_training_jobs_created', 'llm_training_jobs')
    op.drop_index('idx_training_jobs_dataset', 'llm_training_jobs')
    op.drop_index('idx_training_jobs_user_status', 'llm_training_jobs')
    
    # Drop tables
    op.drop_table('llm_training_reports')
    op.drop_table('llm_training_jobs')