"""Example: Add priority column to examples

This is a REFERENCE migration showing how to add a column.
DO NOT run this migration - it's for learning purposes only.

Revision ID: 003_example
Revises: 002_example
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_example'
down_revision = '002_example'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add priority column to examples table.
    
    This demonstrates:
    - Adding a new column
    - Setting a default value
    - Making it non-nullable with server_default
    """
    op.add_column(
        'examples',
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0')
    )
    # Note: server_default ensures existing rows get the default value


def downgrade() -> None:
    """
    Remove priority column.
    
    Warning: This will lose all priority data!
    """
    op.drop_column('examples', 'priority')
