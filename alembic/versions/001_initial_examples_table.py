"""Initial examples table

Revision ID: 001
Revises: 
Create Date: 2024-11-10 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create examples table with legacy_id for demonstration purposes."""
    op.create_table(
        'examples',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('legacy_id', sa.String(length=100), nullable=True),  # For migration example 004
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_examples_name'), 'examples', ['name'], unique=False)


def downgrade() -> None:
    """Drop examples table."""
    op.drop_index(op.f('ix_examples_name'), table_name='examples')
    op.drop_table('examples')
