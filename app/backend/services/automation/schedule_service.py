"""Schedule CRUD and execution service for backup automation."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import ConfigEncryptionError, encrypt_secrets, is_config_encryption_enabled
from backend.services.automation.executor import ScheduleExecutor
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import schedule_to_dict
from models.sql.backup_automation import AuditEvent


def _prepare_schedule_retention_for_storage(
    *,
    existing_retention: Optional[Dict[str, Any]],
    incoming_retention: Dict[str, Any],
) -> Dict[str, Any]:
    """Prepare schedule retention settings for safe storage.

    The schedules table stores the full retention payload as JSON.
    When schedule encryption is enabled, the encryption password must never be
    stored in plaintext. Instead, the password is encrypted-at-rest using the
    application's CONFIG_ENCRYPTION_KEY (Fernet-based) and stored under
    `encrypt_password_encrypted`.

    Args:
        existing_retention: Existing stored retention payload (if any).
        incoming_retention: New retention payload requested by the client.

    Returns:
        Dict[str, Any]: Sanitized retention payload to persist.

    Raises:
        ValueError: When encryption is enabled but no password can be resolved.
        ValueError: When encryption is enabled but CONFIG_ENCRYPTION_KEY is not configured.
    """

    existing = existing_retention or {}
    retention = dict(incoming_retention or {})

    encrypt_enabled = bool(retention.get("encrypt"))
    if not encrypt_enabled:
        retention.pop("encrypt_password", None)
        retention.pop("encrypt_password_encrypted", None)
        return retention

    if not is_config_encryption_enabled():
        raise ValueError(
            "Schedule encryption requires CONFIG_ENCRYPTION_KEY to be configured to store encryption passwords securely."
        )

    password = str(retention.get("encrypt_password") or "").strip()
    if password:
        try:
            token = encrypt_secrets({"encrypt_password": password})
        except ConfigEncryptionError as exc:
            raise ValueError(str(exc)) from exc
        retention["encrypt_password_encrypted"] = token
    else:
        existing_token = str(existing.get("encrypt_password_encrypted") or "").strip()
        if existing_token:
            retention["encrypt_password_encrypted"] = existing_token
        else:
            raise ValueError("Encryption password is required when enabling backup encryption")

    retention.pop("encrypt_password", None)
    return retention


class ScheduleService:
    """Service for managing backup schedules and executing them."""

    def __init__(self, handler: SQLHandler):
        """Initialize the service.

        Args:
            handler: SQL handler.
        """

        self.handler = handler
        self.repo = AutomationRepository()

    async def list_schedules(self) -> List[Dict[str, Any]]:
        """List schedules."""

        async with self.handler.AsyncSessionLocal() as session:
            items = await self.repo.list_schedules(session)
            return [await schedule_to_dict(session, sched) for sched in items]

    async def create_schedule(
        self,
        *,
        name: str,
        target_id: str,
        destination_ids: List[str],
        interval_seconds: int,
        retention: Dict[str, Any],
        enabled: bool,
    ) -> Dict[str, Any]:
        """Create a schedule."""

        async with self.handler.AsyncSessionLocal() as session:
            target = await self.repo.get_target(session, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")

            destinations = []
            for dest_id in destination_ids:
                dest = await self.repo.get_destination(session, dest_id)
                if not dest:
                    raise ValueError(f"Destination not found: {dest_id}")
                destinations.append(dest)

            prepared_retention = _prepare_schedule_retention_for_storage(
                existing_retention=None,
                incoming_retention=retention or {},
            )

            schedule = await self.repo.create_schedule(
                session,
                name=name,
                target_id=target_id,
                destinations=destinations,
                interval_seconds=interval_seconds,
                retention=prepared_retention,
                enabled=enabled,
            )

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="schedule_create",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        target_id=target.id,
                        target_name=target.name,
                        schedule_id=schedule.id,
                        schedule_name=schedule.name,
                        details={"enabled": schedule.enabled, "interval_seconds": schedule.interval_seconds},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

            return await schedule_to_dict(session, schedule)

    async def update_schedule(
        self,
        schedule_id: str,
        *,
        name: Optional[str] = None,
        target_id: Optional[str] = None,
        destination_ids: Optional[List[str]] = None,
        interval_seconds: Optional[int] = None,
        retention: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a schedule."""

        async with self.handler.AsyncSessionLocal() as session:
            schedule = await self.repo.get_schedule(session, schedule_id)
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")

            before = {
                "name": schedule.name,
                "target_id": schedule.target_id,
                "enabled": schedule.enabled,
                "interval_seconds": schedule.interval_seconds,
            }

            if target_id is not None:
                target = await self.repo.get_target(session, target_id)
                if not target:
                    raise ValueError(f"Target not found: {target_id}")

            destinations = None
            if destination_ids is not None:
                destinations = []
                for dest_id in destination_ids:
                    dest = await self.repo.get_destination(session, dest_id)
                    if not dest:
                        raise ValueError(f"Destination not found: {dest_id}")
                    destinations.append(dest)

            prepared_retention = retention
            if retention is not None:
                prepared_retention = _prepare_schedule_retention_for_storage(
                    existing_retention=schedule.retention or {},
                    incoming_retention=retention or {},
                )

            updated = await self.repo.update_schedule(
                session,
                schedule,
                name=name,
                target_id=target_id,
                destinations=destinations,
                interval_seconds=interval_seconds,
                retention=prepared_retention,
                enabled=enabled,
            )

            try:
                now = datetime.now(timezone.utc)
                after = {
                    "name": updated.name,
                    "target_id": updated.target_id,
                    "enabled": updated.enabled,
                    "interval_seconds": updated.interval_seconds,
                }
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="schedule_update",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        schedule_id=updated.id,
                        schedule_name=updated.name,
                        target_id=updated.target_id,
                        details={"before": before, "after": after},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

            return await schedule_to_dict(session, updated)

    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""

        async with self.handler.AsyncSessionLocal() as session:
            schedule = await self.repo.get_schedule(session, schedule_id)
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")

            sched_name = schedule.name
            target_id = schedule.target_id
            await self.repo.delete_schedule(session, schedule)

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="schedule_delete",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        schedule_id=schedule_id,
                        schedule_name=sched_name,
                        target_id=target_id,
                        details={},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

    async def run_now(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule immediately."""

        return await ScheduleExecutor(self.handler).run_now(schedule_id)

    async def run_due(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute due schedules."""

        return await ScheduleExecutor(self.handler).run_due(max_schedules=max_schedules)

    async def run_enabled_now(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute enabled schedules immediately.

        Args:
            max_schedules: Maximum number of schedules to execute.

        Returns:
            Dict[str, Any]: Execution summary.
        """

        return await ScheduleExecutor(self.handler).run_enabled_now(max_schedules=max_schedules)
