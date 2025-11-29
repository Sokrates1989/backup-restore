# Entry point for the FastAPI app
from fastapi import FastAPI
from api.settings import settings
from api.routes import sql_backup, neo4j_backup
from api.middleware import setup_middleware
from api.config import setup_openapi, setup_lifecycle_events

# Initialize FastAPI application
app = FastAPI(
    title="Backup & Restore Service",
    description="Database backup and restore service supporting SQL (PostgreSQL, MySQL, SQLite) and Neo4j databases, both local and remote",
    version=settings.IMAGE_TAG
)

# Configure OpenAPI and lifecycle events
setup_openapi(app)
setup_lifecycle_events(app)

# Include backup routers
app.include_router(sql_backup.router)
print(f"✅ Registered SQL backup/restore routes (/backup/sql/*)")
app.include_router(neo4j_backup.router)
print(f"✅ Registered Neo4j backup/restore routes (/backup/neo4j/*)")

# Setup middleware
setup_middleware(app)

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