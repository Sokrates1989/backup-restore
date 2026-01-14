"""Google Drive storage provider for backups using a service account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import List, Optional, Set

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

from backend.services.automation.retention import BackupObject
from backend.services.automation.storage.base import StorageProvider


@dataclass(frozen=True)
class GoogleDriveConfig:
    """Configuration for Google Drive destination."""

    service_account_json: str
    folder_id: str


class GoogleDriveStorage(StorageProvider):
    """Google Drive storage provider using a service account."""

    def __init__(self, config: GoogleDriveConfig):
        """Initialize the provider.

        Args:
            config: Google Drive configuration.
        """

        super().__init__({})
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(config.service_account_json),
            scopes=scopes,
        )
        self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        if not config.folder_id:
            raise ValueError("Google Drive folder_id is required")
        self._folder_id = config.folder_id
        self._folder_cache: dict[tuple[str, str], Optional[str]] = {}
        self._file_allowed_cache: dict[str, bool] = {}

    def _file_is_within_destination(self, *, file_id: str) -> bool:
        """Return True when the file is within the configured destination folder tree.

        Args:
            file_id: Google Drive file id.

        Returns:
            bool: True if the file is within the configured folder tree.
        """

        fid = str(file_id or "").strip()
        if not fid:
            return False
        if fid in self._file_allowed_cache:
            return self._file_allowed_cache[fid]

        try:
            meta = self._service.files().get(fileId=fid, fields="id, parents").execute()
        except Exception:
            self._file_allowed_cache[fid] = False
            return False

        parents = list(meta.get("parents", []) or [])
        if not parents:
            self._file_allowed_cache[fid] = False
            return False

        visited: Set[str] = set()
        stack = parents[:]
        max_hops = 50

        while stack and len(visited) < max_hops:
            current = stack.pop()
            if not current or current in visited:
                continue
            if current == self._folder_id:
                self._file_allowed_cache[fid] = True
                return True
            visited.add(current)
            try:
                pmeta = self._service.files().get(fileId=current, fields="id, parents").execute()
            except Exception:
                continue
            for p in (pmeta.get("parents", []) or []):
                if p and p not in visited:
                    stack.append(p)

        self._file_allowed_cache[fid] = False
        return False

    def _assert_file_within_destination(self, *, file_id: str) -> None:
        """Raise ValueError if a file is not within the configured destination folder tree.

        Args:
            file_id: Google Drive file id.

        Raises:
            ValueError: If the file is not within the configured destination folder.
        """

        if not self._file_is_within_destination(file_id=file_id):
            raise ValueError("Invalid backup_id for this destination")

    def _folder_mime(self) -> str:
        """Return the Google Drive mime type for folders."""

        return "application/vnd.google-apps.folder"

    def _list_children(self, *, parent_id: str, include_folders: bool) -> list[dict]:
        """List direct child items for a Google Drive folder.

        Args:
            parent_id: Parent folder id.
            include_folders: When True include folders. When False include files only.

        Returns:
            list[dict]: Raw file items.
        """

        folder_mime = self._folder_mime()
        if include_folders:
            query = f"'{parent_id}' in parents and trashed = false"
        else:
            query = f"'{parent_id}' in parents and trashed = false and mimeType != '{folder_mime}'"

        items: list[dict] = []
        page_token: Optional[str] = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, createdTime, size, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )

            items.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return items

    def _find_child_folder_id(self, *, parent_id: str, name: str) -> Optional[str]:
        """Find a child folder id by name.

        Args:
            parent_id: Parent folder id.
            name: Folder name.

        Returns:
            Optional[str]: Folder id if found.
        """

        key = (parent_id, name)
        if key in self._folder_cache:
            return self._folder_cache[key]

        folder_mime = self._folder_mime()
        safe_name = name.replace("'", "\\'")
        query = (
            f"'{parent_id}' in parents and trashed = false and mimeType = '{folder_mime}' and name = '{safe_name}'"
        )

        response = (
            self._service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )

        files = response.get("files", [])
        folder_id = files[0]["id"] if files else None
        self._folder_cache[key] = folder_id
        return folder_id

    def _ensure_child_folder_id(self, *, parent_id: str, name: str) -> str:
        """Get or create a child folder under parent.

        Args:
            parent_id: Parent folder id.
            name: Folder name.

        Returns:
            str: Folder id.
        """

        existing = self._find_child_folder_id(parent_id=parent_id, name=name)
        if existing:
            return existing

        created = (
            self._service.files()
            .create(
                body={"name": name, "mimeType": self._folder_mime(), "parents": [parent_id]},
                fields="id, name",
            )
            .execute()
        )
        folder_id = created["id"]
        self._folder_cache[(parent_id, name)] = folder_id
        return folder_id

    def _to_backup_object(self, *, file: dict, display_name: str) -> Optional[BackupObject]:
        """Convert a Drive API file dict into BackupObject.

        Args:
            file: Raw file dict.
            display_name: Name to expose in UI (may include "folder/").

        Returns:
            Optional[BackupObject]: Backup object if createdTime exists.
        """

        created_raw = file.get("createdTime")
        if not created_raw:
            return None

        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        size = int(file.get("size", 0)) if "size" in file else None
        return BackupObject(id=file["id"], name=display_name, created_at=created, size=size)

    def list_backups(self, *, prefix: str) -> List[BackupObject]:
        """List backups in the configured folder.

        Args:
            prefix: Optional name prefix.

        Returns:
            List[BackupObject]: Backup objects.
        """

        backups: List[BackupObject] = []
        normalized_prefix = (prefix or "").lstrip("/")

        # If caller uses "subfolder/..." we interpret it as a folder lookup.
        if "/" in normalized_prefix:
            folder_name, rest = normalized_prefix.split("/", 1)
            folder_id = self._find_child_folder_id(parent_id=self._folder_id, name=folder_name)
            if not folder_id:
                # Backward compatibility: older versions uploaded files into the base folder
                # with names that contained '/', which Google Drive allowed as a literal name.
                for item in self._list_children(parent_id=self._folder_id, include_folders=False):
                    name = item.get("name", "")
                    if not name.startswith(normalized_prefix):
                        continue
                    obj = self._to_backup_object(file=item, display_name=name)
                    if obj:
                        backups.append(obj)

                backups.sort(key=lambda b: b.created_at, reverse=True)
                return backups

            for item in self._list_children(parent_id=folder_id, include_folders=False):
                display = f"{folder_name}/{item.get('name', '')}".rstrip("/")
                if rest and not display.startswith(normalized_prefix):
                    continue
                obj = self._to_backup_object(file=item, display_name=display)
                if obj:
                    backups.append(obj)

            backups.sort(key=lambda b: b.created_at, reverse=True)
            return backups

        # prefix empty or no folder component: list root files + one level of folders
        root_items = self._list_children(parent_id=self._folder_id, include_folders=True)
        folders = [i for i in root_items if i.get("mimeType") == self._folder_mime()]
        files = [i for i in root_items if i.get("mimeType") != self._folder_mime()]

        for item in files:
            name = item.get("name", "")
            if normalized_prefix and not name.startswith(normalized_prefix):
                continue
            obj = self._to_backup_object(file=item, display_name=name)
            if obj:
                backups.append(obj)

        for folder in folders:
            folder_id = folder.get("id")
            folder_name = folder.get("name", "")
            if not folder_id or not folder_name:
                continue

            # When a prefix is provided (e.g. "db") and we're listing all folders,
            # only include matching folder names.
            if normalized_prefix and not folder_name.startswith(normalized_prefix):
                continue

            for item in self._list_children(parent_id=folder_id, include_folders=False):
                display = f"{folder_name}/{item.get('name', '')}".rstrip("/")
                obj = self._to_backup_object(file=item, display_name=display)
                if obj:
                    backups.append(obj)

        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def upload_backup(self, *, local_path: Path, dest_name: str) -> BackupObject:
        """Upload a backup file.

        Args:
            local_path: Local file.
            dest_name: Destination name.

        Returns:
            BackupObject: Uploaded file metadata.
        """

        display_name = dest_name
        parent_id = self._folder_id
        filename = dest_name
        if "/" in dest_name:
            folder_name, filename = dest_name.split("/", 1)
            parent_id = self._ensure_child_folder_id(parent_id=self._folder_id, name=folder_name)

        file_metadata = {"name": filename, "parents": [parent_id]}
        media = MediaFileUpload(str(local_path), resumable=False)

        created_file = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, createdTime, size")
            .execute()
        )

        created_raw = created_file.get("createdTime")
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        size = int(created_file.get("size", 0)) if "size" in created_file else None

        return BackupObject(
            id=created_file["id"],
            name=display_name,
            created_at=created,
            size=size,
        )

    def download_backup(self, *, backup_id: str, dest_path: Path) -> Path:
        """Download a backup file.

        Args:
            backup_id: Google Drive file id.
            dest_path: Local path.

        Returns:
            Path: Downloaded file path.
        """

        self._assert_file_within_destination(file_id=backup_id)
        request = self._service.files().get_media(fileId=backup_id)
        fh = io.FileIO(str(dest_path), "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.close()
        return dest_path

    def delete_backups(self, backups: List[BackupObject]) -> None:
        """Delete backups from Google Drive.

        Args:
            backups: Backups to delete.
        """

        for obj in backups:
            self._assert_file_within_destination(file_id=obj.id)
            self._service.files().delete(fileId=obj.id).execute()
