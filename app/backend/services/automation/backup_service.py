"""Backup execution service for immediate backup and restore operations.

This module provides the BackupExecutionService class for:
- Performing immediate backups to specified destinations
- Restoring from backups at specified destinations
- Listing available backups at destinations
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import tempfile
import os

from fastapi.concurrency import run_in_threadpool

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import decrypt_secrets
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.storage.google_drive import GoogleDriveConfig, GoogleDriveStorage
from backend.services.automation.storage.sftp import SFTPConfig, SFTPStorage
from backend.services.automation.storage.local import LocalConfig, LocalStorage
from backend.services.automation.target_service import _normalize_local_test_db_address
from backend.services.neo4j.backup_service import Neo4jBackupService
from backend.services.sql.backup_service import BackupService
from models.sql.backup_automation import BackupDestination, BackupRun, BackupTarget


class BackupExecutionService:
    """Service for executing immediate backup and restore operations."""

    def __init__(self, handler: SQLHandler):
        """Initialize the service.

        Args:
            handler: SQL database handler.
        """
        self.handler = handler
        self.repo = AutomationRepository()

    async def backup_now(
        self,
        *,
        target_id: str,
        destination_ids: List[str],
        use_local_storage: bool = False,
    ) -> Dict[str, Any]:
        """Perform an immediate backup of a target to specified destinations.

        Args:
            target_id: ID of the backup target (database).
            destination_ids: List of destination IDs to upload the backup to.
            use_local_storage: If True, store the backup in default local storage (/app/backups)
                and ignore destination_ids.

        Returns:
            Dict with run_id, status, backup_filename, and uploads list.

        Raises:
            ValueError: If target or destinations not found.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        async with self.handler.AsyncSessionLocal() as session:
            target = await session.get(BackupTarget, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")

            destinations: List[BackupDestination] = []
            if not use_local_storage:
                if not destination_ids:
                    raise ValueError("No destinations provided")

                for dest_id in destination_ids:
                    dest = await session.get(BackupDestination, dest_id)
                    if not dest:
                        raise ValueError(f"Destination not found: {dest_id}")
                    destinations.append(dest)

            # Create run record
            run = BackupRun(
                id=run_id,
                schedule_id=None,  # No schedule for immediate backups
                status="started",
                started_at=started_at,
                details={"type": "immediate", "target_id": target_id},
            )
            session.add(run)
            await session.commit()

        temp_path: Optional[Path] = None

        try:
            # Create backup file
            filename, temp_path = await self._create_backup_file(target)
            backup_filename = f"manual-{target.name}-{filename}"

            uploads: List[Dict[str, Any]] = []

            if use_local_storage:
                provider = LocalStorage(LocalConfig(base_path="/app/backups"))
                uploaded = await run_in_threadpool(
                    provider.upload_backup,
                    local_path=temp_path,
                    dest_name=backup_filename,
                )
                uploads.append(
                    {
                        "destination_id": "local",
                        "destination_name": "Local Storage",
                        "backup_id": uploaded.id,
                        "backup_name": uploaded.name,
                        "size": uploaded.size,
                        "created_at": uploaded.created_at.isoformat(),
                    }
                )
            else:
                for dest in destinations:
                    provider = self._build_provider(dest)

                    # Use subfolder per database (remote destinations)
                    subfolder = self._sanitize_name(target.name)
                    dest_filename = f"{subfolder}/{backup_filename}"

                    uploaded = await run_in_threadpool(
                        provider.upload_backup,
                        local_path=temp_path,
                        dest_name=dest_filename,
                    )
                    uploads.append(
                        {
                            "destination_id": dest.id,
                            "destination_name": dest.name,
                            "backup_id": uploaded.id if hasattr(uploaded, "id") else dest_filename,
                            "backup_name": uploaded.name if hasattr(uploaded, "name") else dest_filename,
                            "size": uploaded.size if hasattr(uploaded, "size") else 0,
                            "created_at": uploaded.created_at.isoformat() if hasattr(uploaded, "created_at") else started_at.isoformat(),
                        }
                    )

            finished_at = datetime.now(timezone.utc)

            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                if run:
                    run.status = "success"
                    run.finished_at = finished_at
                    run.backup_filename = backup_filename
                    run.details = {"type": "immediate", "uploads": uploads}
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
                if run:
                    run.status = "failed"
                    run.finished_at = finished_at
                    run.error_message = str(exc)
                await session.commit()
            raise ValueError(f"Backup failed: {exc}")
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    async def restore_now(
        self,
        *,
        target_id: str,
        destination_id: Optional[str],
        backup_id: str,
        use_local_storage: bool = False,
    ) -> Dict[str, Any]:
        """Restore a database from a backup file.

        Args:
            target_id: ID of the backup target (database) to restore to.
            destination_id: ID of the destination where the backup is stored.
                Required unless use_local_storage=True.
            backup_id: ID or name of the backup file to restore.
            use_local_storage: If True, restore from default local storage (/app/backups) and
                ignore destination_id.

        Returns:
            Dict with status, message, and details.

        Raises:
            ValueError: If target, destination, or backup not found.
        """
        async with self.handler.AsyncSessionLocal() as session:
            target = await session.get(BackupTarget, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")

            dest: Optional[BackupDestination] = None
            if not use_local_storage:
                if not destination_id:
                    raise ValueError("destination_id is required unless use_local_storage=true")

                dest = await session.get(BackupDestination, destination_id)
                if not dest:
                    raise ValueError(f"Destination not found: {destination_id}")

        temp_path: Optional[Path] = None

        try:
            if use_local_storage:
                provider = LocalStorage(LocalConfig(base_path="/app/backups"))
            else:
                provider = self._build_provider(dest)

            suffix = Path(str(backup_id)).suffix or ".backup"
            fd, tmp_name = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            temp_path = Path(tmp_name)

            # Download backup to temp file
            temp_path = await run_in_threadpool(
                provider.download_backup,
                backup_id=backup_id,
                dest_path=temp_path,
            )

            # Restore the backup
            await self._restore_backup_file(target, temp_path)

            return {
                "status": "success",
                "message": f"Successfully restored {target.name} from backup",
                "details": {
                    "target_id": target_id,
                    "destination_id": destination_id if not use_local_storage else "local",
                    "backup_id": backup_id,
                },
            }

        except Exception as exc:
            raise ValueError(f"Restore failed: {exc}")
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    async def list_backups(
        self,
        *,
        destination_id: str,
        target_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available backups at a destination.

        Args:
            destination_id: ID of the destination to list backups from.
            target_id: Optional target ID to filter backups by database.

        Returns:
            List of backup file information dictionaries.

        Raises:
            ValueError: If destination not found.
        """
        async with self.handler.AsyncSessionLocal() as session:
            dest = await session.get(BackupDestination, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")

            target_name = None
            if target_id:
                target = await session.get(BackupTarget, target_id)
                if target:
                    target_name = self._sanitize_name(target.name)

        try:
            provider = self._build_provider(dest)

            # List backups, optionally filtered by target subfolder
            prefix = f"{target_name}/" if target_name else ""
            backups = await run_in_threadpool(provider.list_backups, prefix=prefix)

            return [
                {
                    "id": b.id if hasattr(b, 'id') else b.name,
                    "name": b.name,
                    "size": b.size if hasattr(b, 'size') else 0,
                    "created_at": b.created_at.isoformat() if hasattr(b, 'created_at') else None,
                }
                for b in backups
            ]

        except Exception as exc:
            raise ValueError(f"Failed to list backups: {exc}")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as a folder/file name.

        Args:
            name: Original name.

        Returns:
            Sanitized name safe for filesystem use.
        """
        import re
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^\w\-]', '_', name)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_').lower()

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

    async def _restore_backup_file(self, target: BackupTarget, backup_path: Path) -> None:
        """Restore a backup file to the given target.

        Args:
            target: Backup target.
            backup_path: Path to the backup file.

        Raises:
            ValueError: When the target db_type is unsupported or restore fails.
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
            await run_in_threadpool(
                service.restore_from_file,
                neo4j_url=neo4j_url,
                db_user=db_user,
                db_password=db_password,
                backup_path=backup_path,
            )
            return

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
            await run_in_threadpool(
                service.restore_from_file,
                db_type=db_type,
                db_host=raw_host,
                db_port=raw_port,
                db_name=str(cfg.get("database", cfg.get("db_name", ""))),
                db_user=str(cfg.get("user", cfg.get("db_user", ""))),
                db_password=str(secrets.get("password", secrets.get("db_password", ""))),
                backup_path=backup_path,
            )
            return

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
            local_cfg = LocalConfig(
                base_path=str(cfg.get("path", "/app/backups")),
            )
            return LocalStorage(local_cfg)

        if destination.destination_type == "sftp":
            sftp_cfg = SFTPConfig(
                host=str(cfg.get("host", "")),
                port=int(cfg.get("port", 22)),
                username=str(cfg.get("username", "")),
                base_path=str(cfg.get("path", "/backups")),
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
