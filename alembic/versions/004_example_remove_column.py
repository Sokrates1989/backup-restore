"""Example: Remove legacy_id column from examples

This is a REFERENCE migration showing how to remove a column.
DO NOT run this migration - it's for learning purposes only.

Scenario: You added a 'legacy_id' column during migration from an old system,
but now that migration is complete and the column is no longer needed.

Revision ID: 004_example
Revises: 003_example
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_example'
down_revision = '003_example'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Remove legacy_id column from examples table.
    
    This demonstrates:
    - Removing an unnecessary column
    - Safe removal (doesn't break existing functionality)
    - Warning: Data will be lost!
    
    Use case: After migrating from old system, legacy_id is no longer needed.
    """
    op.drop_column('examples', 'legacy_id')


def downgrade() -> None:
    """
    Restore legacy_id column.
    
    Note: Data cannot be recovered after upgrade!
    The column will be recreated but empty.
    """
    op.add_column(
        'examples',
        sa.Column('legacy_id', sa.String(length=100), nullable=True)
    )
