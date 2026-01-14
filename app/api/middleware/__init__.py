"""Middleware configuration for the FastAPI application."""
from fastapi import FastAPI
from .restore_lock import setup_restore_lock_middleware
from .logging import setup_logging_middleware
from .security_headers import setup_security_headers_middleware


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application.
    
    Middleware are applied in the order they are called:
    1. Restore lock middleware (blocks writes during restore)
    2. Logging middleware (debug only)
    3. Security headers middleware (CSP)
    
    Args:
        app: The FastAPI application instance
    """
    setup_restore_lock_middleware(app)
    setup_logging_middleware(app)
    setup_security_headers_middleware(app)
