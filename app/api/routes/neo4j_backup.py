"""Neo4j database backup and restore API routes.

Provides endpoints for backing up and restoring Neo4j graph databases
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

from backend.services.neo4j.backup_service import Neo4jBackupService
from api.security import verify_admin_key, verify_restore_key
from api.schemas.database_config import Neo4jConfig, Neo4jStatsConfig


router = APIRouter(
    prefix="/backup/neo4j",
    tags=["Neo4j Backup & Restore"]
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


class DatabaseStats(BaseModel):
    """Response model for Neo4j database statistics."""
    node_count: int = 0
    relationship_count: int = 0
    labels: List[str] = []
    relationship_types: List[str] = []


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
                warning = f"Failed to lock target API (HTTP {response.status_code}). Proceeding without lock."
                print(f"⚠️  {warning}")
                return False, warning
    except Exception as e:
        warning = f"Failed to lock target API: {e}. Proceeding without lock."
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
async def download_neo4j_backup(
    db_config: Neo4jConfig = Body(...),
    compress: bool = Query(True, description="Compress backup with gzip"),
    _: str = Depends(verify_admin_key)
):
    """
    Create and download a Neo4j database backup from any database (local or remote).
    
    **Requires admin authentication.**
    
    Works with any Neo4j database regardless of local configuration.
    
    Args:
        db_config: Neo4j database connection configuration
        compress: Whether to compress the backup with gzip (default: True)
        
    Returns:
        The backup file for download
    """
    temp_filepath = None
    try:
        backup_service = Neo4jBackupService()
        
        filename, temp_filepath = await run_in_threadpool(
            backup_service.create_backup_to_temp,
            neo4j_url=db_config.neo4j_url,
            db_user=db_config.db_user,
            db_password=db_config.db_password,
            compress=compress,
        )
        
        media_type = "application/gzip" if compress else "text/plain"
        
        return FileResponse(
            path=temp_filepath,
            filename=filename,
            media_type=media_type,
            background=BackgroundTask(_cleanup_temp_file, temp_filepath)
        )
        
    except Exception as e:
        if temp_filepath and temp_filepath.exists():
            temp_filepath.unlink()
        raise HTTPException(status_code=500, detail=f"Backup download failed: {str(e)}")


@router.post("/restore-upload", response_model=RestoreResponse)
async def restore_neo4j_from_uploaded_backup(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    neo4j_url: str = Body(...),
    db_user: str = Body(...),
    db_password: str = Body(...),
    target_api_url: Optional[str] = Body(None),
    target_api_key: Optional[str] = Body(None),
    _: str = Depends(verify_restore_key)
):
    """
    Restore Neo4j database from uploaded backup (works on any database - local or remote).
    
    **⚠️ WARNING: This will DELETE ALL existing data!**
    
    **Requires restore authentication.**
    
    This endpoint starts the restore in the background and returns immediately.
    Use GET /backup/neo4j/restore-status to monitor progress.
    
    Optional locking: If target_api_url and target_api_key are provided, attempts to lock
    the remote API during restore. If locking fails, proceeds with a warning.
    """
    temp_file = None
    locked_api = False
    locking_warning = None
    
    try:
        backup_service = Neo4jBackupService()
        
        # Check if another operation is in progress (local lock only)
        lock_operation = backup_service.check_operation_lock()
        if lock_operation:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start restore: {lock_operation} operation is already in progress locally"
            )
        
        # Attempt to lock target API if provided (non-blocking)
        if target_api_url and target_api_key:
            locked_api, locking_warning = await lock_target_api(target_api_url, target_api_key, "restore")
        
        # Save uploaded file to temporary location
        suffix = '.cypher.gz' if file.filename and file.filename.endswith('.gz') else '.cypher'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_file = Path(temp.name)
            shutil.copyfileobj(file.file, temp)
        
        # Start restore in background
        background_tasks.add_task(
            backup_service.restore_backup,
            temp_file,
            neo4j_url,
            db_user,
            db_password,
            target_api_url,
            target_api_key
        )
        
        response_content = {
            "success": True,
            "message": f"Restore operation started in background for file: {file.filename}. Use GET /backup/neo4j/restore-status to monitor progress.",
            "target_api_locked": locked_api
        }
        
        if locking_warning:
            response_content["locking_warning"] = locking_warning
        
        return JSONResponse(status_code=202, content=response_content)
        
    except HTTPException:
        if locked_api and target_api_url and target_api_key:
            await unlock_target_api(target_api_url, target_api_key)
        raise
    except Exception as e:
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if locked_api and target_api_url and target_api_key:
            await unlock_target_api(target_api_url, target_api_key)
        raise HTTPException(status_code=500, detail=f"Failed to start restore: {str(e)}")


@router.get("/restore-status", response_model=RestoreStatusResponse)
async def get_neo4j_restore_status(_: str = Depends(verify_restore_key)):
    """
    Get the current status of a Neo4j restore operation.
    
    **Requires restore authentication.**
    """
    try:
        backup_service = Neo4jBackupService()
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


@router.post("/stats", response_model=DatabaseStats)
async def get_neo4j_database_stats(
    db_config: Neo4jStatsConfig = Body(...),
    _: str = Depends(verify_admin_key)
):
    """
    Get Neo4j database statistics from any Neo4j database (local or remote).
    
    **Requires admin authentication.**
    
    Returns database statistics including node count, relationship count, labels, and types.
    
    Useful for:
    - Checking database size before backup
    - Verifying restore completed successfully
    - Monitoring database growth
    """
    try:
        backup_service = Neo4jBackupService()
        
        # Get stats using provided credentials
        stats = await run_in_threadpool(
            backup_service.get_database_stats,
            neo4j_url=db_config.neo4j_url,
            db_user=db_config.db_user,
            db_password=db_config.db_password
        )
        
        return DatabaseStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")
