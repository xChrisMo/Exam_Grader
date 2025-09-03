"""Add progress tracking tables

Revision ID: add_progress_tracking
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_progress_tracking'
down_revision = None  # Update this to the latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Create progress tracking tables."""
    
    # Create progress_sessions table
    op.create_table(
        'progress_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False, default=0),
        sa.Column('total_submissions', sa.Integer(), nullable=False, default=1),
        sa.Column('current_submission', sa.Integer(), nullable=False, default=0),
        sa.Column('session_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('estimated_duration', sa.Float(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create indexes for progress_sessions
    op.create_index('idx_progress_sessions_session_id', 'progress_sessions', ['session_id'])
    op.create_index('idx_progress_sessions_user_id', 'progress_sessions', ['user_id'])
    op.create_index('idx_progress_sessions_status', 'progress_sessions', ['status'])
    op.create_index('idx_progress_sessions_session_type', 'progress_sessions', ['session_type'])
    op.create_index('idx_progress_sessions_start_time', 'progress_sessions', ['start_time'])
    
    # Create progress_updates table
    op.create_table(
        'progress_updates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('operation', sa.String(255), nullable=False),
        sa.Column('submission_index', sa.Integer(), nullable=False, default=0),
        sa.Column('percentage', sa.Float(), nullable=False, default=0.0),
        sa.Column('estimated_time_remaining', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='processing'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['progress_sessions.session_id'], ondelete='CASCADE')
    )
    
    # Create indexes for progress_updates
    op.create_index('idx_progress_updates_session_id', 'progress_updates', ['session_id'])
    op.create_index('idx_progress_updates_created_at', 'progress_updates', ['created_at'])
    op.create_index('idx_progress_updates_status', 'progress_updates', ['status'])
    op.create_index('idx_progress_updates_step_number', 'progress_updates', ['step_number'])
    
    # Create progress_recovery table
    op.create_table(
        'progress_recovery',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('recovery_type', sa.String(50), nullable=False),
        sa.Column('recovery_point', sa.Integer(), nullable=True),
        sa.Column('recovery_data', sa.JSON(), nullable=True),
        sa.Column('recovery_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('recovery_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['progress_sessions.session_id'], ondelete='CASCADE')
    )
    
    # Create indexes for progress_recovery
    op.create_index('idx_progress_recovery_session_id', 'progress_recovery', ['session_id'])
    op.create_index('idx_progress_recovery_status', 'progress_recovery', ['recovery_status'])
    op.create_index('idx_progress_recovery_created_at', 'progress_recovery', ['created_at'])
    
    # Create progress_metrics table
    op.create_table(
        'progress_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(50), nullable=True),
        sa.Column('measurement_time', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['progress_sessions.session_id'], ondelete='CASCADE')
    )
    
    # Create indexes for progress_metrics
    op.create_index('idx_progress_metrics_session_id', 'progress_metrics', ['session_id'])
    op.create_index('idx_progress_metrics_type', 'progress_metrics', ['metric_type'])
    op.create_index('idx_progress_metrics_measurement_time', 'progress_metrics', ['measurement_time'])
    op.create_index('idx_progress_metrics_composite', 'progress_metrics', ['session_id', 'metric_type', 'measurement_time'])


def downgrade():
    """Drop progress tracking tables."""
    
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('progress_metrics')
    op.drop_table('progress_recovery')
    op.drop_table('progress_updates')
    op.drop_table('progress_sessions')