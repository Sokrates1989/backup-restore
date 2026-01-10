"""Retention policy planning for stored backups.

This is a simplified, backend-friendly retention planner used by the backup
automation runner.

It supports:
- `mode=last_n`
- `mode=smart` with daily/weekly/monthly/yearly tiers and optional profiles

The planner operates on a list of `BackupObject` metadata and returns (keep,
remove) decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class RetentionConfig:
    """Retention policy configuration.

    Attributes:
        mode: Either "last_n" or "smart".
        keep_last: Always keep the newest N backups.
        profile: Optional preset name ("low", "medium", "high") used in smart mode.
        daily: Keep 1 per day for N days (smart mode).
        weekly: Keep 1 per ISO week for N weeks (smart mode).
        monthly: Keep 1 per calendar month for N months (smart mode).
        yearly: Keep 1 per year for N years (smart mode).
        min_backups: Ensure at least this many backups are kept.
        max_backups: Ensure at most this many backups are kept.
    """

    mode: str = "last_n"
    keep_last: int = 10
    profile: Optional[str] = None

    daily: Optional[int] = None
    weekly: Optional[int] = None
    monthly: Optional[int] = None
    yearly: Optional[int] = None

    min_backups: Optional[int] = None
    max_backups: Optional[int] = None


@dataclass(frozen=True)
class BackupObject:
    """Metadata about a stored backup object."""

    id: str
    name: str
    created_at: datetime
    size: Optional[int] = None


def retention_from_dict(data: Optional[Dict]) -> RetentionConfig:
    """Build a RetentionConfig from an untrusted dictionary.

    Args:
        data: Raw retention config dictionary.

    Returns:
        RetentionConfig: Parsed config.
    """

    data = data or {}
    return RetentionConfig(
        mode=str(data.get("mode", "last_n")),
        keep_last=int(data.get("keep_last", 10)),
        profile=data.get("profile"),
        daily=_to_int_or_none(data.get("daily")),
        weekly=_to_int_or_none(data.get("weekly")),
        monthly=_to_int_or_none(data.get("monthly")),
        yearly=_to_int_or_none(data.get("yearly")),
        min_backups=_to_int_or_none(data.get("min_backups")),
        max_backups=_to_int_or_none(data.get("max_backups")),
    )


def _to_int_or_none(value) -> Optional[int]:
    """Convert value to int or None.

    Args:
        value: Input value.

    Returns:
        Optional[int]: Parsed integer.

    Raises:
        ValueError: If conversion fails.
    """

    if value is None:
        return None
    return int(value)


def plan_retention(
    backups: Sequence[BackupObject],
    retention: RetentionConfig,
    *,
    now: Optional[datetime] = None,
) -> Tuple[List[BackupObject], List[BackupObject]]:
    """Return (keep, delete) lists according to the retention policy.

    Args:
        backups: Existing backups.
        retention: Retention policy.
        now: Override current time.

    Returns:
        Tuple[List[BackupObject], List[BackupObject]]: Keep and delete lists.
    """

    if not backups:
        return [], []

    now = now or datetime.now(timezone.utc)
    backups_sorted = sorted(backups, key=lambda b: b.created_at)  # oldest -> newest

    if retention.mode == "last_n":
        keep_last = max(retention.keep_last, 0)
        keep = backups_sorted[-keep_last:] if keep_last else []
        delete = backups_sorted[:-keep_last] if keep_last else list(backups_sorted)
        return _apply_min_max_bounds(keep, delete, retention)

    eff = _apply_profile(retention)
    newest_first = sorted(backups_sorted, key=lambda b: b.created_at, reverse=True)

    keep_indices: set[int] = set()
    keep_last = max(eff.keep_last, 0)

    for idx in range(min(keep_last, len(newest_first))):
        keep_indices.add(idx)

    daily_buckets: Dict[date, int] = {}
    weekly_buckets: Dict[tuple[int, int], int] = {}
    monthly_buckets: Dict[tuple[int, int], int] = {}
    yearly_buckets: Dict[int, int] = {}

    for idx, obj in enumerate(newest_first):
        if idx < keep_last:
            continue

        created = obj.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        age_days = (now.date() - created.date()).days

        if eff.daily is not None and age_days < eff.daily:
            key = created.date()
            if key not in daily_buckets:
                daily_buckets[key] = idx
                keep_indices.add(idx)
            continue

        if eff.weekly is not None:
            iso_year, iso_week, _ = created.isocalendar()
            now_year, now_week, _ = now.isocalendar()
            week_delta = (now_year - iso_year) * 52 + (now_week - iso_week)
            if 0 <= week_delta < eff.weekly:
                key = (iso_year, iso_week)
                if key not in weekly_buckets:
                    weekly_buckets[key] = idx
                    keep_indices.add(idx)
                continue

        if eff.monthly is not None:
            month_delta = (now.year - created.year) * 12 + (now.month - created.month)
            if 0 <= month_delta < eff.monthly:
                key = (created.year, created.month)
                if key not in monthly_buckets:
                    monthly_buckets[key] = idx
                    keep_indices.add(idx)
                continue

        if eff.yearly is not None:
            year_delta = now.year - created.year
            if 0 <= year_delta < eff.yearly:
                key = created.year
                if key not in yearly_buckets:
                    yearly_buckets[key] = idx
                    keep_indices.add(idx)
                continue

    keep = [obj for idx, obj in enumerate(newest_first) if idx in keep_indices]
    delete = [obj for idx, obj in enumerate(newest_first) if idx not in keep_indices]

    keep.sort(key=lambda b: b.created_at)
    delete.sort(key=lambda b: b.created_at)

    return _apply_min_max_bounds(keep, delete, eff)


def _apply_profile(ret: RetentionConfig) -> RetentionConfig:
    """Apply smart-mode profile defaults to the retention config.

    Args:
        ret: Raw retention config.

    Returns:
        RetentionConfig: Effective config with profile defaults applied.
    """

    if ret.mode != "smart":
        return ret

    has_any_tier = any(v is not None for v in (ret.daily, ret.weekly, ret.monthly, ret.yearly))
    profile = ret.profile or ("medium" if not has_any_tier else None)

    if not profile:
        return ret

    if profile == "low":
        defaults = {"daily": 1, "weekly": 1, "monthly": 3, "yearly": 1}
    elif profile == "high":
        defaults = {"daily": 14, "weekly": 8, "monthly": 24, "yearly": 5}
    else:
        defaults = {"daily": 7, "weekly": 4, "monthly": 12, "yearly": 3}

    data = asdict(ret)
    for key, value in defaults.items():
        if data.get(key) is None:
            data[key] = value

    return RetentionConfig(**data)


def _apply_min_max_bounds(
    keep: List[BackupObject],
    delete: List[BackupObject],
    retention: RetentionConfig,
) -> Tuple[List[BackupObject], List[BackupObject]]:
    """Apply optional min_backups/max_backups to keep/delete lists.

    Args:
        keep: Keep list.
        delete: Delete list.
        retention: Retention policy.

    Returns:
        Tuple[List[BackupObject], List[BackupObject]]: Adjusted keep/delete lists.
    """

    if retention.max_backups is not None and retention.max_backups >= 0:
        max_keep = retention.max_backups
        if len(keep) > max_keep:
            overflow = len(keep) - max_keep
            keep_sorted = sorted(keep, key=lambda b: b.created_at)
            to_drop = keep_sorted[:overflow]
            remaining_keep = keep_sorted[overflow:]
            delete = sorted(delete + to_drop, key=lambda b: b.created_at)
            keep = remaining_keep

    if retention.min_backups is not None and retention.min_backups > 0:
        min_keep = retention.min_backups
        if len(keep) < min_keep and delete:
            missing = min_keep - len(keep)
            delete_sorted = sorted(delete, key=lambda b: b.created_at, reverse=True)
            to_restore = delete_sorted[:missing]
            remaining_delete = delete_sorted[missing:]
            keep = sorted(keep + to_restore, key=lambda b: b.created_at)
            delete = sorted(remaining_delete, key=lambda b: b.created_at)

    return keep, delete
