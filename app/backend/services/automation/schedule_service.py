"""Schedule CRUD and execution service for backup automation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.database.sql_handler import SQLHandler
from backend.services.automation.executor import ScheduleExecutor
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import schedule_to_dict


class ScheduleService:
    """Service for managing backup schedules and executing them."""

    def __init__(self, handler: SQLHandler):
        """Initialize the service.

        Args:
            handler: SQL handler.
        """

        self.handler = handler
        self.repo = AutomationRepository()

    async def list_schedules(self) -> List[Dict[str, Any]]:
        """List schedules."""

        async with self.handler.AsyncSessionLocal() as session:
            items = await self.repo.list_schedules(session)
            return [await schedule_to_dict(session, sched) for sched in items]

    async def create_schedule(
        self,
        *,
        name: str,
        target_id: str,
        destination_ids: List[str],
        interval_seconds: int,
        retention: Dict[str, Any],
        enabled: bool,
    ) -> Dict[str, Any]:
        """Create a schedule."""

        async with self.handler.AsyncSessionLocal() as session:
            target = await self.repo.get_target(session, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")

            destinations = []
            for dest_id in destination_ids:
                dest = await self.repo.get_destination(session, dest_id)
                if not dest:
                    raise ValueError(f"Destination not found: {dest_id}")
                destinations.append(dest)

            schedule = await self.repo.create_schedule(
                session,
                name=name,
                target_id=target_id,
                destinations=destinations,
                interval_seconds=interval_seconds,
                retention=retention or {},
                enabled=enabled,
            )

            return await schedule_to_dict(session, schedule)

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

        async with self.handler.AsyncSessionLocal() as session:
            schedule = await self.repo.get_schedule(session, schedule_id)
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")

            if target_id is not None:
                target = await self.repo.get_target(session, target_id)
                if not target:
                    raise ValueError(f"Target not found: {target_id}")

            destinations = None
            if destination_ids is not None:
                destinations = []
                for dest_id in destination_ids:
                    dest = await self.repo.get_destination(session, dest_id)
                    if not dest:
                        raise ValueError(f"Destination not found: {dest_id}")
                    destinations.append(dest)

            updated = await self.repo.update_schedule(
                session,
                schedule,
                name=name,
                target_id=target_id,
                destinations=destinations,
                interval_seconds=interval_seconds,
                retention=retention,
                enabled=enabled,
            )

            return await schedule_to_dict(session, updated)

    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""

        async with self.handler.AsyncSessionLocal() as session:
            schedule = await self.repo.get_schedule(session, schedule_id)
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")
            await self.repo.delete_schedule(session, schedule)

    async def run_now(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule immediately."""

        return await ScheduleExecutor(self.handler).run_now(schedule_id)

    async def run_due(self, *, max_schedules: int = 10) -> Dict[str, Any]:
        """Execute due schedules."""

        return await ScheduleExecutor(self.handler).run_due(max_schedules=max_schedules)
