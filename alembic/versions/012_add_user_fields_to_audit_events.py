"""Add user_id and user_name columns to audit_events table.

Revision ID: 012_user_fields_audit_events
Revises: 011_create_audit_events
Create Date: 2026-01-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012_user_fields_audit_events"
down_revision = "011_create_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id and user_name columns to audit_events table for user attribution."""

    # Add user_id column
    op.add_column(
        "audit_events",
        sa.Column("user_id", sa.String(), nullable=True)
    )
    
    # Add user_name column
    op.add_column(
        "audit_events",
        sa.Column("user_name", sa.String(), nullable=True)
    )
    
    # Create indexes for user fields
    op.create_index(op.f("ix_audit_events_user_id"), "audit_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_events_user_name"), "audit_events", ["user_name"], unique=False)


def downgrade() -> None:
    """Remove user_id and user_name columns from audit_events table."""

    # Drop indexes
    op.drop_index(op.f("ix_audit_events_user_name"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_user_id"), table_name="audit_events")
    
    # Drop columns
    op.drop_column("audit_events", "user_name")
    op.drop_column("audit_events", "user_id")
