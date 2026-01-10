"""ExampleNode Neo4j CRUD API routes.

These endpoints are used by the repository's test scripts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Any, Dict, Optional

from backend.services.neo4j.example_node_service import ExampleNodeService


router = APIRouter(prefix="/example-nodes", tags=["Example Nodes"])


class ExampleNodeCreateRequest(BaseModel):
    """Request model for creating an example node."""

    name: str
    description: Optional[str] = None


class ExampleNodeUpdateRequest(BaseModel):
    """Request model for updating an example node."""

    name: Optional[str] = None
    description: Optional[str] = None


@router.post("/")
async def create_node(payload: ExampleNodeCreateRequest) -> Dict[str, Any]:
    """Create a node."""

    try:
        service = ExampleNodeService()
        node = await run_in_threadpool(service.create, payload.name, payload.description)
        return {"status": "success", "data": node.model_dump()}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/")
async def list_nodes(skip: int = 0, limit: int = 100, name: Optional[str] = None) -> Dict[str, Any]:
    """List nodes."""

    try:
        service = ExampleNodeService()
        items = await run_in_threadpool(service.get_all, skip, limit, name)
        total = await run_in_threadpool(service.count, name)
        return {
            "status": "success",
            "data": {
                "items": [n.model_dump() for n in items],
                "total": total,
                "skip": skip,
                "limit": limit,
            },
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{node_id}")
async def get_node(node_id: str) -> Dict[str, Any]:
    """Get a node."""

    try:
        service = ExampleNodeService()
        node = await run_in_threadpool(service.get_by_id, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "success", "data": node.model_dump()}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.put("/{node_id}")
async def update_node(node_id: str, payload: ExampleNodeUpdateRequest) -> Dict[str, Any]:
    """Update a node."""

    try:
        service = ExampleNodeService()
        node = await run_in_threadpool(service.update, node_id, payload.name, payload.description)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "success", "data": node.model_dump()}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/{node_id}")
async def delete_node(node_id: str) -> Dict[str, Any]:
    """Delete a node."""

    try:
        service = ExampleNodeService()
        deleted = await run_in_threadpool(service.delete, node_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "success", "message": f"Node {node_id} deleted"}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/")
async def delete_all_nodes() -> Dict[str, Any]:
    """Delete all nodes."""

    try:
        service = ExampleNodeService()
        deleted = await run_in_threadpool(service.delete_all)
        return {"status": "success", "message": f"Deleted {deleted} nodes"}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
