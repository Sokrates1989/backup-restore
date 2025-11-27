"""Example: Add 1:N relationship (examples belong to categories)

This is a REFERENCE migration showing how to create a 1:N relationship.
DO NOT run this migration - it's for learning purposes only.

Revision ID: 005_example
Revises: 004_example
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_example'
down_revision = '004_example'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add category_id foreign key to examples table.
    
    This demonstrates:
    - Creating a 1:N relationship
    - Adding a foreign key constraint
    - Setting ondelete behavior
    - Creating an index for performance
    
    Relationship: One Category has Many Examples
    """
    # Add the foreign key column
    op.add_column(
        'examples',
        sa.Column('category_id', sa.String(), nullable=True)
    )
    
    # Create the foreign key constraint
    op.create_foreign_key(
        'fk_examples_category_id',  # Constraint name
        'examples',                  # Source table
        'categories',                # Target table
        ['category_id'],             # Source column
        ['id'],                      # Target column
        ondelete='SET NULL'          # What to do when category is deleted
    )
    
    # Create index for faster lookups
    op.create_index(
        op.f('ix_examples_category_id'),
        'examples',
        ['category_id'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove category relationship.
    
    This removes:
    - The index
    - The foreign key constraint
    - The category_id column
    """
    op.drop_index(op.f('ix_examples_category_id'), table_name='examples')
    op.drop_constraint('fk_examples_category_id', 'examples', type_='foreignkey')
    op.drop_column('examples', 'category_id')
