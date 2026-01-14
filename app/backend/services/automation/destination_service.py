"""Destination CRUD service for backup automation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import encrypt_secrets, is_config_encryption_enabled
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import destination_to_dict
from models.sql.backup_automation import AuditEvent, BackupDestination


class DestinationService:
    """Service for managing backup destinations."""

    def __init__(self, handler: SQLHandler):
        """Initialize the service.

        Args:
            handler: SQL handler.
        """

        self.handler = handler
        self.repo = AutomationRepository()

    async def list_destinations(self) -> List[Dict[str, Any]]:
        """List destinations."""

        async with self.handler.AsyncSessionLocal() as session:
            items = await self.repo.list_destinations(session)
            return [destination_to_dict(d) for d in items]

    async def ensure_local_destination_exists(self) -> Dict[str, Any]:
        """Ensure a built-in local destination exists.

        The UI and schedules rely on a consistent "Local Storage" option, even when
        the user has not configured any remote destinations.

        Returns:
            Dict[str, Any]: Serialized destination.
        """

        async with self.handler.AsyncSessionLocal() as session:
            existing = await session.get(BackupDestination, "local")
            if existing:
                return destination_to_dict(existing)

            dest = BackupDestination(
                id="local",
                name="Local Storage",
                destination_type="local",
                config={"path": "/app/backups"},
                config_encrypted=None,
                is_active=True,
            )
            session.add(dest)
            await session.commit()
            await session.refresh(dest)
            return destination_to_dict(dest)

    async def test_connection(self, *, dest_type: str, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to a backup destination.

        Args:
            dest_type: Destination type.
            config: Public configuration.
            secrets: Secrets for authentication.

        Returns:
            Dict[str, Any]: Connection test result.

        Raises:
            ValueError: If connection fails.
        """

        try:
            if dest_type == "local":
                # Test local directory access
                path = config.get("path", "/app/backups")
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                if not os.access(path, os.W_OK):
                    raise ValueError(f"Directory {path} is not writable")
                return {"dest_type": dest_type, "path": path, "writable": True}
            
            elif dest_type == "sftp":
                # Test SFTP connection
                import paramiko
                import io
                host = config.get("host", "")
                port = config.get("port", 22)
                username = config.get("username") or secrets.get("username") or ""
                password = secrets.get("password") or config.get("password") or ""
                private_key = secrets.get("private_key")
                private_key_passphrase = secrets.get("private_key_passphrase")
                
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                if private_key:
                    pkey = paramiko.RSAKey.from_private_key(
                        io.StringIO(private_key),
                        password=private_key_passphrase,
                    )
                    ssh.connect(host, port=port, username=username, pkey=pkey, timeout=10)
                else:
                    ssh.connect(host, port=port, username=username, password=password, timeout=10)
                
                # Test remote path
                remote_path = config.get("path", "/backups")
                sftp = ssh.open_sftp()
                try:
                    sftp.stat(remote_path)
                except FileNotFoundError:
                    # Try to create directory
                    try:
                        sftp.mkdir(remote_path)
                    except:
                        pass  # Directory might already exist or we don't have permission

                # Verify write + delete permissions
                test_name = f".backup-restore-test-{os.getpid()}.tmp"
                test_path = f"{remote_path.rstrip('/')}/{test_name}"
                try:
                    with sftp.open(test_path, "w") as f:
                        f.write("test")
                    sftp.remove(test_path)
                except Exception as exc:
                    raise ValueError(
                        f"SFTP path '{remote_path}' is not writable/deletable ({exc}). "
                        "Check folder ownership/permissions (chown/chmod) on the remote server."
                    )
                
                ssh.close()
                return {"dest_type": dest_type, "host": host, "port": port, "path": remote_path, "writable": True}
            
            elif dest_type == "google_drive":
                # Test Google Drive connection
                from googleapiclient.discovery import build
                from google.oauth2 import service_account
                
                credentials_payload = secrets.get("service_account_json")
                if not credentials_payload:
                    raise ValueError("Google Drive service account credentials required")

                if isinstance(credentials_payload, str):
                    credentials_info = json.loads(credentials_payload)
                elif isinstance(credentials_payload, dict):
                    credentials_info = credentials_payload
                else:
                    raise ValueError("Invalid service_account_json format (expected JSON string or object)")

                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                
                service = build('drive', 'v3', credentials=credentials)
                # Test access by listing files
                service.files().list(pageSize=1).execute()
                
                folder_id = config.get("folder_id", "root")
                return {"dest_type": dest_type, "folder_id": folder_id}
            
            else:
                raise ValueError(f"Unsupported destination type: {dest_type}")
                
        except Exception as exc:
            raise ValueError(f"Connection test failed: {str(exc)}")

    async def create_destination(
        self,
        *,
        name: str,
        destination_type: str,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a destination."""

        if destination_type == "google_drive" and "service_account_json" in (secrets or {}):
            value = secrets.get("service_account_json")
            if isinstance(value, dict):
                secrets = dict(secrets)
                secrets["service_account_json"] = json.dumps(value)

        if secrets and not is_config_encryption_enabled():
            raise ValueError("Secrets provided but CONFIG_ENCRYPTION_KEY is not configured")

        async with self.handler.AsyncSessionLocal() as session:
            encrypted = encrypt_secrets(secrets) if secrets else None
            dest = await self.repo.create_destination(
                session,
                name=name,
                destination_type=destination_type,
                config=config or {},
                config_encrypted=encrypted,
            )

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="destination_create",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        destination_id=dest.id,
                        destination_name=dest.name,
                        details={"destination_type": dest.destination_type},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return destination_to_dict(dest)

    async def update_destination(
        self,
        destination_id: str,
        *,
        name: Optional[str] = None,
        destination_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a destination."""

        async with self.handler.AsyncSessionLocal() as session:
            dest = await self.repo.get_destination(session, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")

            before = {"name": dest.name, "destination_type": dest.destination_type, "is_active": dest.is_active}

            secrets_provided = secrets is not None
            encrypted = None
            if secrets_provided:
                effective_type = destination_type or dest.destination_type
                if effective_type == "google_drive" and secrets and "service_account_json" in secrets:
                    value = secrets.get("service_account_json")
                    if isinstance(value, dict):
                        secrets = dict(secrets)
                        secrets["service_account_json"] = json.dumps(value)

                if secrets and not is_config_encryption_enabled():
                    raise ValueError("Secrets provided but CONFIG_ENCRYPTION_KEY is not configured")
                encrypted = encrypt_secrets(secrets) if secrets else None

            updated = await self.repo.update_destination(
                session,
                dest,
                name=name,
                destination_type=destination_type,
                config=config,
                config_encrypted=encrypted,
                is_active=is_active,
                secrets_provided=secrets_provided,
            )

            try:
                now = datetime.now(timezone.utc)
                after = {
                    "name": updated.name,
                    "destination_type": updated.destination_type,
                    "is_active": updated.is_active,
                }
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="destination_update",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        destination_id=updated.id,
                        destination_name=updated.name,
                        details={"before": before, "after": after},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return destination_to_dict(updated)

    async def delete_destination(self, destination_id: str) -> None:
        """Delete a destination."""

        if destination_id == "local":
            raise ValueError("The built-in 'Local Storage' destination cannot be deleted")

        async with self.handler.AsyncSessionLocal() as session:
            dest = await self.repo.get_destination(session, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")
            dest_name = dest.name
            await self.repo.delete_destination(session, dest)

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="destination_delete",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        destination_id=destination_id,
                        destination_name=dest_name,
                        details={},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
