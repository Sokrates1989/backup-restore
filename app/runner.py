#!/usr/bin/env python3
"""Backup runner service.

This script runs as a periodic service to execute due backup schedules.
It can run in two modes:
1. API mode: Calls the backup-restore API to execute due schedules
2. Direct mode: Executes schedules directly using the automation service

Usage:
    python runner.py [--interval SECONDS] [--api-url URL] [--api-key KEY]
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_env_or_file(env_name: str, file_env_name: str, default: str = "") -> str:
    """Get value from environment variable or file.

    Args:
        env_name: Environment variable name.
        file_env_name: Environment variable containing path to file.
        default: Default value if neither is set.

    Returns:
        str: The value.
    """

    value = os.environ.get(env_name, "")
    if value:
        return value

    file_path = os.environ.get(file_env_name, "")
    if file_path and os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read().strip()

    return default


async def run_due_via_api(api_url: str, api_key: str, max_schedules: int = 10) -> dict:
    """Execute due schedules via API call.

    Args:
        api_url: Base URL of the backup-restore API.
        api_key: Admin API key.
        max_schedules: Maximum schedules to run per cycle.

    Returns:
        dict: API response.
    """

    endpoint = f"{api_url}/automation/runner/run-due"
    headers = {"X-Admin-Key": api_key, "Content-Type": "application/json"}
    payload = {"max_schedules": max_schedules}

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def run_due_direct(max_schedules: int = 10) -> dict:
    """Execute due schedules directly using automation service.

    Args:
        max_schedules: Maximum schedules to run per cycle.

    Returns:
        dict: Execution summary.
    """

    # Import here to avoid issues when running in API mode
    from backend.services.automation.schedule_service import ScheduleService
    from backend.database import get_database_handler
    from backend.database.sql_handler import SQLHandler

    handler = get_database_handler()
    if not isinstance(handler, SQLHandler):
        raise ValueError("Runner requires SQL database")

    service = ScheduleService(handler)
    return await service.run_due(max_schedules=max_schedules)


async def run_cycle(
    mode: str,
    api_url: str = "",
    api_key: str = "",
    max_schedules: int = 10,
) -> None:
    """Run one backup cycle.

    Args:
        mode: 'api' or 'direct'.
        api_url: API URL for API mode.
        api_key: API key for API mode.
        max_schedules: Maximum schedules per cycle.
    """

    try:
        logger.info("Starting backup cycle...")

        if mode == "api":
            result = await run_due_via_api(api_url, api_key, max_schedules)
        else:
            result = await run_due_direct(max_schedules)

        executed = result.get("executed", 0)
        errors = result.get("errors", [])

        if executed > 0:
            logger.info(f"Executed {executed} schedule(s)")
        else:
            logger.debug("No schedules due")

        if errors:
            for err in errors:
                logger.error(f"Schedule error: {err}")

    except Exception as e:
        logger.error(f"Backup cycle failed: {e}")


async def main_loop(
    interval: int,
    mode: str,
    api_url: str = "",
    api_key: str = "",
    max_schedules: int = 10,
) -> None:
    """Main runner loop.

    Args:
        interval: Seconds between cycles.
        mode: 'api' or 'direct'.
        api_url: API URL for API mode.
        api_key: API key for API mode.
        max_schedules: Maximum schedules per cycle.
    """

    async def wait_for_api_ready(timeout_seconds: int = 120) -> None:
        """Wait until the API health endpoint is reachable.

        Args:
            timeout_seconds: Maximum time to wait for the API.

        Returns:
            None
        """

        deadline = time.time() + timeout_seconds
        health_url = f"{api_url}/health"

        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.time() < deadline:
                try:
                    resp = await client.get(health_url)
                    if resp.status_code == 200:
                        return
                except Exception:
                    pass

                await asyncio.sleep(1)

    logger.info(f"Backup runner started (mode={mode}, interval={interval}s)")

    if mode == "api":
        logger.info("Waiting for API to become ready...")
        await wait_for_api_ready()
        logger.info("API is ready")

    while True:
        await run_cycle(mode, api_url, api_key, max_schedules)
        await asyncio.sleep(interval)


def main():
    """Entry point."""

    parser = argparse.ArgumentParser(description="Backup runner service")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("RUNNER_INTERVAL", "60")),
        help="Seconds between backup cycles (default: 60)",
    )
    parser.add_argument(
        "--mode",
        choices=["api", "direct"],
        default=os.environ.get("RUNNER_MODE", "api"),
        help="Execution mode (default: api)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("BACKUP_API_URL", "http://localhost:8000"),
        help="Backup API URL for API mode",
    )
    parser.add_argument(
        "--api-key",
        default=get_env_or_file("ADMIN_API_KEY", "ADMIN_API_KEY_FILE"),
        help="Admin API key for API mode",
    )
    parser.add_argument(
        "--max-schedules",
        type=int,
        default=int(os.environ.get("RUNNER_MAX_SCHEDULES", "10")),
        help="Maximum schedules per cycle (default: 10)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)",
    )

    args = parser.parse_args()

    if args.mode == "api" and not args.api_key:
        logger.error("API key required for API mode. Set ADMIN_API_KEY or use --api-key")
        sys.exit(1)

    if args.once:
        asyncio.run(run_cycle(args.mode, args.api_url, args.api_key, args.max_schedules))
    else:
        asyncio.run(
            main_loop(
                args.interval,
                args.mode,
                args.api_url,
                args.api_key,
                args.max_schedules,
            )
        )


if __name__ == "__main__":
    main()
