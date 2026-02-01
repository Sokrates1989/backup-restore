"""Schemas for backup automation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class TargetCreateRequest(BaseModel):
    """Request to create a backup target."""

    name: str = Field(..., description="Human-friendly target name")
    db_type: str = Field(..., description="Database type: neo4j|postgresql|mysql|sqlite")
    config: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive configuration")
    secrets: Dict[str, Any] = Field(default_factory=dict, description="Sensitive configuration (encrypted at rest)")


class TargetUpdateRequest(BaseModel):
    """Request to update a backup target."""

    name: Optional[str] = Field(None, description="Human-friendly target name")
    db_type: Optional[str] = Field(None, description="Database type")
    config: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive configuration")
    secrets: Optional[Dict[str, Any]] = Field(None, description="Sensitive configuration")
    is_active: Optional[bool] = Field(None, description="Active flag")


class DestinationCreateRequest(BaseModel):
    """Request to create a destination."""

    name: str = Field(..., description="Human-friendly destination name")
    destination_type: str = Field(..., description="Destination type: sftp|google_drive")
    config: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive destination config")
    secrets: Dict[str, Any] = Field(default_factory=dict, description="Sensitive destination config")


class DestinationUpdateRequest(BaseModel):
    """Request to update a destination."""

    name: Optional[str] = Field(None, description="Human-friendly destination name")
    destination_type: Optional[str] = Field(None, description="Destination type")
    config: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive destination config")
    secrets: Optional[Dict[str, Any]] = Field(None, description="Sensitive destination config")
    is_active: Optional[bool] = Field(None, description="Active flag")


class ScheduleCreateRequest(BaseModel):
    """Request to create a schedule."""

    name: str = Field(..., description="Human-friendly schedule name")
    target_id: str = Field(..., description="Backup target id")
    destination_ids: List[str] = Field(default_factory=list, description="Destination ids")
    interval_seconds: int = Field(86400, description="Interval in seconds")
    retention: Dict[str, Any] = Field(default_factory=dict, description="Retention policy and schedule options")
    enabled: bool = Field(True, description="Whether schedule is enabled")


class ScheduleUpdateRequest(BaseModel):
    """Request to update a schedule."""

    name: Optional[str] = Field(None, description="Human-friendly schedule name")
    target_id: Optional[str] = Field(None, description="Backup target id")
    destination_ids: Optional[List[str]] = Field(None, description="Destination ids")
    interval_seconds: Optional[int] = Field(None, description="Interval in seconds")
    retention: Optional[Dict[str, Any]] = Field(None, description="Retention policy and schedule options")
    enabled: Optional[bool] = Field(None, description="Whether schedule is enabled")


class RunDueRequest(BaseModel):
    """Request for runner to execute due schedules."""

    max_schedules: int = Field(10, description="Maximum number of schedules to execute")


class RunEnabledNowRequest(BaseModel):
    """Request to execute enabled schedules immediately."""

    max_schedules: int = Field(50, description="Maximum number of schedules to execute")


class RunNowResponse(BaseModel):
    """Response after triggering a schedule execution."""

    run_id: str
    status: str
    backup_filename: Optional[str] = None
    uploads: List[Dict[str, Any]] = Field(default_factory=list)


class BackupNowRequest(BaseModel):
    """Request to perform an immediate backup."""

    target_id: str = Field(..., description="Backup target id")
    destination_ids: List[str] = Field(default_factory=list, description="Destination ids to upload backup to")
    use_local_storage: bool = Field(False, description="Use default local storage (/app/backups) instead of destinations")
    encryption_password: Optional[str] = Field(
        None,
        description=(
            "Optional password to encrypt manual backups before upload. "
            "When provided, the backup artifact is encrypted and stored with a .enc suffix."
        ),
    )


class BackupNowResponse(BaseModel):
    """Response after performing an immediate backup."""

    run_id: str
    status: str
    backup_filename: Optional[str] = None
    uploads: List[Dict[str, Any]] = Field(default_factory=list)


class RestoreNowRequest(BaseModel):
    """Request to perform an immediate restore."""

    target_id: str = Field(..., description="Backup target id to restore to")
    destination_id: Optional[str] = Field(None, description="Destination id to restore from")
    backup_id: str = Field(..., description="Backup file id or name to restore")
    encryption_password: Optional[str] = Field(
        None,
        description="Password for decrypting encrypted backups (required when restoring encrypted artifacts)",
    )
    confirmation: str = Field(..., description='Type RESTORE to confirm the restore operation')
    use_local_storage: bool = Field(False, description="Restore from default local storage (/app/backups)")


class RestoreNowResponse(BaseModel):
    """Response after performing a restore."""

    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
