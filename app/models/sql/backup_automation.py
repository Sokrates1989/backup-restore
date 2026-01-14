"""Backup automation configuration models.

This module contains SQLAlchemy ORM models used to persist:
- Backup targets (what to back up)
- Backup destinations (where to upload backups)
- Backup schedules (when to back up)
- Backup runs (execution history)

These models are used by the backup automation API endpoints and the web GUI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.sql.base import Base


backup_schedule_destinations = Table(
    "backup_schedule_destinations",
    Base.metadata,
    Column("schedule_id", String, ForeignKey("backup_schedules.id"), primary_key=True),
    Column("destination_id", String, ForeignKey("backup_destinations.id"), primary_key=True),
)


class BackupTarget(Base):
    """A configured database target that can be backed up.

    Attributes:
        id (str): Primary key UUID.
        name (str): Human-friendly name.
        db_type (str): Database type. Supported: neo4j|postgresql|mysql|sqlite.
        config (dict): Type-specific configuration (host/user/password/etc.).
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Update timestamp.
    """

    __tablename__ = "backup_targets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)

    db_type = Column(String(32), nullable=False)

    # Type-specific configuration. Sensitive values may be stored encrypted in this structure.
    config = Column(JSON, nullable=False, default=dict)

    config_encrypted = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schedules = relationship("BackupSchedule", back_populates="target")


class BackupDestination(Base):
    """A remote destination where backups can be uploaded.

    Attributes:
        id (str): Primary key UUID.
        name (str): Human-friendly name.
        destination_type (str): Destination type. Supported: sftp|google_drive.
        config (dict): Type-specific destination config.
        is_active (bool): Whether destination is active.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Update timestamp.
    """

    __tablename__ = "backup_destinations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)

    destination_type = Column(String(32), nullable=False)

    # Type-specific configuration. Sensitive values may be stored encrypted in this structure.
    config = Column(JSON, nullable=False, default=dict)

    config_encrypted = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schedules = relationship(
        "BackupSchedule",
        secondary=backup_schedule_destinations,
        back_populates="destinations",
    )


class BackupSchedule(Base):
    """A schedule that triggers periodic backups.

    Notes:
        This MVP supports interval-based scheduling. A schedule is considered due
        when `next_run_at <= now`.

    Attributes:
        id (str): Primary key UUID.
        name (str): Human-friendly name.
        target_id (str): FK to BackupTarget.
        enabled (bool): Whether schedule is active.
        interval_seconds (int): How often to run.
        next_run_at (datetime): Next due time (UTC).
        last_run_at (datetime): Last start time.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Update timestamp.
    """

    __tablename__ = "backup_schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)

    target_id = Column(String, ForeignKey("backup_targets.id"), nullable=False, index=True)

    enabled = Column(Boolean, default=True, nullable=False)

    interval_seconds = Column(Integer, nullable=False, default=86400)

    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)

    retention = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    target = relationship("BackupTarget", back_populates="schedules")
    destinations = relationship(
        "BackupDestination",
        secondary=backup_schedule_destinations,
        back_populates="schedules",
    )
    runs = relationship("BackupRun", back_populates="schedule")


class BackupRun(Base):
    """An execution record for a schedule run.

    Attributes:
        id (str): Primary key UUID.
        schedule_id (str): FK to BackupSchedule.
        status (str): started|success|failed.
        started_at (datetime): Run start.
        finished_at (datetime): Run end.
        backup_filename (str): Produced backup filename.
        details (dict): Execution details and per-destination results.
        error_message (str): Error summary if failed.
    """

    __tablename__ = "backup_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    schedule_id = Column(String, ForeignKey("backup_schedules.id"), nullable=True, index=True)

    status = Column(String(32), nullable=False, default="started")

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    backup_filename = Column(String(512), nullable=True)

    details = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)

    schedule = relationship("BackupSchedule", back_populates="runs")


class AuditEvent(Base):
    """Audit event record for important operations.

    This table is intended to provide a unified, filterable history stream
    for actions such as backups, restores, deletions, and configuration
    changes.

    Attributes:
        id (str): Primary key UUID.
        operation (str): Operation type (e.g. backup|restore|delete_backup).
        trigger (str): Trigger type (manual|scheduled|system).
        status (str): started|success|failed.
        started_at (datetime): Event start timestamp.
        finished_at (datetime): Event finish timestamp.
        target_id (str): Optional target id.
        target_name (str): Optional target display name.
        destination_id (str): Optional destination id.
        destination_name (str): Optional destination display name.
        schedule_id (str): Optional schedule id.
        schedule_name (str): Optional schedule name.
        backup_id (str): Optional provider-specific backup identifier.
        backup_name (str): Optional backup filename/path.
        run_id (str): Optional BackupRun id.
        details (dict): Free-form details.
        error_message (str): Error summary when failed.
    """

    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    operation = Column(String(64), nullable=False, index=True)
    trigger = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="success", index=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    target_id = Column(String, nullable=True, index=True)
    target_name = Column(String(255), nullable=True)

    destination_id = Column(String, nullable=True, index=True)
    destination_name = Column(String(255), nullable=True)

    schedule_id = Column(String, nullable=True, index=True)
    schedule_name = Column(String(255), nullable=True)

    backup_id = Column(String(1024), nullable=True)
    backup_name = Column(String(1024), nullable=True)

    run_id = Column(String, nullable=True, index=True)

    details = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)
