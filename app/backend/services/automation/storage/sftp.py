"""SFTP storage provider for backups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import io
import posixpath
import stat
from pathlib import Path
from typing import List, Optional

import paramiko

from backend.services.automation.retention import BackupObject
from backend.services.automation.storage.base import StorageProvider


@dataclass(frozen=True)
class SFTPConfig:
    """Configuration for an SFTP destination."""

    host: str
    port: int
    username: str
    base_path: str

    password: Optional[str] = None
    private_key: Optional[str] = None
    private_key_passphrase: Optional[str] = None


class SFTPStorage(StorageProvider):
    """SFTP storage provider.

    This provider stores backups under `base_path` on the remote server.
    """

    def __init__(self, config: SFTPConfig):
        """Initialize the SFTP provider.

        Args:
            config: SFTP configuration.
        """

        super().__init__({})
        self._config = config

    def list_backups(self, *, prefix: str) -> List[BackupObject]:
        """List backups in the remote base path.

        Args:
            prefix: File name prefix filter.

        Returns:
            List[BackupObject]: Matching backups.
        """

        with self._connect() as sftp:
            base_path = self._config.base_path
            self._ensure_dir(sftp, base_path)

            backups: List[BackupObject] = []
            for remote_path, rel_name, attr in self._walk_dir(sftp, base_path):
                if prefix and not rel_name.startswith(prefix):
                    continue
                created = datetime.fromtimestamp(attr.st_mtime, tz=timezone.utc)
                backups.append(
                    BackupObject(
                        id=remote_path,
                        name=rel_name,
                        created_at=created,
                        size=attr.st_size,
                    )
                )

            backups.sort(key=lambda b: b.created_at, reverse=True)
            return backups

    def upload_backup(self, *, local_path: Path, dest_name: str) -> BackupObject:
        """Upload a local file via SFTP.

        Args:
            local_path: Local file.
            dest_name: Destination filename.

        Returns:
            BackupObject: Uploaded object metadata.
        """

        with self._connect() as sftp:
            base_path = self._config.base_path
            self._ensure_dir(sftp, base_path)

            remote_path = f"{base_path.rstrip('/')}/{dest_name}"
            remote_dir = posixpath.dirname(remote_path)
            if remote_dir:
                self._ensure_dir(sftp, remote_dir)

            try:
                sftp.put(str(local_path), remote_path)
            except PermissionError as exc:
                raise PermissionError(
                    f"Permission denied uploading to '{remote_path}'. "
                    f"Check remote folder permissions/ownership for '{remote_dir or base_path}'."
                ) from exc

            attr = sftp.stat(remote_path)
            created = datetime.fromtimestamp(attr.st_mtime, tz=timezone.utc)
            return BackupObject(
                id=remote_path,
                name=dest_name,
                created_at=created,
                size=attr.st_size,
            )

    def _walk_dir(self, sftp: paramiko.SFTPClient, base_path: str):
        """Yield files under base_path recursively.

        Args:
            sftp: Connected SFTP client.
            base_path: Remote base path.

        Yields:
            Tuple[str, str, Any]: (remote_path, rel_name, attr)
        """

        base_norm = base_path.rstrip("/")
        stack = [base_norm]

        while stack:
            current = stack.pop()
            try:
                items = sftp.listdir_attr(current)
            except FileNotFoundError:
                continue

            for item in items:
                remote_path = f"{current.rstrip('/')}/{item.filename}"
                if stat.S_ISDIR(item.st_mode):
                    stack.append(remote_path)
                    continue

                rel_name = remote_path
                if remote_path.startswith(base_norm + "/"):
                    rel_name = remote_path[len(base_norm) + 1 :]

                yield remote_path, rel_name, item

    def download_backup(self, *, backup_id: str, dest_path: Path) -> Path:
        """Download a backup from SFTP.

        Args:
            backup_id: Remote path.
            dest_path: Local path.

        Returns:
            Path: Downloaded file path.
        """

        with self._connect() as sftp:
            sftp.get(backup_id, str(dest_path))
        return dest_path

    def delete_backups(self, backups: List[BackupObject]) -> None:
        """Delete backups from the remote SFTP server.

        Args:
            backups: Backups to delete.
        """

        with self._connect() as sftp:
            for obj in backups:
                try:
                    sftp.remove(obj.id)
                except FileNotFoundError:
                    continue

    def _connect(self):
        """Connect to SFTP and return a context manager yielding an SFTPClient."""

        transport = paramiko.Transport((self._config.host, self._config.port))

        if self._config.private_key:
            key = paramiko.RSAKey.from_private_key(
                io.StringIO(self._config.private_key),
                password=self._config.private_key_passphrase,
            )
            transport.connect(username=self._config.username, pkey=key)
        else:
            transport.connect(username=self._config.username, password=self._config.password)

        client = paramiko.SFTPClient.from_transport(transport)

        class _Ctx:
            def __enter__(self_inner):
                """Enter the SFTP connection context.

                Returns:
                    paramiko.SFTPClient: Connected SFTP client.
                """
                return client

            def __exit__(self_inner, exc_type, exc, tb):
                """Exit the SFTP connection context and close resources.

                Args:
                    exc_type: Exception type.
                    exc: Exception instance.
                    tb: Traceback.
                """
                try:
                    client.close()
                finally:
                    transport.close()

        return _Ctx()

    def _ensure_dir(self, sftp: paramiko.SFTPClient, path: str) -> None:
        """Ensure that a remote directory exists.

        Args:
            sftp: SFTP client.
            path: Remote directory path.
        """

        parts = [p for p in path.strip("/").split("/") if p]
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else f"/{part}"
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)
