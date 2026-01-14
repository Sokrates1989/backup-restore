"""Create audit_events table.

Revision ID: 011_create_audit_events
Revises: 010_backup_runs_schedid_null
Create Date: 2026-01-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "011_create_audit_events"
down_revision = "010_backup_runs_schedid_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_events table for unified history/audit logging."""

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'success'")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("target_name", sa.String(length=255), nullable=True),
        sa.Column("destination_id", sa.String(), nullable=True),
        sa.Column("destination_name", sa.String(length=255), nullable=True),
        sa.Column("schedule_id", sa.String(), nullable=True),
        sa.Column("schedule_name", sa.String(length=255), nullable=True),
        sa.Column("backup_id", sa.String(length=1024), nullable=True),
        sa.Column("backup_name", sa.String(length=1024), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_audit_events_operation"), "audit_events", ["operation"], unique=False)
    op.create_index(op.f("ix_audit_events_trigger"), "audit_events", ["trigger"], unique=False)
    op.create_index(op.f("ix_audit_events_status"), "audit_events", ["status"], unique=False)
    op.create_index(op.f("ix_audit_events_started_at"), "audit_events", ["started_at"], unique=False)
    op.create_index(op.f("ix_audit_events_target_id"), "audit_events", ["target_id"], unique=False)
    op.create_index(op.f("ix_audit_events_destination_id"), "audit_events", ["destination_id"], unique=False)
    op.create_index(op.f("ix_audit_events_schedule_id"), "audit_events", ["schedule_id"], unique=False)
    op.create_index(op.f("ix_audit_events_run_id"), "audit_events", ["run_id"], unique=False)


def downgrade() -> None:
    """Drop audit_events table."""

    op.drop_index(op.f("ix_audit_events_run_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_schedule_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_destination_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_target_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_started_at"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_status"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_trigger"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_operation"), table_name="audit_events")
    op.drop_table("audit_events")
