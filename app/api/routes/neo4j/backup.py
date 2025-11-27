"""API routes for Neo4j database backup and restore operations."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List
from pathlib import Path
import tempfile
import shutil

from backend.services.neo4j.backup_service import Neo4jBackupService
from api.security import verify_admin_key, verify_restore_key


router = APIRouter(
    prefix="/backup",
    tags=["database backup"]
)


# Pydantic models
class RestoreResponse(BaseModel):
    """Response model for restore operation."""
    success: bool
    message: str
    warnings: List[str] | None = None
    warning_count: int = 0


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
    """Model for database statistics."""
    node_count: int
    relationship_count: int
    labels: List[str]
    relationship_types: List[str]


# Initialize service
backup_service = Neo4jBackupService()


@router.get("/download")
async def download_backup(compress: bool = True, _: str = Depends(verify_admin_key)):
    """
    Create and immediately download a Neo4j database backup.
    
    **Requires admin authentication.**
    
    The backup is created in a temporary file and immediately returned for download.
    The temporary file is automatically deleted after the download completes.
    
    Args:
        compress: Whether to compress the backup with gzip (default: True)
        
    Returns:
        The backup file for download
        
    Example:
        ```
        GET /backup/download?compress=true
        Headers: X-Admin-Key: your-admin-key
        ```
        
    Note:
        - Exports all nodes and relationships as Cypher CREATE statements
        - Compressed backups (.cypher.gz) are smaller and faster to transfer
        - Uncompressed backups (.cypher) are plain text and easier to inspect
    """
    temp_filepath = None
    try:
        # Create backup in temporary file off the main event loop
        filename, temp_filepath = await run_in_threadpool(
            backup_service.create_backup_to_temp,
            compress=compress,
        )
        
        # Determine media type
        media_type = "application/gzip" if compress else "text/plain"
        
        # Return file for download (FastAPI will handle cleanup via background task)
        return FileResponse(
            path=temp_filepath,
            filename=filename,
            media_type=media_type,
            background=lambda: temp_filepath.unlink() if temp_filepath and temp_filepath.exists() else None
        )
        
    except Exception as e:
        # Clean up temp file on error
        if temp_filepath and temp_filepath.exists():
            temp_filepath.unlink()
        raise HTTPException(status_code=500, detail=f"Backup download failed: {str(e)}")


@router.post("/restore-upload", response_model=RestoreResponse)
async def restore_from_uploaded_backup(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: str = Depends(verify_restore_key)
):
    """
    Restore Neo4j database from an uploaded backup file (runs in background).
    
    **⚠️ WARNING: This will DELETE ALL existing data and replace it with the backup!**
    
    **Requires restore authentication.**
    
    This endpoint accepts the backup file, saves it, and starts the restore
    operation in the background. It returns immediately with a 202 Accepted status.
    
    Use GET /backup/restore-status to monitor the restore progress.
    
    Args:
        file: Backup file to upload and restore from (Cypher script)
        
    Returns:
        Immediate response confirming restore has started
        
    Example:
        ```
        POST /backup/restore-upload
        Headers: X-Restore-Key: your-restore-key
        Body: multipart/form-data with file
        
        Response: 202 Accepted
        {
            "success": true,
            "message": "Restore operation started in background..."
        }
        
        Then poll: GET /backup/restore-status
        ```
        
    Security:
        - Requires X-Restore-Key header with restore API key
        - Clears all existing Neo4j data before restore
        - Use with extreme caution in production
    """
    temp_file = None
    try:
        # Check if another operation is in progress
        lock_operation = backup_service.check_operation_lock()
        if lock_operation:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start restore: {lock_operation} operation is already in progress"
            )
        
        # Save uploaded file to temporary location
        suffix = '.cypher.gz' if file.filename and file.filename.endswith('.gz') else '.cypher'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_file = Path(temp.name)
            shutil.copyfileobj(file.file, temp)
        
        # Start restore in background
        background_tasks.add_task(backup_service.restore_backup, temp_file)
        
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "message": f"Restore operation started in background for file: {file.filename}. Use GET /backup/restore-status to monitor progress."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up temp file on error
        if temp_file and temp_file.exists():
            temp_file.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to start restore: {str(e)}")




@router.get("/restore-status", response_model=RestoreStatusResponse)
async def get_restore_status(_: str = Depends(verify_restore_key)):
    """
    Get the current status of a restore operation.
    
    **Requires restore authentication.**
    
    Returns:
        Current restore operation status including progress, warnings, and lock status
        
    Example:
        ```
        GET /backup/restore-status
        Headers: X-Restore-Key: your-restore-key
        ```
        
    Response:
        - `status`: Operation status (in_progress, completed, failed, or none)
        - `current`: Current statement number being executed
        - `total`: Total number of statements
        - `message`: Status message
        - `warnings_count`: Number of warnings encountered
        - `warnings`: List of warning messages (if any)
        - `is_locked`: Whether backup/restore operations are currently locked
        - `lock_operation`: Name of the operation holding the lock (if any)
        
    Useful for:
        - Monitoring long-running restore operations
        - Checking if restore completed successfully
        - Detecting if another operation is blocking backup/restore
        - Viewing warnings from the most recent restore
    """
    try:
        status = backup_service.get_restore_status()
        
        if status is None:
            # No restore operation tracked
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


@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats(_: str = Depends(verify_admin_key)):
    """
    Get current Neo4j database statistics.
    
    **Requires admin authentication.**
    
    Returns:
        Database statistics including node count, relationship count, labels, and types
        
    Example:
        ```
        GET /backup/stats
        Headers: X-Admin-Key: your-admin-key
        ```
        
    Useful for:
        - Checking database size before backup
        - Verifying restore completed successfully
        - Monitoring database growth
    """
    try:
        stats = backup_service.get_database_stats()
        
        return DatabaseStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")
