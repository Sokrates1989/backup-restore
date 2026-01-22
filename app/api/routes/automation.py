"""Backup automation API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy import func, select

from api.schemas.automation import (
    BackupNowRequest,
    BackupNowResponse,
    DestinationCreateRequest,
    DestinationUpdateRequest,
    RunEnabledNowRequest,
    RestoreNowRequest,
    RestoreNowResponse,
    RunDueRequest,
    RunNowResponse,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    TargetCreateRequest,
    TargetUpdateRequest,
)
from api.security import verify_admin_key, verify_delete_key, verify_download_key, verify_history_key, verify_restore_key
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler
from backend.services.automation.destination_service import DestinationService
from backend.services.automation.schedule_service import ScheduleService
from backend.services.automation.target_service import TargetService
from models.sql.backup_automation import AuditEvent, BackupRun, BackupSchedule, BackupTarget


router = APIRouter(prefix="/automation", tags=["Automation"])


def _audit_event_to_dict(event: AuditEvent) -> dict:
    """Convert an AuditEvent to a response dictionary.

    Args:
        event: Audit event.

    Returns:
        dict: Serializable audit event payload.
    """

    return {
        "id": event.id,
        "operation": event.operation,
        "trigger": event.trigger,
        "status": event.status,
        "started_at": event.started_at.isoformat() if event.started_at else None,
        "finished_at": event.finished_at.isoformat() if event.finished_at else None,
        "target_id": event.target_id,
        "target_name": event.target_name,
        "destination_id": event.destination_id,
        "destination_name": event.destination_name,
        "schedule_id": event.schedule_id,
        "schedule_name": event.schedule_name,
        "backup_id": event.backup_id,
        "backup_name": event.backup_name,
        "run_id": event.run_id,
        "user_id": event.user_id,
        "user_name": event.user_name,
        "details": event.details,
        "error_message": event.error_message,
    }


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


@router.get("/audit")
async def list_audit_events(
    target_id: str | None = Query(None, description="Optional target_id filter"),
    operation: str | None = Query(None, description="Optional operation filter"),
    trigger: str | None = Query(None, description="Optional trigger filter (manual|scheduled|system|non_scheduled)"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    include_total: bool = Query(False, description="When true return a wrapper with total count"),
    _: str = Depends(verify_history_key),
):
    """List recent audit events with optional filtering.

    Args:
        target_id: Optional target_id filter.
        operation: Optional operation filter.
        trigger: Optional trigger filter.
        limit: Maximum number of events to return.
        offset: Pagination offset (0-based).
        include_total: When True, return a wrapper object that includes total count.

    Returns:
        When include_total is False (default), returns a list of audit events.
        When include_total is True, returns a dict with items and pagination metadata.
    """

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        filters = []
        if target_id:
            filters.append(AuditEvent.target_id == target_id)
        if operation:
            filters.append(AuditEvent.operation == operation)
        if trigger:
            if trigger == "non_scheduled":
                filters.append(AuditEvent.trigger != "scheduled")
            else:
                filters.append(AuditEvent.trigger == trigger)

        total = None
        if include_total:
            total_stmt = select(func.count()).select_from(AuditEvent)
            if filters:
                total_stmt = total_stmt.where(*filters)
            total = await session.scalar(total_stmt)

        stmt = select(AuditEvent).order_by(AuditEvent.started_at.desc()).limit(limit).offset(offset)
        if filters:
            stmt = stmt.where(*filters)

        result = await session.execute(stmt)
        events = list(result.scalars().all())
        items = [_audit_event_to_dict(e) for e in events]

        if include_total:
            return {
                "items": items,
                "total": int(total or 0),
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            }

        return items


@router.get("/audit/{event_id}")
async def get_audit_event(event_id: str, _: str = Depends(verify_history_key)):
    """Get a single audit event by id."""

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        event = await session.get(AuditEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Audit event not found: {event_id}")
        return _audit_event_to_dict(event)


@router.post("/audit/login")
async def log_login_event(
    user_id: str = Depends(verify_admin_key),
):
    """Log a user login event to the audit trail.

    This endpoint should be called by the frontend after successful Keycloak authentication
    to record when a user accessed the backup manager UI.

    Returns:
        dict: Created audit event summary.
    """

    from datetime import datetime, timezone

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        # Extract username from user_id (format: "keycloak:username")
        user_name = user_id.split(":", 1)[-1] if ":" in user_id else user_id

        event = AuditEvent(
            operation="login",
            trigger="manual",
            status="success",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            user_id=user_id,
            user_name=user_name,
            details={"action": "User logged in to backup manager UI"},
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        return {
            "id": event.id,
            "operation": event.operation,
            "user_name": event.user_name,
            "started_at": event.started_at.isoformat() if event.started_at else None,
        }


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


@router.post("/schedules/run-enabled-now")
async def run_enabled_now(payload: RunEnabledNowRequest, _: str = Depends(verify_admin_key)):
    """Execute enabled schedules immediately."""

    return await ScheduleService(_get_sql_handler()).run_enabled_now(max_schedules=payload.max_schedules)


@router.get("/destinations/{destination_id}/backups/download")
async def download_destination_backup(
    destination_id: str,
    backup_id: str = Query(..., description="Provider-specific backup identifier"),
    filename: str | None = Query(None, description="Optional download filename"),
    _: str = Depends(verify_download_key),
):
    """Download a backup file from a destination.

    This endpoint streams a backup file stored in a remote destination (SFTP / Google Drive)
    or local storage. The backend will download the file into a temporary location and then
    stream it to the client.

    Args:
        destination_id: Destination ID.
        backup_id: Provider-specific backup identifier (e.g. SFTP remote path, Drive file id).
        filename: Optional filename to use for the downloaded file.

    Returns:
        FileResponse: Streaming file response.

    Raises:
        HTTPException: When download fails.
    """

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        temp_path = await service.download_backup_from_destination(
            destination_id=destination_id,
            backup_id=backup_id,
            filename=filename,
        )

        download_name = Path(str(filename or backup_id)).name or "backup"

        def _cleanup() -> None:
            try:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

        return FileResponse(path=temp_path, filename=download_name, background=BackgroundTask(_cleanup))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/destinations/{destination_id}/backups/delete")
async def delete_destination_backup(
    destination_id: str,
    backup_id: str = Query(..., description="Provider-specific backup identifier"),
    name: str | None = Query(None, description="Optional display name"),
    _: str = Depends(verify_admin_key),
    __: str = Depends(verify_delete_key),
):
    """Delete a backup file from a destination.

    Args:
        destination_id: Destination ID.
        backup_id: Provider-specific backup identifier.
        name: Optional display name.

    Returns:
        Dict[str, str]: Status response.

    Raises:
        HTTPException: When deletion fails.
    """

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        await service.delete_backup_from_destination(destination_id=destination_id, backup_id=backup_id, name=name)
        return {"status": "success"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
async def restore_now(
    payload: RestoreNowRequest,
    _: str = Depends(verify_admin_key),
    __: str = Depends(verify_restore_key),
):
    """Perform an immediate restore from a backup."""

    if (payload.confirmation or "").strip() != "RESTORE":
        raise HTTPException(
            status_code=400,
            detail='Typed confirmation required: confirmation must equal "RESTORE"',
        )

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        result = await service.restore_now(
            target_id=payload.target_id,
            destination_id=payload.destination_id,
            backup_id=payload.backup_id,
            encryption_password=payload.encryption_password,
            use_local_storage=payload.use_local_storage,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs")
async def list_runs(
    limit: int = Query(200, ge=1, le=1000, description="Max runs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    include_total: bool = Query(False, description="When true return a wrapper with total count"),
    _: str = Depends(verify_admin_key),
):
    """List recent backup runs (scheduled + immediate).

    Args:
        limit: Maximum number of runs to return.
        offset: Pagination offset (0-based).
        include_total: When True, return a wrapper object that includes total count.

    Returns:
        When include_total is False (default), returns a list of run dictionaries.
        When include_total is True, returns a dict with items and pagination metadata.
    """

    handler = _get_sql_handler()
    async with handler.AsyncSessionLocal() as session:
        total = None
        if include_total:
            total = await session.scalar(select(func.count()).select_from(BackupRun))

        result = await session.execute(
            select(BackupRun, BackupSchedule, BackupTarget)
            .select_from(BackupRun)
            .outerjoin(BackupSchedule, BackupRun.schedule_id == BackupSchedule.id)
            .outerjoin(BackupTarget, BackupSchedule.target_id == BackupTarget.id)
            .order_by(BackupRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        )

        items = []
        for run, sched, target in result.all():
            uploads = (run.details or {}).get("uploads") if isinstance(run.details, dict) else None
            first_upload = uploads[0] if isinstance(uploads, list) and uploads else None

            size_mb = None
            if isinstance(first_upload, dict):
                raw_size = first_upload.get("size")
                try:
                    if raw_size is not None:
                        size_mb = round(float(raw_size) / (1024 * 1024), 4)
                except Exception:
                    size_mb = None

            immediate_target_name = None
            immediate_target_id = None
            if not target and isinstance(run.details, dict):
                raw_target_id = run.details.get("target_id")
                if raw_target_id:
                    immediate_target_id = str(raw_target_id)
                    t = await session.get(BackupTarget, raw_target_id)
                    if t:
                        immediate_target_name = t.name

                if not immediate_target_name:
                    raw_target_name = run.details.get("target_name")
                    if raw_target_name:
                        immediate_target_name = str(raw_target_name)

            # Backward compatibility: older immediate runs overwrote details and lost target_id.
            # Try to extract target name from backup_filename pattern: manual-<target>-backup_...
            if not target and not immediate_target_name and run.backup_filename:
                fn = str(run.backup_filename)
                if fn.startswith("manual-"):
                    # Expected: manual-<target>-backup_...
                    marker = "-backup_"
                    idx = fn.find(marker)
                    if idx > len("manual-"):
                        immediate_target_name = fn[len("manual-") : idx]

            items.append(
                {
                    "id": run.id,
                    "schedule_id": run.schedule_id,
                    "schedule_name": getattr(sched, "name", None) if sched else None,
                    "target_id": (getattr(sched, "target_id", None) if sched else None) or immediate_target_id,
                    "target_name": getattr(target, "name", None) if target else (immediate_target_name or None),
                    "status": run.status,
                    "backup_filename": run.backup_filename,
                    "created_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "error_message": run.error_message,
                    "destination_id": first_upload.get("destination_id") if isinstance(first_upload, dict) else None,
                    "destination_name": first_upload.get("destination_name") if isinstance(first_upload, dict) else None,
                    "file_size_mb": size_mb,
                }
            )

        if include_total:
            return {
                "items": items,
                "total": int(total or 0),
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            }

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
    target_id: str | None = Query(None, description="Optional target_id filter"),
    limit: int | None = Query(None, ge=1, le=10000, description="Max backups to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    include_total: bool = Query(False, description="When true return a wrapper with total count"),
    _: str = Depends(verify_admin_key),
):
    """List backup files available at a destination, optionally filtered by target.

    Args:
        destination_id: Destination id.
        target_id: Optional target id.
        limit: Optional maximum number of backups to return. When omitted, all backups are returned.
        offset: Pagination offset (0-based).
        include_total: When True, return a wrapper object that includes total count.

    Returns:
        When include_total is False (default), returns a list of backups.
        When include_total is True, returns a dict with items and pagination metadata.
    """

    from backend.services.automation.backup_service import BackupExecutionService

    try:
        service = BackupExecutionService(_get_sql_handler())
        items = await service.list_backups(destination_id=destination_id, target_id=target_id)

        total = len(items) if isinstance(items, list) else 0
        paged = items
        if limit is not None and isinstance(items, list):
            start = min(offset, total)
            end = min(start + limit, total)
            paged = items[start:end]

        if include_total:
            effective_limit = limit if limit is not None else total
            return {
                "items": paged,
                "total": total,
                "limit": effective_limit,
                "offset": offset,
                "returned": len(paged) if isinstance(paged, list) else 0,
            }

        return paged
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
