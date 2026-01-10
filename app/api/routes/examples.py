"""Example SQL CRUD API routes.

These endpoints are used by the repository's test scripts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from backend.services.sql.example_service import ExampleService


router = APIRouter(prefix="/examples", tags=["Examples"])


class ExampleCreateRequest(BaseModel):
    """Request model for creating an example."""

    name: str
    description: Optional[str] = None


class ExampleUpdateRequest(BaseModel):
    """Request model for updating an example."""

    name: Optional[str] = None
    description: Optional[str] = None


@router.post("/")
async def create_example(payload: ExampleCreateRequest) -> Dict[str, Any]:
    """Create a new example."""

    try:
        return await ExampleService().create_example(name=payload.name, description=payload.description)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{example_id}")
async def get_example(example_id: str) -> Dict[str, Any]:
    """Get an example by id."""

    try:
        return await ExampleService().get_example(example_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/")
async def list_examples(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List examples.

    Note:
        The response includes `total` at the top-level for compatibility with
        older test scripts.
    """

    try:
        result = await ExampleService().list_examples(limit=limit, offset=offset)
        total = 0
        if isinstance(result, dict):
            pagination = result.get("pagination") or {}
            total = int(pagination.get("total", 0) or 0)
            result.setdefault("total", total)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.put("/{example_id}")
async def update_example(example_id: str, payload: ExampleUpdateRequest) -> Dict[str, Any]:
    """Update an example."""

    try:
        return await ExampleService().update_example(
            example_id,
            name=payload.name,
            description=payload.description,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/{example_id}")
async def delete_example(example_id: str) -> Dict[str, Any]:
    """Delete an example."""

    try:
        return await ExampleService().delete_example(example_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
