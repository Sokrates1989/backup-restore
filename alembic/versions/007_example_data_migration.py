"""Example: Data migration - assign default category

This is a REFERENCE migration showing how to migrate existing data.
DO NOT run this migration - it's for learning purposes only.

Revision ID: 007_example
Revises: 006_example
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_example'
down_revision = '006_example'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migrate existing examples to a default category.
    
    This demonstrates:
    - Creating default data
    - Updating existing records
    - Handling data migration
    - Using raw SQL in migrations
    
    Use case: After adding category relationship, assign all
    existing examples without a category to a default "General" category.
    """
    # Step 1: Create default category (if it doesn't exist)
    op.execute("""
        INSERT INTO categories (id, name, description, created_at)
        VALUES (
            'default-general-category',
            'General',
            'Default category for uncategorized examples',
            NOW()
        )
        ON CONFLICT (name) DO NOTHING
    """)
    
    # Step 2: Assign all examples without category to the default category
    op.execute("""
        UPDATE examples
        SET category_id = 'default-general-category'
        WHERE category_id IS NULL
    """)
    
    # Optional Step 3: Make category_id required (non-nullable)
    # Uncomment if you want to enforce categories
    # op.alter_column('examples', 'category_id', nullable=False)


def downgrade() -> None:
    """
    Revert data migration.
    
    Note: This removes the category assignments but keeps the data.
    """
    # Step 1: Remove category assignments
    op.execute("""
        UPDATE examples
        SET category_id = NULL
        WHERE category_id = 'default-general-category'
    """)
    
    # Step 2: Optionally delete the default category
    # (Only if no other examples use it)
    op.execute("""
        DELETE FROM categories
        WHERE id = 'default-general-category'
        AND NOT EXISTS (
            SELECT 1 FROM examples
            WHERE category_id = 'default-general-category'
        )
    """)
