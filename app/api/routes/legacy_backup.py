"""Legacy backup endpoints.

The repository includes older test scripts that expect simple backup endpoints:
- POST /backup/create
- POST /backup/restore/{filename}
- DELETE /backup/delete/{filename}

These endpoints operate on the locally configured database via `api.settings`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import shutil
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from api.security import verify_admin_key, verify_delete_key, verify_restore_key
from api.settings import settings
from backend.services.neo4j.backup_service import Neo4jBackupService
from backend.services.sql.backup_service import BackupService


router = APIRouter(prefix="/backup", tags=["Legacy Backup"])


def _backups_dir() -> Path:
    """Return the persistent backups directory.

    Returns:
        Path: Directory path.
    """

    base = Path("/app/backups")
    base.mkdir(parents=True, exist_ok=True)
    return base


@router.post("/create")
async def legacy_create_backup(
    compress: bool = Query(True, description="Compress backup"),
    _: str = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Create a backup file for the locally configured database."""

    db_type = settings.DB_TYPE

    if db_type == "neo4j":
        service = Neo4jBackupService()
        filename, temp_path = await run_in_threadpool(
            service.create_backup_to_temp,
            neo4j_url=settings.get_neo4j_uri(),
            db_user=settings.DB_USER,
            db_password=settings.get_db_password(),
            compress=compress,
        )
    else:
        service = BackupService()
        filename, temp_path = await run_in_threadpool(
            service.create_backup_to_temp,
            db_type=db_type,
            db_host=settings.DB_HOST,
            db_port=settings.DB_PORT,
            db_name=settings.DB_NAME,
            db_user=settings.DB_USER,
            db_password=settings.get_db_password(),
            compress=compress,
        )

    dest = _backups_dir() / filename
    shutil.copy2(temp_path, dest)

    try:
        temp_path.unlink()
    except Exception:
        pass

    size_mb = round(dest.stat().st_size / (1024 * 1024), 4)
    return {
        "success": True,
        "filename": dest.name,
        "path": str(dest),
        "size_mb": size_mb,
        "created_at": datetime.now().isoformat(),
    }


@router.post("/restore/{filename}")
async def legacy_restore_backup(
    filename: str,
    _: str = Depends(verify_restore_key),
) -> Dict[str, Any]:
    """Restore the locally configured database from a stored backup file."""

    source = _backups_dir() / filename
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")

    suffix = ".gz" if filename.endswith(".gz") else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp_path = Path(temp.name)
        shutil.copyfileobj(source.open("rb"), temp)

    db_type = settings.DB_TYPE

    if db_type == "neo4j":
        service = Neo4jBackupService()
        warnings = await run_in_threadpool(
            service.restore_backup,
            temp_path,
            settings.get_neo4j_uri(),
            settings.DB_USER,
            settings.get_db_password(),
            None,
            None,
        )
        return {
            "success": True,
            "message": "Restore completed successfully",
            "warnings": warnings,
            "warning_count": len(warnings) if warnings else 0,
        }

    service = BackupService()
    result = await run_in_threadpool(
        service.restore_backup,
        temp_path,
        db_type,
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_NAME,
        settings.DB_USER,
        settings.get_db_password(),
        None,
        None,
    )

    return {
        "success": True,
        "message": "Restore completed successfully",
        **(result or {}),
    }


@router.get("/list")
async def list_backups(
    _: str = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List available backup files."""

    backups_dir = _backups_dir()
    files = []

    backup_extensions = (
        ".sql",
        ".sql.gz",
        ".cypher",
        ".cypher.gz",
        ".dump",
        ".dump.gz",
        ".db",
        ".db.gz",
    )
    for path in sorted(backups_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file() and not path.name.startswith(".") and path.name.endswith(backup_extensions):
            stat = path.stat()
            files.append({
                "filename": path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 4),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return {"files": files, "count": len(files)}


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    _: str = Depends(verify_admin_key),
) -> FileResponse:
    """Download a stored backup file.

    Args:
        filename: Backup filename to download.

    Returns:
        FileResponse: Backup file.

    Raises:
        HTTPException: If the file does not exist.
    """

    path = _backups_dir() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")

    return FileResponse(path=path, filename=path.name)


@router.delete("/delete/{filename}")
async def legacy_delete_backup(
    filename: str,
    _: str = Depends(verify_delete_key),
) -> Dict[str, Any]:
    """Delete a stored backup file."""

    path = _backups_dir() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")

    path.unlink()
    return {"success": True, "message": f"Deleted {filename}"}
