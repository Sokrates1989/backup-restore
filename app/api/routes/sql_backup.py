"""SQL database backup and restore API routes.

Provides endpoints for backing up and restoring SQL databases (PostgreSQL, MySQL, SQLite)
with support for both local and remote database configurations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks, Body, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import tempfile
import shutil
import httpx
from starlette.background import BackgroundTask

from backend.services.sql.backup_service import BackupService
from api.security import verify_admin_key, verify_restore_key
from api.schemas.database_config import SQLConfig, SQLStatsConfig


router = APIRouter(
    prefix="/backup/sql",
    tags=["SQL Backup & Restore"]
)


def _cleanup_temp_file(path: Path) -> None:
    try:
        if path and path.exists():
            path.unlink()
    except Exception as e:
        print(f"Warning: Failed to delete temp file {path}: {e}")


# Pydantic models
class RestoreResponse(BaseModel):
    """Response model for restore operation."""
    success: bool
    message: str
    warnings: List[str] | None = None
    warning_count: int = 0
    target_api_locked: bool = False
    locking_warning: str | None = None


class RestoreStatusResponse(BaseModel):
    """Response model for restore operation status."""
    status: str  # in_progress, completed, failed, or none
    current: int = 0
    total: int = 0
    message: str = ""
    warnings_count: int = 0
    warnings: List[str] | None = None
    timestamp: str | None = None
    is_locked: bool = False
    lock_operation: str | None = None


class SQLDatabaseStats(BaseModel):
    """Response model for SQL database statistics."""
    table_count: int = 0
    total_rows: int = 0
    database_size_mb: float = 0.0
    tables: List[dict] = []


async def lock_target_api(api_url: str, api_key: str, operation: str = "restore") -> tuple[bool, str | None]:
    """
    Attempt to lock write operations on target API.
    
    Returns:
        Tuple of (success: bool, warning_message: str | None)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/database/lock",
                json={"operation": operation},
                headers={"X-Admin-Key": api_key}
            )
            if response.status_code == 200:
                return True, None
            else:
                warning = f"Failed to lock target API (HTTP {response.status_code})."
                print(f"⚠️  {warning}")
                return False, warning
    except Exception as e:
        warning = f"Failed to lock target API: {e}."
        print(f"⚠️  {warning}")
        return False, warning


async def unlock_target_api(api_url: str, api_key: str) -> bool:
    """Unlock write operations on target API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/database/unlock",
                headers={"X-Admin-Key": api_key}
            )
            return response.status_code == 200
    except Exception as e:
        print(f"⚠️  Failed to unlock target API: {e}")
        return False


@router.post("/download")
async def download_sql_backup(
    db_config: SQLConfig = Body(...),
    compress: bool = Query(True, description="Compress backup with gzip"),
    _: str = Depends(verify_admin_key)
):
    """
    Create and download a SQL database backup from any database (local or remote).
    
    **Requires admin authentication.**
    
    Supports PostgreSQL, MySQL, and SQLite databases regardless of local configuration.
    
    Args:
        db_config: SQL database connection configuration
        compress: Whether to compress the backup with gzip (default: True)
        
    Returns:
        The backup file for download
    """
    temp_filepath = None
    locked_api = False
    try:
        # Optionally lock target API to improve snapshot consistency
        if getattr(db_config, "lock_target_db", False):
            if not db_config.target_api_url or not db_config.target_api_key:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "lock_target_db is True but target_api_url and/or "
                        "target_api_key are missing"
                    ),
                )
            locked_api, locking_warning = await lock_target_api(
                db_config.target_api_url,
                db_config.target_api_key,
                "backup",
            )
            if not locked_api:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        locking_warning
                        or "Failed to lock target API for backup. Backup was not started. Check /database/lock endpoint."
                    ),
                )

        backup_service = BackupService()

        # Create backup in temporary file off the main event loop
        filename, temp_filepath = await run_in_threadpool(
            backup_service.create_backup_to_temp,
            db_type=db_config.db_type,
            db_host=db_config.db_host,
            db_port=db_config.db_port,
            db_name=db_config.db_name,
            db_user=db_config.db_user,
            db_password=db_config.db_password,
            compress=compress,
        )

        media_type = "application/gzip" if compress else "application/sql"

        return FileResponse(
            path=temp_filepath,
            filename=filename,
            media_type=media_type,
            background=BackgroundTask(_cleanup_temp_file, temp_filepath)
        )

    except HTTPException:
        # HTTP errors are propagated as-is
        raise
    except Exception as e:
        if temp_filepath and temp_filepath.exists():
            temp_filepath.unlink()
        raise HTTPException(status_code=500, detail=f"Backup download failed: {str(e)}")
    finally:
        # Always attempt to unlock target API if we previously locked it
        if locked_api and getattr(db_config, "target_api_url", None) and getattr(db_config, "target_api_key", None):
            unlock_ok = await unlock_target_api(db_config.target_api_url, db_config.target_api_key)
            if not unlock_ok:
                print(
                    "\u26a0\ufe0f  Warning: backup completed but failed to unlock target API. "
                    "Please check /database/lock-status on the target service."
                )


@router.post("/restore-upload", response_model=RestoreResponse)
async def restore_sql_from_uploaded_backup(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db_type: str = Body(...),
    db_host: str = Body(...),
    db_port: int = Body(...),
    db_name: str = Body(...),
    db_user: str = Body(...),
    db_password: str = Body(...),
    lock_target_db: bool = Body(False),
    target_api_url: Optional[str] = Body(None),
    target_api_key: Optional[str] = Body(None),
    _: str = Depends(verify_restore_key)
):
    """
    Restore SQL database from uploaded backup (works on any database - local or remote).
    
    **⚠️ WARNING: This will overwrite the target database!**
    
    **Requires restore authentication.**
    
    This endpoint starts the restore in the background and returns immediately.
    Use GET /backup/sql/restore-status to monitor progress.
    
    Optional locking: If lock_target_db is true, attempts to lock the remote API during
    restore using target_api_url and target_api_key. If locking fails, the restore
    request fails and no restore is started.
    """
    temp_file = None
    locked_api = False
    locking_warning = None
    
    try:
        backup_service = BackupService()
        
        # Check if another operation is in progress (local lock only)
        lock_operation = backup_service.check_operation_lock()
        if lock_operation:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start restore: {lock_operation} operation is already in progress locally"
            )
        
        # Optionally lock target API before starting restore
        if lock_target_db:
            if not target_api_url or not target_api_key:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "lock_target_db is True but target_api_url and/or "
                        "target_api_key are missing"
                    ),
                )
            locked_api, locking_warning = await lock_target_api(
                target_api_url,
                target_api_key,
                "restore",
            )
            if not locked_api:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        locking_warning
                        or "Failed to lock target API for restore. Check /database/lock endpoint."
                    ),
                )

        # Save uploaded file to temporary location
        suffix = '.sql.gz' if file.filename and file.filename.endswith('.gz') else '.sql'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_file = Path(temp.name)
            shutil.copyfileobj(file.file, temp)
        
        # Start restore in background
        background_tasks.add_task(
            backup_service.restore_backup,
            temp_file,
            db_type,
            db_host,
            db_port,
            db_name,
            db_user,
            db_password,
            target_api_url,
            target_api_key
        )
        
        response_content = {
            "success": True,
            "message": f"Restore operation started in background for file: {file.filename}. Use GET /backup/sql/restore-status to monitor progress.",
            "target_api_locked": locked_api
        }
        
        if locking_warning:
            response_content["locking_warning"] = locking_warning
        
        return JSONResponse(status_code=202, content=response_content)
        
    except HTTPException:
        if locked_api and target_api_url and target_api_key:
            unlock_ok = await unlock_target_api(target_api_url, target_api_key)
            if not unlock_ok:
                print(
                    "\u26a0\ufe0f  Warning: restore failed and target API could not be unlocked. "
                    "Please check /database/lock-status on the target service."
                )
        raise
    except Exception as e:
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if locked_api and target_api_url and target_api_key:
            unlock_ok = await unlock_target_api(target_api_url, target_api_key)
            if not unlock_ok:
                print(
                    "\u26a0\ufe0f  Warning: restore failed and target API could not be unlocked. "
                    "Please check /database/lock-status on the target service."
                )
        raise HTTPException(status_code=500, detail=f"Failed to start restore: {str(e)}")


@router.get("/restore-status", response_model=RestoreStatusResponse)
async def get_sql_restore_status(_: str = Depends(verify_restore_key)):
    """
    Get the current status of a SQL restore operation.
    
    **Requires restore authentication.**
    """
    try:
        backup_service = BackupService()
        status = backup_service.get_restore_status()
        
        if status is None:
            lock_operation = backup_service.check_operation_lock()
            return RestoreStatusResponse(
                status="none",
                message="No restore operation in progress or completed recently",
                is_locked=bool(lock_operation),
                lock_operation=lock_operation
            )
        
        return RestoreStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get restore status: {str(e)}")


@router.post("/stats", response_model=SQLDatabaseStats)
async def get_sql_database_stats(
    db_config: SQLStatsConfig = Body(...),
    _: str = Depends(verify_admin_key)
):
    """
    Get SQL database statistics from any SQL database (local or remote).
    
    **Requires admin authentication.**
    
    Returns database statistics including table count, row counts, and database size.
    
    Useful for:
    - Checking database size before backup
    - Verifying restore completed successfully
    - Monitoring database growth
    """
    try:
        backup_service = BackupService()
        
        # Get stats using provided credentials
        stats = await run_in_threadpool(
            backup_service.get_database_stats,
            db_type=db_config.db_type,
            db_host=db_config.db_host,
            db_port=db_config.db_port,
            db_name=db_config.db_name,
            db_user=db_config.db_user,
            db_password=db_config.db_password
        )
        
        return SQLDatabaseStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")
