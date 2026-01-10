"""Basic test endpoints.

These endpoints are used by `testing/scripts/test-api.sh`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.database_service import DatabaseService


router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/db-test")
async def test_db_connection():
    """Test database connection."""

    return await DatabaseService().test_connection()


@router.get("/db-info")
async def get_db_info():
    """Get database info."""

    return await DatabaseService().get_database_info()


@router.get("/sample-query")
async def sample_query():
    """Execute a sample query based on configured DB type."""

    return await DatabaseService().execute_sample_query()


@router.get("/db-sample-query")
async def sample_query_legacy():
    """Legacy alias for sample query."""

    return await DatabaseService().execute_sample_query()
