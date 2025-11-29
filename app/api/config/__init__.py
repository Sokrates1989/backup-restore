"""Configuration modules for the FastAPI application."""
from .openapi import setup_openapi
from .lifecycle import setup_lifecycle_events

__all__ = ["setup_openapi", "setup_lifecycle_events"]
