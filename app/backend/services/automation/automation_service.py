"""Automation service for scheduled backups.

This service persists automation configuration in the SQL database and executes
scheduled backups against configured targets, uploading them to one or more
destinations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler
from backend.services.automation.destination_service import DestinationService
from backend.services.automation.schedule_service import ScheduleService
from backend.services.automation.target_service import TargetService


class AutomationService:
    """Compatibility facade for backup automation.

    The project has been refactored into smaller services:
    - TargetService
    - DestinationService
    - ScheduleService

    This class is kept as a thin wrapper to avoid breaking older imports.
    """

    def __init__(self):
        """Initialize the automation service.

        Raises:
            ValueError: If the configured database handler is not SQL.
        """

        handler = get_database_handler()
        if not isinstance(handler, SQLHandler):
            raise ValueError("AutomationService requires SQL database")
        self.handler: SQLHandler = handler

    def _targets(self) -> TargetService:
        """Create a TargetService instance.

        Returns:
            TargetService: Service instance.
        """

        return TargetService(self.handler)

    def _destinations(self) -> DestinationService:
        """Create a DestinationService instance.

        Returns:
            DestinationService: Service instance.
        """

        return DestinationService(self.handler)

    def _schedules(self) -> ScheduleService:
        """Create a ScheduleService instance.

        Returns:
            ScheduleService: Service instance.
        """

        return ScheduleService(self.handler)

    async def list_targets(self) -> List[Dict[str, Any]]:
        """List configured backup targets."""

        return await self._targets().list_targets()

    async def create_target(self, *, name: str, db_type: str, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Create a backup target."""

        return await self._targets().create_target(name=name, db_type=db_type, config=config, secrets=secrets)

    async def update_target(
        self,
        target_id: str,
        *,
        name: Optional[str] = None,
        db_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a backup target."""

        return await self._targets().update_target(
            target_id,
            name=name,
            db_type=db_type,
            config=config,
            secrets=secrets,
            is_active=is_active,
        )

    async def delete_target(self, target_id: str) -> None:
        """Delete a backup target."""

        await self._targets().delete_target(target_id)

    async def list_destinations(self) -> List[Dict[str, Any]]:
        """List configured destinations."""

        return await self._destinations().list_destinations()

    async def create_destination(
        self,
        *,
        name: str,
        destination_type: str,
        config: Dict[str, Any],
        secrets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a backup destination."""

        return await self._destinations().create_destination(
            name=name,
            destination_type=destination_type,
            config=config,
            secrets=secrets,
        )

    async def update_destination(
        self,
        destination_id: str,
        *,
        name: Optional[str] = None,
        destination_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a destination."""

        return await self._destinations().update_destination(
            destination_id,
            name=name,
            destination_type=destination_type,
            config=config,
            secrets=secrets,
            is_active=is_active,
        )

    async def delete_destination(self, destination_id: str) -> None:
        """Delete a destination."""

        await self._destinations().delete_destination(destination_id)

    async def list_schedules(self) -> List[Dict[str, Any]]:
        """List configured schedules."""

        return await self._schedules().list_schedules()

    async def create_schedule(
        self,
        *,
        name: str,
        target_id: str,
        destination_ids: List[str],
        interval_seconds: int,
        retention: Dict[str, Any],
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Create a schedule."""

        return await self._schedules().create_schedule(
            name=name,
            target_id=target_id,
            destination_ids=destination_ids,
            interval_seconds=interval_seconds,
            retention=retention,
            enabled=enabled,
        )

    async def update_schedule(
        self,
        schedule_id: str,
        *,
        name: Optional[str] = None,
        target_id: Optional[str] = None,
        destination_ids: Optional[List[str]] = None,
        interval_seconds: Optional[int] = None,
        retention: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a schedule."""

        return await self._schedules().update_schedule(
            schedule_id,
            name=name,
            target_id=target_id,
            destination_ids=destination_ids,
            interval_seconds=interval_seconds,
            retention=retention,
            enabled=enabled,
        )

    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""

        await self._schedules().delete_schedule(schedule_id)

    async def run_now(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule immediately."""

        return await self._schedules().run_now(schedule_id)

    async def run_due(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute all due schedules."""

        return await self._schedules().run_due(max_schedules=max_schedules)
