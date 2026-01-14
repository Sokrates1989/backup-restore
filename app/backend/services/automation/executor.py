"""Execution engine for backup automation.

This module contains the orchestration to:
- Execute a schedule (create backup file, upload to destinations, apply retention)
- Execute all due schedules (runner mode)
- Persist run history in the SQL database
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import re

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from backend.database.sql_handler import SQLHandler
from backend.services.automation.backup_file_crypto import BackupEncryptionError, encrypt_file
from backend.services.automation.config_crypto import decrypt_secrets
from backend.services.automation.retention import plan_retention, retention_from_dict
from backend.services.automation.schedule_timing import compute_next_run_at
from backend.services.automation.notification_service import get_notification_service
from backend.services.automation.storage.factory import build_storage_provider
from backend.services.automation.target_service import _normalize_local_test_db_address
from backend.services.neo4j.backup_service import Neo4jBackupService
from backend.services.sql.backup_service import BackupService
from models.sql.backup_automation import AuditEvent, BackupDestination, BackupRun, BackupSchedule, BackupTarget


def _resolve_schedule_encryption_password(*, retention: Dict[str, Any]) -> str:
    """Resolve the schedule encryption password from stored retention settings.

    Args:
        retention: Schedule retention payload.

    Returns:
        str: Encryption password.

    Raises:
        ValueError: When the schedule is configured for encryption but no password is available.
    """

    if not isinstance(retention, dict) or not retention.get("encrypt"):
        return ""

    token = str(retention.get("encrypt_password_encrypted") or "").strip()
    if not token:
        raise ValueError("Schedule encryption is enabled but no encryption password is configured")

    try:
        decrypted = decrypt_secrets(token)
    except Exception as exc:
        raise ValueError(f"Failed to decrypt schedule encryption password: {exc}") from exc

    password = str(decrypted.get("encrypt_password") or "").strip()
    if not password:
        raise ValueError("Schedule encryption is enabled but encryption password is empty")

    return password


def _encrypt_backup_to_temp(*, input_path: Path, password: str) -> Path:
    """Encrypt a backup artifact to a temporary file.

    Args:
        input_path: Path to the plaintext backup file.
        password: Encryption password.

    Returns:
        Path: Path to the encrypted temporary file.

    Raises:
        BackupEncryptionError: When encryption fails.
    """

    import os
    import tempfile

    fd, tmp_name = tempfile.mkstemp(suffix=".enc")
    os.close(fd)
    out_path = Path(tmp_name)
    try:
        encrypt_file(input_path=input_path, output_path=out_path, password=password)
        return out_path
    except Exception:
        try:
            if out_path.exists():
                out_path.unlink()
        except Exception:
            pass
        raise


class ScheduleExecutor:
    """Execute scheduled backups using persisted configuration."""

    def __init__(self, handler: SQLHandler):
        """Initialize the executor.

        Args:
            handler: SQL database handler.
        """

        self.handler = handler

    async def run_now(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule immediately.

        Args:
            schedule_id: Schedule id.

        Returns:
            Dict[str, Any]: Run information.
        """

        return await self._execute_schedule(schedule_id, trigger="manual")

    async def run_due(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute all due schedules.

        Args:
            max_schedules: Maximum schedules to execute.

        Returns:
            Dict[str, Any]: Summary.
        """

        now = datetime.now(timezone.utc)

        async with self.handler.AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackupSchedule)
                .where(BackupSchedule.enabled.is_(True))
                .where((BackupSchedule.next_run_at.is_(None)) | (BackupSchedule.next_run_at <= now))
                .order_by(BackupSchedule.next_run_at.asc().nullsfirst())
                .limit(max_schedules)
            )
            schedules = result.scalars().all()

        executed: List[Dict[str, Any]] = []
        for sched in schedules:
            try:
                run_info = await self._execute_schedule(sched.id, trigger="scheduled")
                executed.append({"schedule_id": sched.id, "status": "success", "run": run_info})
            except Exception as exc:
                executed.append({"schedule_id": sched.id, "status": "failed", "error": str(exc)})

        return {"now": now.isoformat(), "count": len(executed), "results": executed}

    async def run_enabled_now(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute enabled schedules immediately.

        This ignores `next_run_at` and runs schedules that are enabled.

        Args:
            max_schedules: Maximum number of schedules to execute.

        Returns:
            Dict[str, Any]: Summary.
        """

        now = datetime.now(timezone.utc)

        async with self.handler.AsyncSessionLocal() as session:
            result = await session.execute(
                select(BackupSchedule)
                .where(BackupSchedule.enabled.is_(True))
                .order_by(BackupSchedule.created_at.desc())
                .limit(max_schedules)
            )
            schedules = result.scalars().all()

        executed: List[Dict[str, Any]] = []
        for sched in schedules:
            try:
                run_info = await self._execute_schedule(sched.id, trigger="manual")
                executed.append({"schedule_id": sched.id, "status": "success", "run": run_info})
            except Exception as exc:
                executed.append({"schedule_id": sched.id, "status": "failed", "error": str(exc)})

        return {"now": now.isoformat(), "count": len(executed), "results": executed}

    async def _execute_schedule(self, schedule_id: str, *, trigger: str = "scheduled") -> Dict[str, Any]:
        """Execute a schedule and record a BackupRun.

        Args:
            schedule_id: Schedule id.

        Returns:
            Dict[str, Any]: Run information.
        """

        started_at = datetime.now(timezone.utc)
        run_id = str(uuid.uuid4())
        audit_event_id = str(uuid.uuid4())
        audit_event_created = False

        async with self.handler.AsyncSessionLocal() as session:
            schedule = await session.get(BackupSchedule, schedule_id)
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")

            await session.refresh(schedule)
            target = await session.get(BackupTarget, schedule.target_id)
            if not target:
                raise ValueError(f"Target not found: {schedule.target_id}")

            await session.refresh(target)
            await session.refresh(schedule, attribute_names=["destinations"])
            destinations = list(schedule.destinations)

            try:
                session.add(
                    AuditEvent(
                        id=audit_event_id,
                        operation="backup",
                        trigger=trigger,
                        status="started",
                        started_at=started_at,
                        target_id=target.id,
                        target_name=target.name,
                        schedule_id=schedule.id,
                        schedule_name=schedule.name,
                        run_id=run_id,
                        details={},
                    )
                )
                await session.commit()
                audit_event_created = True
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

            run = BackupRun(
                id=run_id,
                schedule_id=schedule.id,
                status="started",
                started_at=started_at,
                details={},
            )
            session.add(run)
            await session.commit()

        temp_path: Optional[Path] = None
        encrypted_path: Optional[Path] = None

        try:
            prefix = f"sched-{schedule_id}-"
            filename, temp_path = await self._create_backup_file(target)
            backup_filename = prefix + filename

            retention_payload = schedule.retention or {}
            upload_source_path = temp_path
            if isinstance(retention_payload, dict) and retention_payload.get("encrypt"):
                password = _resolve_schedule_encryption_password(retention=retention_payload)
                encrypted_path = await run_in_threadpool(_encrypt_backup_to_temp, input_path=temp_path, password=password)
                upload_source_path = encrypted_path
                backup_filename = f"{backup_filename}.enc"

            subfolder = self._sanitize_name(target.name)
            retention_prefix = f"{subfolder}/{prefix}"

            uploads: List[Dict[str, Any]] = []
            retention_actions: List[Dict[str, Any]] = []

            for dest in destinations:
                provider = self._build_provider(dest)

                dest_name = f"{subfolder}/{backup_filename}"
                uploaded = await run_in_threadpool(provider.upload_backup, local_path=upload_source_path, dest_name=dest_name)
                uploads.append(
                    {
                        "destination_id": dest.id,
                        "destination_name": dest.name,
                        "backup_id": uploaded.id,
                        "backup_name": uploaded.name,
                        "size": uploaded.size,
                        "created_at": uploaded.created_at.isoformat(),
                    }
                )

                existing = await run_in_threadpool(provider.list_backups, prefix=retention_prefix)
                keep, delete = plan_retention(existing, retention_from_dict(schedule.retention))
                if delete:
                    retention_event_id = str(uuid.uuid4())
                    retention_event_created = False
                    try:
                        async with self.handler.AsyncSessionLocal() as del_session:
                            try:
                                del_session.add(
                                    AuditEvent(
                                        id=retention_event_id,
                                        operation="delete_backup",
                                        trigger=trigger,
                                        status="started",
                                        started_at=datetime.now(timezone.utc),
                                        target_id=target.id,
                                        target_name=target.name,
                                        schedule_id=schedule.id,
                                        schedule_name=schedule.name,
                                        destination_id=dest.id,
                                        destination_name=dest.name,
                                        run_id=run_id,
                                        details={"count": len(delete), "deleted_names": [b.name for b in delete]},
                                    )
                                )
                                await del_session.commit()
                                retention_event_created = True
                            except Exception:
                                try:
                                    await del_session.rollback()
                                except Exception:
                                    pass

                        await run_in_threadpool(provider.delete_backups, delete)

                        if retention_event_created:
                            async with self.handler.AsyncSessionLocal() as del_session:
                                try:
                                    evt = await del_session.get(AuditEvent, retention_event_id)
                                    if evt:
                                        evt.status = "success"
                                        evt.finished_at = datetime.now(timezone.utc)
                                    await del_session.commit()
                                except Exception:
                                    try:
                                        await del_session.rollback()
                                    except Exception:
                                        pass
                    except Exception as exc:
                        if retention_event_created:
                            async with self.handler.AsyncSessionLocal() as del_session:
                                try:
                                    evt = await del_session.get(AuditEvent, retention_event_id)
                                    if evt:
                                        evt.status = "failed"
                                        evt.finished_at = datetime.now(timezone.utc)
                                        evt.error_message = str(exc)
                                    await del_session.commit()
                                except Exception:
                                    try:
                                        await del_session.rollback()
                                    except Exception:
                                        pass
                        raise

                retention_actions.append(
                    {
                        "destination_id": dest.id,
                        "existing": len(existing),
                        "keep": len(keep),
                        "delete": len(delete),
                        "deleted_names": [b.name for b in delete],
                    }
                )

            finished_at = datetime.now(timezone.utc)

            notification_results: Optional[Dict[str, Any]] = None
            try:
                retention_payload = schedule.retention or {}
                notifications_config = retention_payload.get("notifications") if isinstance(retention_payload, dict) else None
                backup_size_bytes: Optional[int] = None
                try:
                    backup_size_bytes = upload_source_path.stat().st_size if upload_source_path else None
                except OSError:
                    backup_size_bytes = None
                if isinstance(notifications_config, dict) and notifications_config:
                    notification_results = await get_notification_service().send_backup_notification(
                        schedule_name=getattr(schedule, "name", schedule_id),
                        target_name=getattr(target, "name", ""),
                        status="success",
                        backup_filename=backup_filename,
                        uploads=uploads,
                        backup_file_path=upload_source_path,
                        backup_size_bytes=backup_size_bytes,
                        notifications_config=notifications_config,
                    )
            except Exception as exc:
                notification_results = {"sent": False, "error": str(exc)}

            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                schedule = await session.get(BackupSchedule, schedule_id)
                if run:
                    run.status = "success"
                    run.finished_at = finished_at
                    run.backup_filename = backup_filename
                    run.details = {
                        "type": trigger,
                        "schedule_id": schedule_id,
                        "schedule_name": getattr(schedule, "name", None) if schedule else None,
                        "target_id": getattr(schedule, "target_id", None) if schedule else getattr(target, "id", None),
                        "target_name": getattr(target, "name", None),
                        "uploads": uploads,
                        "retention": retention_actions,
                        "notifications": notification_results,
                    }

                if audit_event_created:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "success"
                            evt.finished_at = finished_at
                            evt.backup_name = backup_filename
                            evt.details = {"uploads": uploads, "retention": retention_actions}
                    except Exception:
                        pass

                if schedule:
                    schedule.last_run_at = started_at
                    if trigger == "scheduled":
                        schedule.next_run_at = compute_next_run_at(
                            reference=finished_at,
                            interval_seconds=int(schedule.interval_seconds),
                            retention=schedule.retention or {},
                        )

                await session.commit()

            return {
                "run_id": run_id,
                "status": "success",
                "backup_filename": backup_filename,
                "uploads": uploads,
                "notifications": notification_results,
            }

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)

            notification_results: Optional[Dict[str, Any]] = None
            try:
                if "schedule" in locals() and schedule is not None:
                    retention_payload = schedule.retention or {}
                    notifications_config = retention_payload.get("notifications") if isinstance(retention_payload, dict) else None
                    if isinstance(notifications_config, dict) and notifications_config:
                        notification_results = await get_notification_service().send_backup_notification(
                            schedule_name=getattr(schedule, "name", schedule_id),
                            target_name=getattr(target, "name", ""),
                            status="failed",
                            error_message=str(exc),
                            uploads=uploads if "uploads" in locals() else None,
                            notifications_config=notifications_config,
                        )
            except Exception as notify_exc:
                notification_results = {"sent": False, "error": str(notify_exc)}

            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                schedule = await session.get(BackupSchedule, schedule_id)
                if run:
                    run.status = "failed"
                    run.finished_at = finished_at
                    run.error_message = str(exc)
                    if isinstance(run.details, dict):
                        run.details["notifications"] = notification_results
                    else:
                        run.details = {"notifications": notification_results}

                if audit_event_created:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "failed"
                            evt.finished_at = finished_at
                            evt.error_message = str(exc)
                    except Exception:
                        pass
                if schedule:
                    schedule.last_run_at = started_at
                    if trigger == "scheduled":
                        schedule.next_run_at = compute_next_run_at(
                            reference=finished_at,
                            interval_seconds=int(schedule.interval_seconds),
                            retention=schedule.retention or {},
                        )
                await session.commit()
            raise
        finally:
            for cleanup_path in (encrypted_path, temp_path):
                if cleanup_path and cleanup_path.exists():
                    try:
                        cleanup_path.unlink()
                    except Exception:
                        pass

    async def _create_backup_file(self, target: BackupTarget) -> tuple[str, Path]:
        """Create a backup file for the given target.

        Args:
            target: Backup target.

        Returns:
            tuple[str, Path]: Filename and file path.

        Raises:
            ValueError: When the target db_type is unsupported.
        """

        secrets = decrypt_secrets(target.config_encrypted)
        cfg = target.config or {}

        if target.db_type == "neo4j":
            neo4j_url = str(cfg.get("neo4j_url", cfg.get("host", "")))
            if not neo4j_url.startswith("bolt://") and not neo4j_url.startswith("neo4j://"):
                raw_host = str(neo4j_url)
                raw_port = int(cfg.get("port", 7687) or 7687)
                host, port = _normalize_local_test_db_address(db_type="neo4j", host=raw_host, port=raw_port)
                neo4j_url = f"bolt://{host}:{port}"
            db_user = str(cfg.get("user", cfg.get("db_user", "")))
            db_password = str(secrets.get("password", secrets.get("db_password", "")))

            service = Neo4jBackupService()
            filename, path = await run_in_threadpool(
                service.create_backup_to_temp,
                neo4j_url=neo4j_url,
                db_user=db_user,
                db_password=db_password,
                compress=True,
            )
            return filename, path

        if target.db_type in ["postgresql", "postgres", "mysql", "sqlite"]:
            db_type = target.db_type
            if db_type == "postgres":
                db_type = "postgresql"

            raw_host = str(cfg.get("host", cfg.get("db_host", "")))
            raw_port = int(cfg.get("port", cfg.get("db_port", 0)) or 0)
            if raw_port <= 0 and db_type == "postgresql":
                raw_port = 5432
            if raw_port <= 0 and db_type == "mysql":
                raw_port = 3306
            if raw_port > 0:
                raw_host, raw_port = _normalize_local_test_db_address(db_type=db_type, host=raw_host, port=raw_port)

            service = BackupService()
            filename, path = await run_in_threadpool(
                service.create_backup_to_temp,
                db_type=db_type,
                db_host=raw_host,
                db_port=raw_port,
                db_name=str(cfg.get("database", cfg.get("db_name", ""))),
                db_user=str(cfg.get("user", cfg.get("db_user", ""))),
                db_password=str(secrets.get("password", secrets.get("db_password", ""))),
                compress=True,
            )
            return filename, path

        raise ValueError(f"Unsupported target db_type: {target.db_type}")

    def _build_provider(self, destination: BackupDestination):
        """Instantiate a storage provider from a destination record.

        Args:
            destination: Destination model.

        Returns:
            Storage provider instance.

        Raises:
            ValueError: When destination type is unsupported.
        """

        return build_storage_provider(destination)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as a folder/file name.

        Args:
            name: Original name.

        Returns:
            str: Sanitized name safe for filesystem use.
        """

        sanitized = re.sub(r"[^\w\-]", "_", name)
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized.strip("_").lower()
