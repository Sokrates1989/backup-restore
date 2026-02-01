"""Backup execution service for immediate backup and restore operations.

This module provides the BackupExecutionService class for:
- Performing immediate backups to specified destinations
- Restoring from backups at specified destinations
- Listing available backups at destinations
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional
import uuid
import tempfile
import os

from fastapi.concurrency import run_in_threadpool

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import decrypt_secrets
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.retention import BackupObject
from backend.services.automation.storage.factory import build_storage_provider
from backend.services.automation.storage.local import LocalConfig, LocalStorage
from backend.services.automation.target_service import _normalize_local_test_db_address
from backend.services.automation.backup_file_crypto import (
    BackupEncryptionError,
    decrypt_to_temporary_file,
    encrypt_file,
    is_encrypted_backup_file,
)
from backend.services.automation.restore_validation import (
    allowed_backup_name_extensions_for_db_type,
    is_backup_name_compatible_with_db_type,
    validate_backup_compatibility,
)
from backend.services.neo4j.backup_service import Neo4jBackupService
from backend.services.sql.backup_service import BackupService
from models.sql.backup_automation import AuditEvent, BackupDestination, BackupRun, BackupTarget
from api.logging_config import get_logger

logger = get_logger(__name__)


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
        encryption_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform an immediate backup of a target to specified destinations.

        Args:
            target_id: ID of the backup target (database).
            destination_ids: List of destination IDs to upload the backup to.
            use_local_storage: If True, store the backup in default local storage (/app/backups)
                and ignore destination_ids.
            encryption_password: Optional password to encrypt the backup before upload.

        Returns:
            Dict with run_id, status, backup_filename, and uploads list.

        Raises:
            ValueError: If target or destinations not found.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        audit_event_id = str(uuid.uuid4())
        audit_event_created = False

        password = str(encryption_password or "").strip()

        logger.info(
            "Starting manual backup (target_id=%s, destinations=%s, use_local_storage=%s, encrypted=%s)",
            target_id,
            destination_ids,
            use_local_storage,
            bool(password),
        )

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

            audit_destination_id: Optional[str] = None
            audit_destination_name: Optional[str] = None
            if use_local_storage:
                audit_destination_id = "local"
                audit_destination_name = "Local Storage"
            elif len(destinations) == 1:
                audit_destination_id = destinations[0].id
                audit_destination_name = destinations[0].name
            elif len(destinations) > 1:
                audit_destination_name = "Multiple"

            try:
                session.add(
                    AuditEvent(
                        id=audit_event_id,
                        operation="backup",
                        trigger="manual",
                        status="started",
                        started_at=started_at,
                        target_id=target.id,
                        target_name=target.name,
                        destination_id=audit_destination_id,
                        destination_name=audit_destination_name,
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

            # Create run record
            run = BackupRun(
                id=run_id,
                schedule_id=None,  # No schedule for immediate backups
                status="started",
                started_at=started_at,
                details={"type": "immediate", "target_id": target_id, "target_name": target.name},
            )
            session.add(run)
            await session.commit()

        temp_path: Optional[Path] = None
        encrypted_path: Optional[Path] = None

        try:
            # Create backup file
            filename, temp_path = await self._create_backup_file(target)
            subfolder = self._sanitize_name(target.name)
            backup_filename = f"manual-{subfolder}-{filename}"

            upload_source_path = temp_path
            if password:
                encrypted_path = await run_in_threadpool(
                    self._encrypt_backup_to_temp,
                    input_path=temp_path,
                    password=password,
                )
                upload_source_path = encrypted_path
                backup_filename = f"{backup_filename}.enc"

            uploads: List[Dict[str, Any]] = []

            if use_local_storage:
                provider = LocalStorage(LocalConfig(base_path="/app/backups"))
                dest_filename = f"{subfolder}/{backup_filename}"
                uploaded = await run_in_threadpool(
                    provider.upload_backup,
                    local_path=upload_source_path,
                    dest_name=dest_filename,
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
                    dest_filename = f"{subfolder}/{backup_filename}"

                    uploaded = await run_in_threadpool(
                        provider.upload_backup,
                        local_path=upload_source_path,
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
                    run.details = {
                        "type": "immediate",
                        "target_id": target_id,
                        "target_name": target.name,
                        "uploads": uploads,
                        "encrypted": bool(password),
                    }
                await session.commit()

            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "success"
                            evt.finished_at = finished_at
                            evt.backup_name = backup_filename
                            evt.details = {"uploads": uploads, "encrypted": bool(password)}
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass

            logger.info(
                "Manual backup completed successfully (target_id=%s, destinations=%s, use_local_storage=%s, encrypted=%s)",
                target_id,
                destination_ids,
                use_local_storage,
                bool(password),
            )

            return {
                "run_id": run_id,
                "status": "success",
                "backup_filename": backup_filename,
                "uploads": uploads,
            }

        except Exception as exc:
            logger.exception("Manual backup failed (target_id=%s)", target_id)
            finished_at = datetime.now(timezone.utc)
            async with self.handler.AsyncSessionLocal() as session:
                run = await session.get(BackupRun, run_id)
                if run:
                    run.status = "failed"
                    run.finished_at = finished_at
                    run.error_message = str(exc)
                    if isinstance(run.details, dict):
                        run.details = {
                            **run.details,
                            "target_id": run.details.get("target_id") or target_id,
                            "target_name": run.details.get("target_name") or getattr(target, "name", None),
                        }
                await session.commit()

            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "failed"
                            evt.finished_at = finished_at
                            evt.error_message = str(exc)
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
            raise ValueError(f"Backup failed: {exc}")
        finally:
            for cleanup_path in (encrypted_path, temp_path):
                if cleanup_path and cleanup_path.exists():
                    try:
                        cleanup_path.unlink()
                    except Exception:
                        pass

    @staticmethod
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
        fd, tmp_name = tempfile.mkstemp(suffix=".enc")
        os.close(fd)
        out_path = Path(tmp_name)
        try:
            encrypt_file(input_path=input_path, output_path=out_path, password=password)
            return out_path
        except Exception as exc:
            try:
                if out_path.exists():
                    out_path.unlink()
            except Exception:
                pass
            if isinstance(exc, BackupEncryptionError):
                raise
            raise BackupEncryptionError(f"Failed to encrypt backup file: {exc}") from exc

    async def restore_now(
        self,
        *,
        target_id: str,
        destination_id: Optional[str],
        backup_id: str,
        encryption_password: Optional[str] = None,
        use_local_storage: bool = False,
    ) -> Dict[str, Any]:
        """Restore a database from a backup file.

        Args:
            target_id: ID of the backup target (database) to restore to.
            destination_id: ID of the destination where the backup is stored.
                Required unless use_local_storage=True.
            backup_id: ID or name of the backup file to restore.
            encryption_password: Password used to decrypt encrypted backups.
            use_local_storage: If True, restore from default local storage (/app/backups) and
                ignore destination_id.

        Returns:
            Dict with status, message, and details.

            When the backup is accepted but may be risky (e.g. MySQL vs MariaDB SQL
            dumps), compatibility warnings may be included under details.warnings.

        Raises:
            ValueError: If target, destination, or backup not found.
        """
        started_at = datetime.now(timezone.utc)
        audit_event_id = str(uuid.uuid4())
        audit_event_created = False

        logger.info(
            "Starting manual restore (target_id=%s, destination_id=%s, backup_id=%s, use_local_storage=%s)",
            target_id,
            destination_id,
            backup_id,
            use_local_storage,
        )

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

            try:
                session.add(
                    AuditEvent(
                        id=audit_event_id,
                        operation="restore",
                        trigger="manual",
                        status="started",
                        started_at=started_at,
                        target_id=target.id,
                        target_name=target.name,
                        destination_id=("local" if use_local_storage else getattr(dest, "id", None)),
                        destination_name=("Local Storage" if use_local_storage else getattr(dest, "name", None)),
                        backup_id=str(backup_id),
                        backup_name=str(backup_id),
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

        temp_path: Optional[Path] = None
        downloaded_path: Optional[Path] = None
        decrypted_path: Optional[Path] = None
        restore_warnings: List[str] = []

        try:
            if use_local_storage:
                provider = LocalStorage(LocalConfig(base_path="/app/backups"))
                bid = str(backup_id or "").replace("\\", "/")
                rel = PurePosixPath(bid)
                if not bid or rel.is_absolute() or ".." in rel.parts:
                    raise ValueError("Invalid backup_id")
            else:
                provider = self._build_provider(dest)
                self._validate_destination_backup_id(dest, backup_id)

            suffix = Path(str(backup_id)).suffix or ".backup"
            fd, tmp_name = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            temp_path = Path(tmp_name)

            # Download backup to temp file
            downloaded_path = await run_in_threadpool(
                provider.download_backup,
                backup_id=backup_id,
                dest_path=temp_path,
            )

            restore_input_path = downloaded_path

            if restore_input_path and is_encrypted_backup_file(restore_input_path):
                password = str(encryption_password or "").strip()
                if not password:
                    raise ValueError("Selected backup is encrypted. Please provide encryption_password to restore it.")

                try:
                    decrypted_path = await run_in_threadpool(
                        decrypt_to_temporary_file,
                        encrypted_path=restore_input_path,
                        password=password,
                        suffix=".decrypted",
                    )
                except BackupEncryptionError as exc:
                    raise ValueError(str(exc)) from exc

                restore_input_path = decrypted_path

            if use_local_storage or (dest and dest.destination_type != "google_drive"):
                if not is_backup_name_compatible_with_db_type(db_type=target.db_type, backup_name=str(backup_id)):
                    raise ValueError("Selected backup filename does not match the target database type")

            compat = validate_backup_compatibility(target_db_type=target.db_type, backup_path=restore_input_path)
            restore_warnings.extend(list(compat.warnings or []))

            for w in restore_warnings:
                logger.warning(
                    "Restore compatibility warning (target_id=%s, backup_id=%s): %s",
                    target_id,
                    backup_id,
                    w,
                )

            # Restore the backup
            await self._restore_backup_file(target, restore_input_path)

            finished_at = datetime.now(timezone.utc)
            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "success"
                            evt.finished_at = finished_at
                            if restore_warnings:
                                evt.details = {"warnings": restore_warnings}
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass

            return {
                "status": "success",
                "message": f"Successfully restored {target.name} from backup",
                "details": {
                    "target_id": target_id,
                    "destination_id": destination_id if not use_local_storage else "local",
                    "backup_id": backup_id,
                    "warnings": restore_warnings,
                },
            }

        except Exception as exc:
            logger.exception(
                "Manual restore failed (target_id=%s, destination_id=%s, backup_id=%s)",
                target_id,
                destination_id,
                backup_id,
            )
            finished_at = datetime.now(timezone.utc)
            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "failed"
                            evt.finished_at = finished_at
                            evt.error_message = str(exc)
                            if restore_warnings:
                                evt.details = {"warnings": restore_warnings}
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
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
            target_db_type: Optional[str] = None
            if target_id:
                target = await session.get(BackupTarget, target_id)
                if target:
                    target_name = self._sanitize_name(target.name)
                    target_db_type = target.db_type

        try:
            provider = self._build_provider(dest)

            # List backups, optionally filtered by target subfolder
            prefix = f"{target_name}/" if target_name else ""
            backups = await run_in_threadpool(provider.list_backups, prefix=prefix)

            if target_db_type:
                allowed = tuple(s.lower() for s in allowed_backup_name_extensions_for_db_type(target_db_type))
                if allowed:
                    backups = [
                        b
                        for b in backups
                        if any(str(getattr(b, "name", "")).lower().endswith(suf) for suf in allowed)
                    ]

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

    async def download_backup_from_destination(
        self,
        *,
        destination_id: str,
        backup_id: str,
        filename: Optional[str] = None,
    ) -> Path:
        """Download a backup from a destination to a temporary file.

        Args:
            destination_id: ID of the destination where the backup is stored.
            backup_id: Provider-specific identifier of the backup.
            filename: Optional user-friendly name (used to preserve extension).

        Returns:
            Path: Path to the downloaded temporary file.

        Raises:
            ValueError: If destination not found or download fails.
        """

        async with self.handler.AsyncSessionLocal() as session:
            dest = await session.get(BackupDestination, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")

        self._validate_destination_backup_id(dest, backup_id)

        provider = self._build_provider(dest)
        suffix_source = filename or backup_id
        suffix = Path(str(suffix_source)).suffix or ".backup"
        fd, tmp_name = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        temp_path = Path(tmp_name)

        try:
            await run_in_threadpool(provider.download_backup, backup_id=backup_id, dest_path=temp_path)
            return temp_path
        except Exception as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            raise ValueError(f"Failed to download backup: {exc}")

    async def delete_backup_from_destination(
        self,
        *,
        destination_id: str,
        backup_id: str,
        name: Optional[str] = None,
    ) -> None:
        """Delete a backup file from a destination.

        Args:
            destination_id: ID of the destination where the backup is stored.
            backup_id: Provider-specific identifier of the backup.
            name: Optional display name for logs/metadata.

        Raises:
            ValueError: If destination not found or delete fails.
        """

        started_at = datetime.now(timezone.utc)
        audit_event_id = str(uuid.uuid4())
        audit_event_created = False
        target_name: Optional[str] = None
        display_name = str(name or "")
        if "/" in display_name:
            target_name = display_name.split("/", 1)[0] or None

        async with self.handler.AsyncSessionLocal() as session:
            dest = await session.get(BackupDestination, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")

            try:
                session.add(
                    AuditEvent(
                        id=audit_event_id,
                        operation="delete_backup",
                        trigger="manual",
                        status="started",
                        started_at=started_at,
                        target_name=target_name,
                        destination_id=dest.id,
                        destination_name=dest.name,
                        backup_id=str(backup_id),
                        backup_name=str(name or backup_id),
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

        self._validate_destination_backup_id(dest, backup_id)
        provider = self._build_provider(dest)

        obj = BackupObject(
            id=str(backup_id),
            name=str(name or backup_id),
            created_at=datetime.now(timezone.utc),
            size=None,
        )

        try:
            await run_in_threadpool(provider.delete_backups, [obj])
            finished_at = datetime.now(timezone.utc)
            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "success"
                            evt.finished_at = finished_at
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            if audit_event_created:
                async with self.handler.AsyncSessionLocal() as session:
                    try:
                        evt = await session.get(AuditEvent, audit_event_id)
                        if evt:
                            evt.status = "failed"
                            evt.finished_at = finished_at
                            evt.error_message = str(exc)
                        await session.commit()
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
            raise ValueError(f"Failed to delete backup: {exc}")

    def _validate_destination_backup_id(self, destination: BackupDestination, backup_id: str) -> None:
        """Validate a destination backup id to reduce accidental misuse.

        This API is protected by admin/delete keys, but we still validate obvious
        path traversal and out-of-base deletions for destinations that expose
        filesystem-like identifiers.

        Args:
            destination: Destination model.
            backup_id: Provider-specific identifier.

        Raises:
            ValueError: When backup_id is invalid for the destination.
        """

        bid = str(backup_id or "").replace("\\", "/")
        if not bid:
            raise ValueError("backup_id is required")

        if destination.destination_type == "local":
            rel = PurePosixPath(bid)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Invalid backup_id")
            return

        if destination.destination_type == "sftp":
            cfg = destination.config or {}
            base_path = str(cfg.get("path", cfg.get("base_path", "/backups")))
            base_norm = base_path.rstrip("/")
            if not bid.startswith(f"{base_norm}/"):
                raise ValueError("Invalid backup_id")
            return

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
                service.restore_backup,
                backup_file=backup_path,
                neo4j_url=neo4j_url,
                db_user=db_user,
                db_password=db_password,
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
                service.restore_backup,
                backup_file=backup_path,
                db_type=db_type,
                db_host=raw_host,
                db_port=raw_port,
                db_name=str(cfg.get("database", cfg.get("db_name", ""))),
                db_user=str(cfg.get("user", cfg.get("db_user", ""))),
                db_password=str(secrets.get("password", secrets.get("db_password", ""))),
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
        return build_storage_provider(destination)
