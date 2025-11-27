"""Example: Add N:M relationship (examples and tags)

This is a REFERENCE migration showing how to create an N:M relationship.
DO NOT run this migration - it's for learning purposes only.

Revision ID: 006_example
Revises: 005_example
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_example'
down_revision = '005_example'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create tags table and N:M relationship with examples.
    
    This demonstrates:
    - Creating a new table (tags)
    - Creating an association table (example_tags)
    - Setting up N:M relationship
    - Cascade deletes
    
    Relationship: Many Examples have Many Tags
    """
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=False)
    
    # Create association table for N:M relationship
    # This table has no model - it's just for the relationship
    op.create_table(
        'example_tags',
        sa.Column('example_id', sa.String(), nullable=False),
        sa.Column('tag_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ['example_id'],
            ['examples.id'],
            ondelete='CASCADE'  # Delete association when example is deleted
        ),
        sa.ForeignKeyConstraint(
            ['tag_id'],
            ['tags.id'],
            ondelete='CASCADE'  # Delete association when tag is deleted
        ),
        sa.PrimaryKeyConstraint('example_id', 'tag_id')  # Composite primary key
    )


def downgrade() -> None:
    """
    Remove tags and N:M relationship.
    
    This removes:
    - The association table
    - The tags table
    """
    op.drop_table('example_tags')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_table('tags')
