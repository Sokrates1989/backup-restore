"""Destination CRUD service for backup automation."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import encrypt_secrets, is_config_encryption_enabled
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import destination_to_dict


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
                path = config.get("path", "/backups")
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                if not os.access(path, os.W_OK):
                    raise ValueError(f"Directory {path} is not writable")
                return {"dest_type": dest_type, "path": path, "writable": True}
            
            elif dest_type == "sftp":
                # Test SFTP connection
                import paramiko
                host = config.get("host", "")
                port = config.get("port", 22)
                username = secrets.get("username", "")
                password = secrets.get("password", "")
                
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
                
                ssh.close()
                return {"dest_type": dest_type, "host": host, "port": port, "path": remote_path}
            
            elif dest_type == "google_drive":
                # Test Google Drive connection
                import json
                from googleapiclient.discovery import build
                from google.oauth2 import service_account
                
                credentials_json = secrets.get("service_account_json", {})
                if not credentials_json:
                    raise ValueError("Google Drive service account credentials required")
                
                credentials_info = json.loads(credentials_json)
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

            secrets_provided = secrets is not None
            encrypted = None
            if secrets_provided:
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
            return destination_to_dict(updated)

    async def delete_destination(self, destination_id: str) -> None:
        """Delete a destination."""

        async with self.handler.AsyncSessionLocal() as session:
            dest = await self.repo.get_destination(session, destination_id)
            if not dest:
                raise ValueError(f"Destination not found: {destination_id}")
            await self.repo.delete_destination(session, dest)
