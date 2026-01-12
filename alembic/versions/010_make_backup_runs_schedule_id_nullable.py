"""Make backup_runs.schedule_id nullable.

Revision ID: 010_backup_runs_schedid_null
Revises: 009_backup_automation_tables
Create Date: 2026-01-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "010_backup_runs_schedid_null"
down_revision = "009_backup_automation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow immediate backups by making schedule_id nullable."""

    with op.batch_alter_table("backup_runs") as batch_op:
        batch_op.alter_column("schedule_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    """Revert schedule_id to NOT NULL.

    Note:
        Immediate backup runs stored with schedule_id=NULL will be deleted.
    """

    op.execute(sa.text("DELETE FROM backup_runs WHERE schedule_id IS NULL"))

    with op.batch_alter_table("backup_runs") as batch_op:
        batch_op.alter_column("schedule_id", existing_type=sa.String(), nullable=False)
