# Entry point for the FastAPI app
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.settings import settings
from api.logging_config import configure_logging, get_logger
from api.routes import sql_backup, neo4j_backup
from api.routes import automation, examples, example_nodes, legacy_backup, test_routes, files
from api.middleware import setup_middleware
from api.config import setup_openapi, setup_lifecycle_events

try:
    configure_logging(
        log_dir=settings.LOG_DIR,
        log_level=settings.LOG_LEVEL,
        debug=settings.DEBUG,
        log_filename=settings.LOG_FILENAME,
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT,
    )
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
logger = get_logger(__name__)

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
logger.info("✅ Registered SQL backup/restore routes (/backup/sql/*)")
app.include_router(neo4j_backup.router)
logger.info("✅ Registered Neo4j backup/restore routes (/backup/neo4j/*)")

app.include_router(automation.router)
logger.info("✅ Registered automation routes (/automation/*)")

app.include_router(examples.router)
logger.info("✅ Registered example CRUD routes (/examples/*)")

app.include_router(example_nodes.router)
logger.info("✅ Registered Neo4j example node routes (/example-nodes/*)")

app.include_router(legacy_backup.router)
logger.info("✅ Registered legacy backup routes (/backup/*)")

app.include_router(test_routes.router)
logger.info("✅ Registered test routes (/test/*)")

app.include_router(files.router)
logger.info("✅ Registered file routes (/files/*)")

# Setup middleware
setup_middleware(app)

# Health check endpoint.
@app.get("/health")
def check_health():
    """Health check endpoint."""
    return {"status": "OK"}

# Get Image version.
@app.get("/version")
def get_version():
    """Return the running image tag/version."""
    return {"IMAGE_TAG": f"{settings.IMAGE_TAG}"}

# # Test endpoint for hot-reloading demonstration
# @app.get("/hot-reload-test")
# def hot_reload_test():
#     return {"message": "This endpoint was added while the container was running!", "timestamp": "2024-01-01"}

# Serve website static files
WEBSITE_DIR = Path("/app/website")
if WEBSITE_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEBSITE_DIR)), name="static")
    logger.info("✅ Mounted website static files at /static")

    @app.get("/")
    async def serve_index():
        """Serve the main web UI."""
        return FileResponse(WEBSITE_DIR / "index.html")

    @app.get("/{filename:path}")
    async def serve_static(filename: str):
        """Serve static files from the website directory."""
        file_path = WEBSITE_DIR / filename
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA routing
        return FileResponse(WEBSITE_DIR / "index.html")