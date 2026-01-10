"""Base storage provider interface for backup destinations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Mapping

from backend.services.automation.retention import BackupObject


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    def __init__(self, env: Mapping[str, str]):
        """Initialize a storage provider.

        Args:
            env: Environment mapping.
        """

        self.env = env

    @abstractmethod
    def list_backups(self, *, prefix: str) -> List[BackupObject]:
        """List all backups managed by this provider.

        Args:
            prefix: Optional name prefix to filter backups.

        Returns:
            List[BackupObject]: Matching backups.
        """

    @abstractmethod
    def upload_backup(self, *, local_path: Path, dest_name: str) -> BackupObject:
        """Upload a local backup file.

        Args:
            local_path: Path to the local file.
            dest_name: Destination filename.

        Returns:
            BackupObject: Metadata about the uploaded file.
        """

    @abstractmethod
    def download_backup(self, *, backup_id: str, dest_path: Path) -> Path:
        """Download a backup to the given destination path.

        Args:
            backup_id: Provider-specific identifier.
            dest_path: Where to store the downloaded file.

        Returns:
            Path: The path to the downloaded file.
        """

    @abstractmethod
    def delete_backups(self, backups: List[BackupObject]) -> None:
        """Delete the given backups.

        Args:
            backups: Backups to delete.
        """
