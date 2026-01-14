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
from typing import Any, List, Tuple

import httpx

from api.logging_config import configure_logging, get_logger

try:
    configure_logging(
        log_dir=os.environ.get("LOG_DIR", "/app/logs"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        debug=os.environ.get("DEBUG", "").strip().lower() in ("1", "true", "yes"),
        log_filename=os.environ.get("LOG_FILENAME", "backup-restore-runner.log"),
    )
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
logger = get_logger(__name__)


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


def extract_run_due_summary(result: Any) -> Tuple[int, List[str]]:
    """Extract executed count and errors from a run-due result.

    The runner supports two shapes:

    - Legacy runner shape: {"executed": int, "errors": [str, ...]}
    - Current backend shape: {"count": int, "results": [{"status": "success"|"failed", ...}]}

    Args:
        result: Parsed JSON response (API mode) or returned dict (direct mode).

    Returns:
        Tuple[int, List[str]]: (executed_count, errors)
    """

    if not isinstance(result, dict):
        return 0, [f"Unexpected run-due result type: {type(result).__name__}"]

    executed_raw = result.get("executed", None)
    if executed_raw is None:
        executed_raw = result.get("count", 0)

    try:
        executed = int(executed_raw or 0)
    except (TypeError, ValueError):
        executed = 0

    errors: List[str] = []

    legacy_errors = result.get("errors", None)
    if isinstance(legacy_errors, list):
        for err in legacy_errors:
            if err is None:
                continue
            errors.append(str(err))

    results = result.get("results", None)
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            if str(item.get("status", "")).lower() != "failed":
                continue
            schedule_id = item.get("schedule_id")
            error_text = item.get("error") or item.get("message") or "Unknown error"
            if schedule_id is not None:
                errors.append(f"schedule_id={schedule_id}: {error_text}")
            else:
                errors.append(str(error_text))

    return executed, errors


async def run_cycle(
    mode: str,
    api_url: str = "",
    api_key: str = "",
    max_schedules: int = 10,
    drain_mode: bool = False,
    drain_max_batches: int = 20,
) -> None:
    """Run one backup cycle.

    Args:
        mode: 'api' or 'direct'.
        api_url: API URL for API mode.
        api_key: API key for API mode.
        max_schedules: Maximum schedules per cycle.
        drain_mode: When True, keep running batches in a single cycle until fewer than
            max_schedules were executed (or a safety limit is reached).
        drain_max_batches: Safety limit for how many batches may be executed in a single
            cycle when drain_mode is enabled.
    """

    try:
        logger.info("Starting backup cycle...")

        total_executed = 0
        all_errors: List[str] = []

        batches = 0
        while True:
            batches += 1
            if batches > max(1, drain_max_batches):
                logger.warning(
                    "Drain mode reached max batches (%s). Stopping to avoid infinite backlog loop.",
                    drain_max_batches,
                )
                break

            if mode == "api":
                result = await run_due_via_api(api_url, api_key, max_schedules)
            else:
                result = await run_due_direct(max_schedules)

            executed, errors = extract_run_due_summary(result)
            total_executed += executed
            all_errors.extend(errors)

            if not drain_mode:
                break

            # When we execute a full batch, there may still be more due schedules.
            # Keep draining until we don't fill the batch (or hit a safety limit).
            if executed < max_schedules:
                break

        if total_executed > 0:
            if drain_mode and batches > 1:
                logger.info("Executed %s schedule(s) across %s batch(es)", total_executed, batches)
            else:
                logger.info("Executed %s schedule(s)", total_executed)
        else:
            logger.debug("No schedules due")

        if all_errors:
            for err in all_errors:
                logger.error("Schedule error: %s", err)

    except Exception as e:
        logger.error("Backup cycle failed: %s", e)


async def main_loop(
    interval: int,
    mode: str,
    api_url: str = "",
    api_key: str = "",
    max_schedules: int = 10,
    drain_mode: bool = False,
    drain_max_batches: int = 20,
) -> None:
    """Main runner loop.

    Args:
        interval: Seconds between cycles.
        mode: 'api' or 'direct'.
        api_url: API URL for API mode.
        api_key: API key for API mode.
        max_schedules: Maximum schedules per cycle.
        drain_mode: When True, keep running batches in a single cycle until fewer than
            max_schedules were executed (or a safety limit is reached).
        drain_max_batches: Safety limit for how many batches may be executed in a single
            cycle when drain_mode is enabled.
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

    logger.info(
        "Backup runner started (mode=%s, interval=%ss, max_schedules=%s, drain_mode=%s)",
        mode,
        interval,
        max_schedules,
        drain_mode,
    )

    if mode == "api":
        logger.info("Waiting for API to become ready...")
        await wait_for_api_ready()
        logger.info("API is ready")

    while True:
        await run_cycle(
            mode,
            api_url,
            api_key,
            max_schedules,
            drain_mode=drain_mode,
            drain_max_batches=drain_max_batches,
        )
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
        "--drain",
        action="store_true",
        default=os.environ.get("RUNNER_DRAIN_MODE", "").strip().lower() in ("1", "true", "yes"),
        help="When enabled, run multiple batches per cycle to drain past-due schedules",
    )
    parser.add_argument(
        "--drain-max-batches",
        type=int,
        default=int(os.environ.get("RUNNER_DRAIN_MAX_BATCHES", "20")),
        help="Safety limit for drain batches per cycle (default: 20)",
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
        asyncio.run(
            run_cycle(
                args.mode,
                args.api_url,
                args.api_key,
                args.max_schedules,
                drain_mode=args.drain,
                drain_max_batches=args.drain_max_batches,
            )
        )
    else:
        asyncio.run(
            main_loop(
                args.interval,
                args.mode,
                args.api_url,
                args.api_key,
                args.max_schedules,
                drain_mode=args.drain,
                drain_max_batches=args.drain_max_batches,
            )
        )


if __name__ == "__main__":
    main()
