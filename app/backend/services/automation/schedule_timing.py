"""Schedule timing helpers for backup automation.

This module provides small, well-tested helpers to compute `next_run_at` timestamps
for interval-based schedules.

The current scheduler is interval-based. Schedules can optionally be anchored to
a fixed UTC time-of-day (HH:MM) via `retention.run_at_time`. When set, hourly
and N-hour schedules align to that minute (and, for N-hour intervals, to the
phase implied by the anchor). Daily schedules default to 03:30 UTC.

All timestamps returned by these helpers are timezone-aware UTC datetimes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple


DEFAULT_DAILY_TIME = "03:30"
RUN_AT_TIME_RETENTION_KEY = "run_at_time"


def parse_time_hhmm(value: str) -> Tuple[int, int]:
    """Parse a HH:MM string into (hour, minute).

    Args:
        value: Time string in HH:MM format.

    Returns:
        Tuple[int, int]: Parsed (hour, minute).

    Raises:
        ValueError: If the value cannot be parsed or is out of range.
    """

    raw = str(value or "").strip()
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time-of-day (expected HH:MM): {value!r}")

    hour = int(parts[0])
    minute = int(parts[1])

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time-of-day (out of range): {value!r}")

    return hour, minute


def get_run_at_time_from_retention(retention: Optional[Dict[str, Any]], *, default: str = "") -> str:
    """Extract a run-at time-of-day from a schedule retention dict.

    The schedule model stores miscellaneous configuration in `BackupSchedule.retention`.
    We store the schedule anchor time under `retention.run_at_time`.

    For daily schedules we typically use a default (03:30) when not provided.
    For other schedules the time is optional; when missing, the scheduler keeps the
    legacy drift behavior.

    Args:
        retention: The schedule's retention/config dictionary.
        default: Default time-of-day in HH:MM format.

    Returns:
        str: Time-of-day in HH:MM format, or the provided default.
    """

    data = retention or {}
    raw = str(data.get(RUN_AT_TIME_RETENTION_KEY) or "").strip()
    return raw or default


def get_daily_time_from_retention(retention: Optional[Dict[str, Any]]) -> str:
    """Backwards-compatible helper to extract the daily run time-of-day.

    Args:
        retention: The schedule's retention/config dictionary.

    Returns:
        str: Time-of-day in HH:MM format.
    """

    return get_run_at_time_from_retention(retention, default=DEFAULT_DAILY_TIME)


def compute_next_daily_run_at(*, reference: datetime, run_at_time: str) -> datetime:
    """Compute the next daily run timestamp after a reference time.

    Args:
        reference: Reference time (timezone-aware). The next run will be strictly
            after this timestamp.
        run_at_time: Time-of-day (HH:MM) in UTC.

    Returns:
        datetime: Next run timestamp (UTC).

    Raises:
        ValueError: If `run_at_time` is invalid.
    """

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    hour, minute = parse_time_hhmm(run_at_time)

    candidate = reference.astimezone(timezone.utc).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate <= reference:
        candidate = candidate + timedelta(days=1)

    return candidate


def _compute_anchor_origin(*, reference: datetime, run_at_time: str) -> datetime:
    """Compute a stable anchor origin (UTC) at or before a reference time.

    This origin is used to compute anchored interval schedules so that 6-hour / 12-hour
    schedules can be aligned to a specific HH:MM time-of-day (e.g. 03:30).

    Args:
        reference: Reference time (timezone-aware preferred).
        run_at_time: Time-of-day (HH:MM) in UTC.

    Returns:
        datetime: Anchor origin timestamp (UTC) that is <= reference.

    Raises:
        ValueError: If `run_at_time` is invalid.
    """

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    hour, minute = parse_time_hhmm(run_at_time)

    origin = reference.astimezone(timezone.utc).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if origin > reference:
        origin = origin - timedelta(days=1)
    return origin


def compute_next_anchored_run_at(
    *,
    reference: datetime,
    interval_seconds: int,
    run_at_time: str,
) -> datetime:
    """Compute the next run time for an anchored interval schedule.

    Examples:
        - interval=43200 (12h), run_at_time=03:30 -> 03:30 and 15:30 UTC
        - interval=21600 (6h), run_at_time=03:30 -> 03:30, 09:30, 15:30, 21:30 UTC
        - interval=3600 (hourly), run_at_time=03:30 -> every hour at minute 30

    Args:
        reference: Reference timestamp; the next run will be strictly after this time.
        interval_seconds: Interval in seconds.
        run_at_time: Time-of-day (HH:MM) in UTC.

    Returns:
        datetime: Next run timestamp (UTC).

    Raises:
        ValueError: If inputs are invalid.
    """

    if interval_seconds <= 0:
        raise ValueError(f"Invalid interval_seconds: {interval_seconds}")

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    hour, minute = parse_time_hhmm(run_at_time)
    candidate = reference.astimezone(timezone.utc).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate <= reference:
        delta_seconds = (reference - candidate).total_seconds()
        steps = int(delta_seconds // float(interval_seconds)) + 1
        candidate = candidate + timedelta(seconds=steps * int(interval_seconds))

    return candidate


def compute_next_run_at(
    *,
    reference: datetime,
    interval_seconds: int,
    retention: Optional[Dict[str, Any]] = None,
) -> datetime:
    """Compute the next run time for an interval-based schedule.

    Args:
        reference: Reference timestamp.
        interval_seconds: Schedule interval in seconds.
        retention: The schedule retention/config dict.

    Returns:
        datetime: Next run timestamp.

    Raises:
        ValueError: If the interval_seconds is invalid.
    """

    if interval_seconds <= 0:
        raise ValueError(f"Invalid interval_seconds: {interval_seconds}")

    if interval_seconds == 86400:
        run_at_time = get_daily_time_from_retention(retention)
        return compute_next_anchored_run_at(
            reference=reference,
            interval_seconds=interval_seconds,
            run_at_time=run_at_time,
        )

    run_at_time = get_run_at_time_from_retention(retention, default="")
    if run_at_time and interval_seconds >= 3600:
        return compute_next_anchored_run_at(
            reference=reference,
            interval_seconds=interval_seconds,
            run_at_time=run_at_time,
        )

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    return reference + timedelta(seconds=int(interval_seconds))


def compute_initial_next_run_at(
    *,
    now: datetime,
    enabled: bool,
    interval_seconds: int,
    retention: Optional[Dict[str, Any]] = None,
) -> Optional[datetime]:
    """Compute initial `next_run_at` for a newly created schedule.

    For non-daily schedules we keep the previous behavior (immediate scheduling).
    For daily schedules we schedule the next run at the next occurrence of the
    configured time-of-day.

    Args:
        now: Current timestamp.
        enabled: Whether the schedule is enabled.
        interval_seconds: Interval in seconds.
        retention: Retention/config dict.

    Returns:
        Optional[datetime]: Initial `next_run_at` value.
    """

    if not enabled:
        return None

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if interval_seconds == 86400:
        return compute_next_run_at(reference=now, interval_seconds=interval_seconds, retention=retention)

    run_at_time = get_run_at_time_from_retention(retention, default="")
    if run_at_time and interval_seconds >= 3600:
        return compute_next_run_at(reference=now, interval_seconds=interval_seconds, retention=retention)

    return now
