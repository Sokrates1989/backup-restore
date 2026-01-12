"""Local filesystem storage provider for backups.

This module provides local directory storage for backup files.
Primarily intended for testing and development use.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.services.automation.retention import BackupObject


@dataclass
class LocalConfig:
    """Configuration for local storage.

    Attributes:
        base_path: Base directory path for storing backups.
    """

    base_path: str = "/backups"


class LocalStorage:
    """Local filesystem storage provider."""

    def __init__(self, config: LocalConfig):
        """Initialize local storage.

        Args:
            config: Local storage configuration.
        """
        self.config = config
        self.base_path = Path(config.base_path)

    def _ensure_path(self, path: Path) -> None:
        """Ensure a directory path exists.

        Args:
            path: Directory path to ensure exists.
        """
        path.mkdir(parents=True, exist_ok=True)

    def list_backups(self, *, prefix: str = "") -> List[BackupObject]:
        """List all backups in the local directory.

        Args:
            prefix: Optional name prefix to filter backups.

        Returns:
            List[BackupObject]: Matching backups.
        """
        self._ensure_path(self.base_path)
        
        backups = []
        
        # Walk through base path
        for root, dirs, files in os.walk(self.base_path):
            for filename in files:
                filepath = Path(root) / filename
                rel_path = filepath.relative_to(self.base_path)
                rel_path_str = str(rel_path).replace("\\", "/")
                
                # Filter by prefix if specified
                if prefix and not rel_path_str.startswith(prefix):
                    continue
                
                stat = filepath.stat()
                backups.append(BackupObject(
                    id=rel_path_str,
                    name=rel_path_str,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                ))
        
        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def upload_backup(self, *, local_path: Path, dest_name: str) -> BackupObject:
        """Copy a local backup file to the storage directory.

        Args:
            local_path: Path to the source file.
            dest_name: Destination filename (may include subdirectory).

        Returns:
            BackupObject: Metadata about the uploaded file.
        """
        dest_path = self.base_path / dest_name
        self._ensure_path(dest_path.parent)
        
        shutil.copy2(local_path, dest_path)
        
        stat = dest_path.stat()
        return BackupObject(
            id=dest_name,
            name=dest_name,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    def download_backup(self, *, backup_id: str, dest_path: Optional[Path] = None) -> Path:
        """Download a backup to a local file.

        This method is compatible with the generic StorageProvider interface.
        If `dest_path` is not provided, a temporary file is created.

        Args:
            backup_id: Relative path to the backup file.
            dest_path: Optional destination path for the downloaded file.

        Returns:
            Path: Path to the downloaded file.

        Raises:
            FileNotFoundError: If the backup file doesn't exist.
        """
        source_path = self.base_path / backup_id
        
        if not source_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_id}")
        
        if dest_path is None:
            # Create temp file with same extension
            suffix = source_path.suffix or ".backup"
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            dest_path = Path(temp_path)

        self._ensure_path(Path(dest_path).parent)
        shutil.copy2(source_path, dest_path)
        return Path(dest_path)

    def delete_backups(self, backups: List[BackupObject]) -> None:
        """Delete the given backups.

        Args:
            backups: Backups to delete.
        """
        for backup in backups:
            filepath = self.base_path / backup.id
            if filepath.exists():
                filepath.unlink()
                
                # Clean up empty parent directories
                parent = filepath.parent
                while parent != self.base_path and parent.exists():
                    try:
                        parent.rmdir()  # Only removes if empty
                        parent = parent.parent
                    except OSError:
                        break
