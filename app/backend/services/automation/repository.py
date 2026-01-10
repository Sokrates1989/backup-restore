"""Database access layer for backup automation.

This module provides CRUD helpers for the backup automation SQL tables.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from models.sql.backup_automation import BackupDestination, BackupSchedule, BackupTarget


class AutomationRepository:
    """Repository for backup automation models."""

    async def list_targets(self, session) -> List[BackupTarget]:
        """List targets.

        Args:
            session: SQLAlchemy async session.

        Returns:
            List[BackupTarget]: Targets.
        """

        result = await session.execute(select(BackupTarget).order_by(BackupTarget.created_at.desc()))
        return list(result.scalars().all())

    async def get_target(self, session, target_id: str) -> Optional[BackupTarget]:
        """Get a target by id."""

        return await session.get(BackupTarget, target_id)

    async def create_target(self, session, *, name: str, db_type: str, config: Dict[str, Any], config_encrypted: Optional[str]) -> BackupTarget:
        """Create a target."""

        target = BackupTarget(
            id=str(uuid.uuid4()),
            name=name,
            db_type=db_type,
            config=config or {},
            config_encrypted=config_encrypted,
            is_active=True,
        )
        session.add(target)
        await session.commit()
        await session.refresh(target)
        return target

    async def update_target(
        self,
        session,
        target: BackupTarget,
        *,
        name: Optional[str] = None,
        db_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        config_encrypted: Optional[str] = None,
        is_active: Optional[bool] = None,
        secrets_provided: bool = False,
    ) -> BackupTarget:
        """Update a target."""

        if name is not None:
            target.name = name
        if db_type is not None:
            target.db_type = db_type
        if config is not None:
            target.config = config
        if is_active is not None:
            target.is_active = is_active
        if secrets_provided:
            target.config_encrypted = config_encrypted

        await session.commit()
        await session.refresh(target)
        return target

    async def delete_target(self, session, target: BackupTarget) -> None:
        """Delete a target."""

        await session.delete(target)
        await session.commit()

    async def list_destinations(self, session) -> List[BackupDestination]:
        """List destinations."""

        result = await session.execute(select(BackupDestination).order_by(BackupDestination.created_at.desc()))
        return list(result.scalars().all())

    async def get_destination(self, session, destination_id: str) -> Optional[BackupDestination]:
        """Get a destination by id."""

        return await session.get(BackupDestination, destination_id)

    async def create_destination(
        self,
        session,
        *,
        name: str,
        destination_type: str,
        config: Dict[str, Any],
        config_encrypted: Optional[str],
    ) -> BackupDestination:
        """Create a destination."""

        dest = BackupDestination(
            id=str(uuid.uuid4()),
            name=name,
            destination_type=destination_type,
            config=config or {},
            config_encrypted=config_encrypted,
            is_active=True,
        )
        session.add(dest)
        await session.commit()
        await session.refresh(dest)
        return dest

    async def update_destination(
        self,
        session,
        dest: BackupDestination,
        *,
        name: Optional[str] = None,
        destination_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        config_encrypted: Optional[str] = None,
        is_active: Optional[bool] = None,
        secrets_provided: bool = False,
    ) -> BackupDestination:
        """Update a destination."""

        if name is not None:
            dest.name = name
        if destination_type is not None:
            dest.destination_type = destination_type
        if config is not None:
            dest.config = config
        if is_active is not None:
            dest.is_active = is_active
        if secrets_provided:
            dest.config_encrypted = config_encrypted

        await session.commit()
        await session.refresh(dest)
        return dest

    async def delete_destination(self, session, dest: BackupDestination) -> None:
        """Delete a destination."""

        await session.delete(dest)
        await session.commit()

    async def list_schedules(self, session) -> List[BackupSchedule]:
        """List schedules."""

        result = await session.execute(select(BackupSchedule).order_by(BackupSchedule.created_at.desc()))
        return list(result.scalars().all())

    async def get_schedule(self, session, schedule_id: str) -> Optional[BackupSchedule]:
        """Get a schedule by id."""

        return await session.get(BackupSchedule, schedule_id)

    async def create_schedule(
        self,
        session,
        *,
        name: str,
        target_id: str,
        destinations: List[BackupDestination],
        interval_seconds: int,
        retention: Dict[str, Any],
        enabled: bool,
    ) -> BackupSchedule:
        """Create a schedule and attach destinations."""

        schedule = BackupSchedule(
            id=str(uuid.uuid4()),
            name=name,
            target_id=target_id,
            enabled=enabled,
            interval_seconds=interval_seconds,
            next_run_at=datetime.now(timezone.utc) if enabled else None,
            retention=retention or {},
        )
        schedule.destinations = destinations
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
        return schedule

    async def update_schedule(
        self,
        session,
        schedule: BackupSchedule,
        *,
        name: Optional[str] = None,
        target_id: Optional[str] = None,
        destinations: Optional[List[BackupDestination]] = None,
        interval_seconds: Optional[int] = None,
        retention: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> BackupSchedule:
        """Update a schedule."""

        if name is not None:
            schedule.name = name
        if target_id is not None:
            schedule.target_id = target_id
        if interval_seconds is not None:
            schedule.interval_seconds = interval_seconds
        if retention is not None:
            schedule.retention = retention
        if enabled is not None:
            schedule.enabled = enabled
            if enabled and schedule.next_run_at is None:
                schedule.next_run_at = datetime.now(timezone.utc)

        if destinations is not None:
            schedule.destinations = destinations

        await session.commit()
        await session.refresh(schedule)
        return schedule

    async def delete_schedule(self, session, schedule: BackupSchedule) -> None:
        """Delete a schedule."""

        await session.delete(schedule)
        await session.commit()
