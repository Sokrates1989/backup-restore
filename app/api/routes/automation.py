"""Backup automation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.schemas.automation import (
    BackupNowRequest,
    BackupNowResponse,
    DestinationCreateRequest,
    DestinationUpdateRequest,
    RestoreNowRequest,
    RestoreNowResponse,
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
from models.sql.backup_automation import BackupRun, BackupSchedule, BackupTarget


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

    service = DestinationService(_get_sql_handler())
    await service.ensure_local_destination_exists()
    return await service.list_destinations()


@router.post("/destinations/test-connection")
async def test_destination_connection(payload: DestinationCreateRequest, _: str = Depends(verify_admin_key)):
    """Test connection to a backup destination."""
    
    try:
        result = await DestinationService(_get_sql_handler()).test_connection(
            dest_type=payload.destination_type,
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
        await DestinationService(_get_sql_handler()).ensure_local_destination_exists()
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
        await DestinationService(_get_sql_handler()).ensure_local_destination_exists()
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
        raise HTTPException(status_code=404, detail=str(exc))


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


@router.post("/backup-now", response_model=BackupNowResponse)
async def backup_now(payload: BackupNowRequest, _: str = Depends(verify_admin_key)):
    """Perform an immediate backup of a target to specified destinations."""

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        result = await service.backup_now(
            target_id=payload.target_id,
            destination_ids=payload.destination_ids,
            use_local_storage=payload.use_local_storage,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/restore-now", response_model=RestoreNowResponse)
async def restore_now(payload: RestoreNowRequest, _: str = Depends(verify_admin_key)):
    """Perform an immediate restore from a backup."""

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        result = await service.restore_now(
            target_id=payload.target_id,
            destination_id=payload.destination_id,
            backup_id=payload.backup_id,
            use_local_storage=payload.use_local_storage,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs")
async def list_runs(_: str = Depends(verify_admin_key)):
    """List recent backup runs (scheduled + immediate)."""

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        result = await session.execute(
            select(BackupRun, BackupSchedule, BackupTarget)
            .select_from(BackupRun)
            .outerjoin(BackupSchedule, BackupRun.schedule_id == BackupSchedule.id)
            .outerjoin(BackupTarget, BackupSchedule.target_id == BackupTarget.id)
            .order_by(BackupRun.started_at.desc())
            .limit(200)
        )

        items = []
        for run, sched, target in result.all():
            uploads = (run.details or {}).get("uploads") if isinstance(run.details, dict) else None
            first_upload = uploads[0] if isinstance(uploads, list) and uploads else None

            immediate_target_name = None
            if not target and isinstance(run.details, dict):
                raw_target_id = run.details.get("target_id")
                if raw_target_id:
                    t = await session.get(BackupTarget, raw_target_id)
                    if t:
                        immediate_target_name = t.name

            items.append(
                {
                    "id": run.id,
                    "schedule_id": run.schedule_id,
                    "schedule_name": getattr(sched, "name", None) if sched else None,
                    "target_id": getattr(sched, "target_id", None) if sched else None,
                    "target_name": getattr(target, "name", None) if target else (immediate_target_name or None),
                    "status": run.status,
                    "backup_filename": run.backup_filename,
                    "created_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "error_message": run.error_message,
                    "destination_id": first_upload.get("destination_id") if isinstance(first_upload, dict) else None,
                    "destination_name": first_upload.get("destination_name") if isinstance(first_upload, dict) else None,
                    "file_size_mb": None,
                }
            )

        return items


@router.get("/runs/{run_id}")
async def get_run(run_id: str, _: str = Depends(verify_admin_key)):
    """Get a single backup run by id."""

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        run = await session.get(BackupRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        schedule = None
        target = None
        if run.schedule_id:
            schedule = await session.get(BackupSchedule, run.schedule_id)
            if schedule:
                target = await session.get(BackupTarget, schedule.target_id)

        return {
            "id": run.id,
            "schedule_id": run.schedule_id,
            "schedule_name": schedule.name if schedule else None,
            "target_id": schedule.target_id if schedule else None,
            "target_name": target.name if target else None,
            "status": run.status,
            "backup_filename": run.backup_filename,
            "created_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "details": run.details,
            "error_message": run.error_message,
        }


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str, _: str = Depends(verify_delete_key)):
    """Delete a run record (does not delete stored backup files)."""

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        run = await session.get(BackupRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        await session.delete(run)
        await session.commit()
        return {"status": "success"}


@router.get("/destinations/{destination_id}/backups")
async def list_destination_backups(
    destination_id: str,
    target_id: str = None,
    _: str = Depends(verify_admin_key),
):
    """List backup files available at a destination, optionally filtered by target."""

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        return await service.list_backups(destination_id=destination_id, target_id=target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
