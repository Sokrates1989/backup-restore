# Entry point for the FastAPI app
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from api.settings import settings
from api.routes import sql_backup, neo4j_backup
from backend.database import initialize_database, close_database
from backend.database.migrations import run_migrations

app = FastAPI(
    title="Backup & Restore Service",
    description="Database backup and restore service supporting SQL (PostgreSQL, MySQL, SQLite) and Neo4j databases, both local and remote",
    version=settings.IMAGE_TAG
)

# Configure OpenAPI security schemes for Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Define security schemes that will appear in Swagger UI "Authorize" button
    openapi_schema["components"]["securitySchemes"] = {
        "X-Admin-Key": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Admin-Key",
            "description": "Admin API Key for backup operations (download backups)"
        },
        "X-Restore-Key": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Restore-Key",
            "description": "Restore API Key for restore operations (overwrites database)"
        }
    }
    
    # Add security requirements to backup endpoints
    for path, path_item in openapi_schema.get("paths", {}).items():
        if path.startswith("/backup/"):
            for method, operation in path_item.items():
                if method in ["get", "post", "delete", "put", "patch"]:
                    # Determine which security scheme based on endpoint
                    if "restore" in path:
                        operation["security"] = [{"X-Restore-Key": []}]
                    else:
                        operation["security"] = [{"X-Admin-Key": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection and run migrations on startup."""
    if settings.DB_MODE == "standalone":
        print("DB_MODE=standalone - skipping internal database initialization and migrations.")
        return

    try:
        await initialize_database()
        # Run database migrations automatically
        print("🔄 About to run migrations...")
        run_migrations()
        print("🔄 Migrations completed (or skipped)")
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    await close_database()

# Include backup routers
app.include_router(sql_backup.router)
print(f"✅ Registered SQL backup/restore routes (/backup/sql/*)")
app.include_router(neo4j_backup.router)
print(f"✅ Registered Neo4j backup/restore routes (/backup/neo4j/*)")

# Middleware to block write operations during restore
@app.middleware("http")
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


# Middleware to log request headers, if Debug is enabled in env variables.
if settings.DEBUG:
    @app.middleware("http")
    async def log_request_headers(request: Request, call_next):

        # Output basic request info.
        print(f"🔹 Received request: {request.method} {request.url}")

        # Read and log the request headers.
        headers = request.headers
        print(f"🔹 Request headers: {headers}")

        # Read and log the request body
        body = await request.body()
        print(f"🔹 Request body: {body.decode('utf-8') if body else 'No Body'}")

        response = await call_next(request)

        # Collect the response body so it can be logged and re-sent.
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        print(f"🟪 Response status: {response.status_code}")
        print(f"🟪 Response headers: {dict(response.headers)}")
        
        # Only decode text responses, skip binary content (like gzipped files)
        content_type = response.headers.get('content-type', '')
        if response_body:
            # Check if it's a binary content type
            is_binary = any(binary_type in content_type.lower() for binary_type in 
                          ['application/octet-stream', 'application/gzip', 'application/zip', 
                           'image/', 'video/', 'audio/', 'application/pdf'])
            
            if is_binary:
                print(f"🟪 Response body: <Binary content, {len(response_body)} bytes>")
            else:
                try:
                    print(f"🟪 Response body: {response_body.decode('utf-8')}")
                except UnicodeDecodeError:
                    print(f"🟪 Response body: <Binary content, {len(response_body)} bytes>")
        else:
            print(f"🟪 Response body: No Body")

        # call_next returns a streaming Response whose body_iterator can only be consumed once.
        # We iterate above to log the payload, so we must rebuild the Response to forward the body.
        # Only pass background if it exists to avoid "await None" error.
        response_kwargs = {
            "content": response_body,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "media_type": response.media_type,
        }
        
        # Only add background if it's not None (avoids TypeError: object NoneType can't be used in 'await' expression)
        if response.background is not None:
            response_kwargs["background"] = response.background
        
        new_response = Response(**response_kwargs)
        return new_response


# Health check endpoint.
@app.get("/health")
def check_health():
    return {"status": "OK"}

# Get Image version.
@app.get("/version")
def get_version():
    return {"IMAGE_TAG": f"{settings.IMAGE_TAG}"}

# # Test endpoint for hot-reloading demonstration
# @app.get("/hot-reload-test")
# def hot_reload_test():
#     return {"message": "This endpoint was added while the container was running!", "timestamp": "2024-01-01"}