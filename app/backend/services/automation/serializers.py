"""Serialization helpers for backup automation models.

These helpers convert SQLAlchemy models into JSON-friendly dictionaries for API
responses.
"""

from __future__ import annotations

from typing import Any, Dict

from models.sql.backup_automation import BackupDestination, BackupSchedule, BackupTarget


def target_to_dict(target: BackupTarget) -> Dict[str, Any]:
    """Convert a BackupTarget to a JSON-friendly dict.

    Args:
        target: Target model.

    Returns:
        Dict[str, Any]: Serialized target.
    """

    return {
        "id": target.id,
        "name": target.name,
        "db_type": target.db_type,
        "config": target.config or {},
        "is_active": bool(target.is_active),
        "secrets_present": bool(target.config_encrypted),
        "created_at": target.created_at.isoformat() if target.created_at else None,
        "updated_at": target.updated_at.isoformat() if target.updated_at else None,
    }


def destination_to_dict(dest: BackupDestination) -> Dict[str, Any]:
    """Convert a BackupDestination to a JSON-friendly dict.

    Args:
        dest: Destination model.

    Returns:
        Dict[str, Any]: Serialized destination.
    """

    return {
        "id": dest.id,
        "name": dest.name,
        "destination_type": dest.destination_type,
        "config": dest.config or {},
        "is_active": bool(dest.is_active),
        "secrets_present": bool(dest.config_encrypted),
        "created_at": dest.created_at.isoformat() if dest.created_at else None,
        "updated_at": dest.updated_at.isoformat() if dest.updated_at else None,
    }


async def schedule_to_dict(session, schedule: BackupSchedule) -> Dict[str, Any]:
    """Convert a BackupSchedule to a JSON-friendly dict.

    Args:
        session: SQLAlchemy async session.
        schedule: Schedule model.

    Returns:
        Dict[str, Any]: Serialized schedule.
    """

    target = await session.get(BackupTarget, schedule.target_id)
    await session.refresh(schedule, attribute_names=["destinations"])

    retention = dict(schedule.retention or {})
    retention.pop("encrypt_password", None)
    retention.pop("encrypt_password_encrypted", None)

    return {
        "id": schedule.id,
        "name": schedule.name,
        "target_id": schedule.target_id,
        "target_name": target.name if target else None,
        "enabled": bool(schedule.enabled),
        "interval_seconds": int(schedule.interval_seconds),
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "retention": retention,
        "destination_ids": [d.id for d in schedule.destinations],
        "destinations": [
            {"id": d.id, "name": d.name, "destination_type": d.destination_type}
            for d in schedule.destinations
        ],
        "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
    }
