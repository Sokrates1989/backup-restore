"""File-related endpoints.

These endpoints are used by `testing/scripts/test-api.sh`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from backend.services.file_service import FileService


router = APIRouter(prefix="/files", tags=["Files"])


def _file_service() -> FileService:
    """Build a FileService instance.

    Returns:
        FileService: Service instance.
    """

    return FileService(mount_path=Path("/mnt/data"))


@router.get("/file-count")
async def get_file_count():
    """Return number of files in the mounted data directory."""

    return _file_service().get_file_count()
