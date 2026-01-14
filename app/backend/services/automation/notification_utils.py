"""Notification utilities for backup automation.

This module contains small pure helpers used by the notification subsystem.
They are intentionally kept separate from the NotificationService implementation
to keep the service module focused on I/O (Telegram/SMTP) and to avoid
overgrowing single files.

The notification configuration supports two shapes:

1) New format (multi-recipient):

    {
        "enabled": true,
        "recipients": [
            {"chat_id": "-100123", "min_severity": "warning"},
            {"chat_id": "123", "min_severity": "error"},
        ]
    }

2) Legacy format (single recipient with per-status flags):

    {
        "enabled": true,
        "chat_id": "-100123",
        "on_success": true,
        "on_warning": false,
        "on_failure": true,
    }

The legacy format is mapped to a single minimum-severity value.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping


_SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


def normalize_min_severity(value: Any) -> str:
    """Normalize a severity label.

    Args:
        value: Severity value.

    Returns:
        str: Normalized severity label (info|warning|error).
    """

    if not value:
        return "error"

    label = str(value).strip().lower()
    if label in _SEVERITY_ORDER:
        return label

    return "error"


def status_to_severity(status: str) -> str:
    """Map a backup status to a severity label.

    Args:
        status: Backup status string.

    Returns:
        str: Severity label.
    """

    normalized = (status or "").strip().lower()
    if normalized == "success":
        return "info"
    if normalized == "warning":
        return "warning"
    if normalized == "failed":
        return "error"
    return "error"


def legacy_flags_to_min_severity(config: Mapping[str, Any]) -> str:
    """Derive a minimum severity from legacy on_success/on_warning/on_failure flags.

    Args:
        config: Legacy channel configuration.

    Returns:
        str: Minimum severity label.
    """

    if config.get("on_success"):
        return "info"
    if config.get("on_warning"):
        return "warning"
    if config.get("on_failure"):
        return "error"
    return "error"


def should_notify_for_min_severity(*, status: str, min_severity: str) -> bool:
    """Return True when a status should be delivered to a recipient.

    Args:
        status: Backup status.
        min_severity: Minimum severity configured for recipient.

    Returns:
        bool: True if recipient should receive the status.
    """

    status_severity = status_to_severity(status)
    status_rank = _SEVERITY_ORDER[status_severity]
    min_rank = _SEVERITY_ORDER[normalize_min_severity(min_severity)]
    return status_rank >= min_rank


def extract_telegram_recipients(telegram_config: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Extract Telegram recipients from channel configuration.

    Args:
        telegram_config: Telegram notification configuration.

    Returns:
        List[Dict[str, str]]: Recipients in the form {chat_id, min_severity}.
    """

    recipients = telegram_config.get("recipients")
    if isinstance(recipients, list) and recipients:
        normalized: List[Dict[str, str]] = []
        for item in recipients:
            if not isinstance(item, dict):
                continue
            chat_id = str(item.get("chat_id") or "").strip()
            if not chat_id:
                continue
            normalized.append(
                {
                    "chat_id": chat_id,
                    "min_severity": normalize_min_severity(item.get("min_severity")),
                }
            )
        return normalized

    chat_id = str(telegram_config.get("chat_id") or "").strip()
    if not chat_id:
        return []

    return [
        {
            "chat_id": chat_id,
            "min_severity": legacy_flags_to_min_severity(telegram_config),
        }
    ]


def extract_email_recipients(email_config: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Extract email recipients from channel configuration.

    Args:
        email_config: Email notification configuration.

    Returns:
        List[Dict[str, str]]: Recipients in the form {to, min_severity}.
    """

    recipients = email_config.get("recipients")
    if isinstance(recipients, list) and recipients:
        normalized: List[Dict[str, str]] = []
        for item in recipients:
            if not isinstance(item, dict):
                continue
            to_addr = str(item.get("to") or "").strip()
            if not to_addr:
                continue
            normalized.append(
                {
                    "to": to_addr,
                    "min_severity": normalize_min_severity(item.get("min_severity")),
                }
            )
        return normalized

    to_addr = str(email_config.get("to") or "").strip()
    if not to_addr:
        return []

    return [
        {
            "to": to_addr,
            "min_severity": legacy_flags_to_min_severity(email_config),
        }
    ]
