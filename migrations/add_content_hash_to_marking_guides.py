"""Add content_hash to marking_guides

Revision ID: add_content_hash_to_marking_guides
Revises: add_training_models
Create Date: 2025-09-03 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_content_hash_to_marking_guides'
down_revision = 'add_training_models'
branch_labels = None
depends_on = None

def upgrade():
    # Add content_hash column to marking_guides table
    op.add_column('marking_guides', 
                 sa.Column('content_hash', sa.String(64), index=True))
    
    # Create an index on the content_hash column
    op.create_index('idx_marking_guides_content_hash', 'marking_guides', ['content_hash'])

def downgrade():
    # Drop the index first
    op.drop_index('idx_marking_guides_content_hash', 'marking_guides')
    
    # Drop the content_hash column
    op.drop_column('marking_guides', 'content_hash')
