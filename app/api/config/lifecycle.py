"""Application lifecycle event handlers."""
from fastapi import FastAPI
from api.settings import settings
from api.logging_config import get_logger
from backend.database import initialize_database, close_database
from backend.database.migrations import run_migrations

logger = get_logger(__name__)


def setup_lifecycle_events(app: FastAPI) -> None:
    """
    Configure application lifecycle events (startup and shutdown).
    
    Args:
        app: The FastAPI application instance
    """
    @app.on_event("startup")
    async def startup_event():
        """Initialize database connection and run migrations on startup."""
        if settings.DB_MODE == "standalone":
            logger.info("DB_MODE=standalone - skipping internal database initialization and migrations.")
            return

        try:
            await initialize_database()
            # Run database migrations automatically
            logger.info(" About to run migrations...")
            run_migrations()
            logger.info(" Migrations completed (or skipped)")
        except Exception:
            logger.exception(" Error during startup")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Close database connection on shutdown."""
        logger.info("Shutting down...")
        await close_database()
