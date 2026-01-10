"""Backup automation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.automation import (
    DestinationCreateRequest,
    DestinationUpdateRequest,
    RunDueRequest,
    RunNowResponse,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    TargetCreateRequest,
    TargetUpdateRequest,
)
from api.security import verify_admin_key, verify_delete_key
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler
from backend.services.automation.destination_service import DestinationService
from backend.services.automation.schedule_service import ScheduleService
from backend.services.automation.target_service import TargetService


router = APIRouter(prefix="/automation", tags=["Automation"])


def _get_sql_handler() -> SQLHandler:
    """Get the configured SQL database handler.

    Returns:
        SQLHandler: SQL handler.

    Raises:
        HTTPException: If the database handler is not SQL.
    """

    handler = get_database_handler()
    if not isinstance(handler, SQLHandler):
        raise HTTPException(status_code=503, detail="Automation endpoints require a SQL database")
    return handler


@router.get("/targets")
async def list_targets(_: str = Depends(verify_admin_key)):
    """List backup targets."""

    return await TargetService(_get_sql_handler()).list_targets()


@router.post("/targets/test-connection")
async def test_target_connection(payload: TargetCreateRequest, _: str = Depends(verify_admin_key)):
    """Test connection to a backup target."""
    
    try:
        result = await TargetService(_get_sql_handler()).test_connection(
            db_type=payload.db_type,
            config=payload.config,
            secrets=payload.secrets,
        )
        return {"success": True, "message": "Connection successful", "details": result}
    except Exception as exc:
        return {"success": False, "message": str(exc), "details": None}


@router.post("/targets")
async def create_target(payload: TargetCreateRequest, _: str = Depends(verify_admin_key)):
    """Create a backup target."""

    try:
        return await TargetService(_get_sql_handler()).create_target(
            name=payload.name,
            db_type=payload.db_type,
            config=payload.config,
            secrets=payload.secrets,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/targets/{target_id}")
async def update_target(target_id: str, payload: TargetUpdateRequest, _: str = Depends(verify_admin_key)):
    """Update a backup target."""

    try:
        return await TargetService(_get_sql_handler()).update_target(
            target_id,
            name=payload.name,
            db_type=payload.db_type,
            config=payload.config,
            secrets=payload.secrets,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/targets/{target_id}")
async def delete_target(target_id: str, _: str = Depends(verify_delete_key)):
    """Delete a backup target."""

    try:
        await TargetService(_get_sql_handler()).delete_target(target_id)
        return {"status": "success"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/destinations")
async def list_destinations(_: str = Depends(verify_admin_key)):
    """List destinations."""

    return await DestinationService(_get_sql_handler()).list_destinations()


@router.post("/destinations/test-connection")
async def test_destination_connection(payload: DestinationCreateRequest, _: str = Depends(verify_admin_key)):
    """Test connection to a backup destination."""
    
    try:
        result = await DestinationService(_get_sql_handler()).test_connection(
            dest_type=payload.dest_type,
            config=payload.config,
            secrets=payload.secrets,
        )
        return {"success": True, "message": "Connection successful", "details": result}
    except Exception as exc:
        return {"success": False, "message": str(exc), "details": None}


@router.post("/destinations")
async def create_destination(payload: DestinationCreateRequest, _: str = Depends(verify_admin_key)):
    """Create a destination."""

    try:
        return await DestinationService(_get_sql_handler()).create_destination(
            name=payload.name,
            destination_type=payload.destination_type,
            config=payload.config,
            secrets=payload.secrets,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/destinations/{destination_id}")
async def update_destination(destination_id: str, payload: DestinationUpdateRequest, _: str = Depends(verify_admin_key)):
    """Update a destination."""

    try:
        return await DestinationService(_get_sql_handler()).update_destination(
            destination_id,
            name=payload.name,
            destination_type=payload.destination_type,
            config=payload.config,
            secrets=payload.secrets,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/destinations/{destination_id}")
async def delete_destination(destination_id: str, _: str = Depends(verify_delete_key)):
    """Delete a destination."""

    try:
        await DestinationService(_get_sql_handler()).delete_destination(destination_id)
        return {"status": "success"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/schedules")
async def list_schedules(_: str = Depends(verify_admin_key)):
    """List schedules."""

    return await ScheduleService(_get_sql_handler()).list_schedules()


@router.post("/schedules")
async def create_schedule(payload: ScheduleCreateRequest, _: str = Depends(verify_admin_key)):
    """Create a schedule."""

    try:
        return await ScheduleService(_get_sql_handler()).create_schedule(
            name=payload.name,
            target_id=payload.target_id,
            destination_ids=payload.destination_ids,
            interval_seconds=payload.interval_seconds,
            retention=payload.retention,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, payload: ScheduleUpdateRequest, _: str = Depends(verify_admin_key)):
    """Update a schedule."""

    try:
        return await ScheduleService(_get_sql_handler()).update_schedule(
            schedule_id,
            name=payload.name,
            target_id=payload.target_id,
            destination_ids=payload.destination_ids,
            interval_seconds=payload.interval_seconds,
            retention=payload.retention,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, _: str = Depends(verify_delete_key)):
    """Delete a schedule."""

    try:
        await ScheduleService(_get_sql_handler()).delete_schedule(schedule_id)
        return {"status": "success"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/schedules/{schedule_id}/run-now", response_model=RunNowResponse)
async def run_now(schedule_id: str, _: str = Depends(verify_admin_key)):
    """Trigger a schedule immediately."""

    try:
        return await ScheduleService(_get_sql_handler()).run_now(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runner/run-due")
async def run_due(payload: RunDueRequest, _: str = Depends(verify_admin_key)):
    """Runner endpoint to execute due schedules."""

    return await ScheduleService(_get_sql_handler()).run_due(max_schedules=payload.max_schedules)
