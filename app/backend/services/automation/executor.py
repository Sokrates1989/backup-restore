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

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import decrypt_secrets
from backend.services.automation.retention import plan_retention, retention_from_dict
from backend.services.automation.storage.google_drive import GoogleDriveConfig, GoogleDriveStorage
from backend.services.automation.storage.sftp import SFTPConfig, SFTPStorage
from backend.services.automation.storage.local import LocalConfig, LocalStorage
from backend.services.automation.target_service import _normalize_local_test_db_address
from backend.services.neo4j.backup_service import Neo4jBackupService
from backend.services.sql.backup_service import BackupService
from models.sql.backup_automation import BackupDestination, BackupRun, BackupSchedule, BackupTarget


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

        return await self._execute_schedule(schedule_id)

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
                run_info = await self._execute_schedule(sched.id)
                executed.append({"schedule_id": sched.id, "status": "success", "run": run_info})
            except Exception as exc:
                executed.append({"schedule_id": sched.id, "status": "failed", "error": str(exc)})

        return {"now": now.isoformat(), "count": len(executed), "results": executed}

    async def _execute_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule and record a BackupRun.

        Args:
            schedule_id: Schedule id.

        Returns:
            Dict[str, Any]: Run information.
        """

        started_at = datetime.now(timezone.utc)
        run_id = str(uuid.uuid4())

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

        try:
            prefix = f"sched-{schedule_id}-"
            filename, temp_path = await self._create_backup_file(target)
            backup_filename = prefix + filename

            uploads: List[Dict[str, Any]] = []
            retention_actions: List[Dict[str, Any]] = []

            for dest in destinations:
                provider = self._build_provider(dest)
                uploaded = await run_in_threadpool(provider.upload_backup, local_path=temp_path, dest_name=backup_filename)
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

                existing = await run_in_threadpool(provider.list_backups, prefix=prefix)
                keep, delete = plan_retention(existing, retention_from_dict(schedule.retention))
                if delete:
                    await run_in_threadpool(provider.delete_backups, delete)

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

            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                schedule = await session.get(BackupSchedule, schedule_id)
                if run:
                    run.status = "success"
                    run.finished_at = finished_at
                    run.backup_filename = backup_filename
                    run.details = {
                        "uploads": uploads,
                        "retention": retention_actions,
                    }

                if schedule:
                    schedule.last_run_at = started_at
                    schedule.next_run_at = finished_at + timedelta(seconds=int(schedule.interval_seconds))

                await session.commit()

            return {
                "run_id": run_id,
                "status": "success",
                "backup_filename": backup_filename,
                "uploads": uploads,
            }

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                schedule = await session.get(BackupSchedule, schedule_id)
                if run:
                    run.status = "failed"
                    run.finished_at = finished_at
                    run.error_message = str(exc)
                if schedule:
                    schedule.last_run_at = started_at
                    schedule.next_run_at = finished_at + timedelta(seconds=int(schedule.interval_seconds))
                await session.commit()
            raise
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
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

        secrets = decrypt_secrets(destination.config_encrypted)
        cfg = destination.config or {}

        if destination.destination_type == "local":
            local_cfg = LocalConfig(base_path=str(cfg.get("path", "/app/backups")))
            return LocalStorage(local_cfg)

        if destination.destination_type == "sftp":
            sftp_cfg = SFTPConfig(
                host=str(cfg.get("host", "")),
                port=int(cfg.get("port", 22)),
                username=str(cfg.get("username", "")),
                base_path=str(cfg.get("path", cfg.get("base_path", "/backups"))),
                password=secrets.get("password"),
                private_key=secrets.get("private_key"),
                private_key_passphrase=secrets.get("private_key_passphrase"),
            )
            return SFTPStorage(sftp_cfg)

        if destination.destination_type == "google_drive":
            g_cfg = GoogleDriveConfig(
                service_account_json=str(secrets.get("service_account_json", "")),
                folder_id=str(cfg.get("folder_id", "")),
            )
            return GoogleDriveStorage(g_cfg)

        raise ValueError(f"Unsupported destination type: {destination.destination_type}")
