"""Storage provider factory for backup destinations.

This module centralizes the logic that converts a database `BackupDestination` record
into a concrete storage provider instance.

Adding a new destination type should generally only require:
- Implementing a new provider under `backend.services.automation.storage.*`
- Extending `build_storage_provider` with the new type

This keeps provider selection consistent across automation executor, immediate
backup/restore flows, and API endpoints.
"""

from __future__ import annotations

from typing import Any

from backend.services.automation.config_crypto import decrypt_secrets
from backend.services.automation.storage.google_drive import GoogleDriveConfig, GoogleDriveStorage
from backend.services.automation.storage.local import LocalConfig, LocalStorage
from backend.services.automation.storage.sftp import SFTPConfig, SFTPStorage
from models.sql.backup_automation import BackupDestination


def build_storage_provider(destination: BackupDestination) -> Any:
    """Instantiate a storage provider from a destination record.

    Args:
        destination: Destination model.

    Returns:
        Any: Storage provider instance.

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
