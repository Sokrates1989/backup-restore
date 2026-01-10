"""Create backup automation tables.

Revision ID: 009_backup_automation_tables
Revises: 008_create_users_table
Create Date: 2026-01-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "009_backup_automation_tables"
down_revision = "008_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables for backup targets, destinations, schedules, and run history."""

    op.create_table(
        "backup_targets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("db_type", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("config_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_backup_targets_name"), "backup_targets", ["name"], unique=True)

    op.create_table(
        "backup_destinations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("destination_type", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("config_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_backup_destinations_name"), "backup_destinations", ["name"], unique=True)

    op.create_table(
        "backup_schedules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default=sa.text("86400")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["target_id"], ["backup_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_backup_schedules_name"), "backup_schedules", ["name"], unique=True)
    op.create_index(op.f("ix_backup_schedules_target_id"), "backup_schedules", ["target_id"], unique=False)

    op.create_table(
        "backup_schedule_destinations",
        sa.Column("schedule_id", sa.String(), nullable=False),
        sa.Column("destination_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["backup_schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["destination_id"], ["backup_destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("schedule_id", "destination_id"),
    )

    op.create_table(
        "backup_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("schedule_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'started'")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backup_filename", sa.String(length=512), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["schedule_id"], ["backup_schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backup_runs_schedule_id"), "backup_runs", ["schedule_id"], unique=False)


def downgrade() -> None:
    """Drop backup automation tables."""

    op.drop_index(op.f("ix_backup_runs_schedule_id"), table_name="backup_runs")
    op.drop_table("backup_runs")

    op.drop_table("backup_schedule_destinations")

    op.drop_index(op.f("ix_backup_schedules_target_id"), table_name="backup_schedules")
    op.drop_index(op.f("ix_backup_schedules_name"), table_name="backup_schedules")
    op.drop_table("backup_schedules")

    op.drop_index(op.f("ix_backup_destinations_name"), table_name="backup_destinations")
    op.drop_table("backup_destinations")

    op.drop_index(op.f("ix_backup_targets_name"), table_name="backup_targets")
    op.drop_table("backup_targets")
