"""Google Drive storage provider for backups using a service account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import List, Optional

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
        self._folder_id = config.folder_id

    def list_backups(self, *, prefix: str) -> List[BackupObject]:
        """List backups in the configured folder.

        Args:
            prefix: Optional name prefix.

        Returns:
            List[BackupObject]: Backup objects.
        """

        query = f"'{self._folder_id}' in parents and trashed = false"

        backups: List[BackupObject] = []
        page_token: Optional[str] = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, createdTime, size)",
                    pageToken=page_token,
                )
                .execute()
            )

            for item in response.get("files", []):
                name = item.get("name", "")
                if prefix and not name.startswith(prefix):
                    continue

                created_raw = item.get("createdTime")
                if not created_raw:
                    continue

                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
                size = int(item.get("size", 0)) if "size" in item else None

                backups.append(
                    BackupObject(
                        id=item["id"],
                        name=name,
                        created_at=created,
                        size=size,
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return backups

    def upload_backup(self, *, local_path: Path, dest_name: str) -> BackupObject:
        """Upload a backup file.

        Args:
            local_path: Local file.
            dest_name: Destination name.

        Returns:
            BackupObject: Uploaded file metadata.
        """

        file_metadata = {"name": dest_name, "parents": [self._folder_id]}
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
            name=created_file.get("name", dest_name),
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
            self._service.files().delete(fileId=obj.id).execute()
