"""Restore lock middleware to prevent writes during restore operations."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.settings import settings


async def block_writes_during_restore(request: Request, call_next):
    """
    Block write operations (POST, PUT, PATCH, DELETE) during database restore.
    
    This prevents data corruption by ensuring no data modifications occur while
    the database is being restored. Read operations (GET) are allowed to continue.
    
    Exempted endpoints:
    - /backup/* (all backup/restore management endpoints)
    - /health (health check)
    - /version (version info)
    """
    # Allow all backup endpoints to proceed (they manage the restore operation)
    if request.url.path.startswith("/backup/"):
        return await call_next(request)
    
    # Allow health and version endpoints
    if request.url.path in ["/health", "/version"]:
        return await call_next(request)
    
    # Check if restore is in progress for write operations
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        try:
            # Import the appropriate backup service based on DB type
            backup_service = None
            if settings.DB_TYPE == "neo4j":
                from backend.services.neo4j.backup_service import Neo4jBackupService
                backup_service = Neo4jBackupService()
            elif settings.DB_TYPE in ["postgresql", "postgres", "mysql", "sqlite"]:
                from backend.services.sql.backup_service import BackupService
                backup_service = BackupService()
            
            if backup_service:
                lock_operation = backup_service.check_operation_lock()
                
                if lock_operation == "restore":
                    return JSONResponse(
                        status_code=503,
                        content={
                            "error": "Service temporarily unavailable",
                            "detail": f"Database restore is in progress for {settings.DB_TYPE}. Write operations are blocked to prevent data corruption.",
                            "operation_in_progress": lock_operation,
                            "database_type": settings.DB_TYPE,
                            "retry_after": "Poll GET /backup/restore-status to monitor restore progress"
                        }
                    )
        except Exception as e:
            # If we can't check the lock, allow the request (fail open)
            print(f"Warning: Failed to check restore lock: {e}")
    
    return await call_next(request)


def setup_restore_lock_middleware(app: FastAPI) -> None:
    """
    Configure restore lock middleware for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    app.middleware("http")(block_writes_during_restore)
