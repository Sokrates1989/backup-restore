"""Example: Add categories table

This is a REFERENCE migration showing how to create a new table.
DO NOT run this migration - it's for learning purposes only.

To use this as a template:
1. Copy this file
2. Update the revision IDs
3. Modify the table structure for your needs
4. Run: alembic upgrade head

Revision ID: 002_example
Revises: 001
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_example'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create categories table.
    
    This demonstrates:
    - Creating a new table
    - Adding indexes
    - Setting up constraints
    """
    op.create_table(
        'categories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=False)


def downgrade() -> None:
    """
    Drop categories table.
    
    Always implement downgrade to allow rollback!
    """
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_table('categories')
