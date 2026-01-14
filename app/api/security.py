"""
Security utilities for API authentication.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets
from typing import Deque, Dict, Optional

from fastapi import Request, Security, HTTPException, status
from fastapi.security import APIKeyHeader
from api.settings import settings

# Define the API key headers
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
restore_key_header = APIKeyHeader(name="X-Restore-Key", auto_error=False)
delete_key_header = APIKeyHeader(name="X-Delete-Key", auto_error=False)


@dataclass(frozen=True)
class _RateLimitResult:
    """Represents the result of a rate-limit check."""

    allowed: bool
    retry_after_seconds: int


class _InMemoryRateLimiter:
    """In-memory sliding-window rate limiter.

    This is intended as basic protection against brute forcing API keys and
    accidental repeated destructive operations.

    Note:
        This is process-local and resets on restart. For multi-worker or
        distributed deployments, replace with Redis-based rate limiting.
    """

    def __init__(self) -> None:
        """Initialize the limiter."""

        self._events: Dict[str, Deque[float]] = {}

    def check_and_add(self, *, key: str, limit: int, window_seconds: int, now: float) -> _RateLimitResult:
        """Check a sliding-window limit and record the current event.

        Args:
            key: Bucket key.
            limit: Maximum number of events allowed within the window.
            window_seconds: Window duration in seconds.
            now: Current timestamp (seconds).

        Returns:
            _RateLimitResult: Whether allowed and how long to wait if blocked.
        """

        bucket = self._events.setdefault(key, deque())
        cutoff = now - float(window_seconds)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = int(max(1.0, bucket[0] + float(window_seconds) - now))
            return _RateLimitResult(allowed=False, retry_after_seconds=retry_after)

        bucket.append(now)
        return _RateLimitResult(allowed=True, retry_after_seconds=0)


_rate_limiter = _InMemoryRateLimiter()


def _client_bucket_key(request: Optional[Request]) -> str:
    """Build a stable bucket key for a client.

    Args:
        request: Request context.

    Returns:
        str: Bucket identifier.
    """

    if not request or not request.client:
        return "unknown"
    return request.client.host or "unknown"


def _raise_rate_limited(*, retry_after_seconds: int, scope: str) -> None:
    """Raise a 429 HTTPException for a rate limited operation.

    Args:
        retry_after_seconds: Suggested wait time.
        scope: Human readable scope label.

    Raises:
        HTTPException: Always.
    """

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many requests ({scope}). Please retry later.",
        headers={"Retry-After": str(max(1, int(retry_after_seconds)))} if retry_after_seconds else None,
    )


def _enforce_auth_failure_budget(*, request: Optional[Request], kind: str) -> None:
    """Enforce a rate limit budget for auth failures.

    Args:
        request: Request context.
        kind: One of: admin|restore|delete.

    Raises:
        HTTPException: 429 if exceeded.
    """

    now = datetime.now(timezone.utc).timestamp()
    client = _client_bucket_key(request)
    key = f"authfail:{kind}:{client}"
    result = _rate_limiter.check_and_add(key=key, limit=20, window_seconds=300, now=now)
    if not result.allowed:
        _raise_rate_limited(retry_after_seconds=result.retry_after_seconds, scope=f"auth failures ({kind})")


def _enforce_operation_budget(*, request: Optional[Request], kind: str) -> None:
    """Enforce a rate limit budget for destructive operations.

    Args:
        request: Request context.
        kind: One of: restore|delete.

    Raises:
        HTTPException: 429 if exceeded.
    """

    now = datetime.now(timezone.utc).timestamp()
    client = _client_bucket_key(request)

    if kind == "restore":
        limit = 6
        window_seconds = 300
    else:
        limit = 30
        window_seconds = 300

    key = f"op:{kind}:{client}"
    result = _rate_limiter.check_and_add(key=key, limit=limit, window_seconds=window_seconds, now=now)
    if not result.allowed:
        _raise_rate_limited(retry_after_seconds=result.retry_after_seconds, scope=f"{kind} operations")


async def verify_admin_key(request: Request, admin_key: str = Security(admin_key_header)) -> str:
    """
    Verify the admin API key provided in the X-Admin-Key header.
    
    This is used for sensitive operations like backup/restore.
    
    Args:
        admin_key: The admin API key from the request header
        
    Returns:
        The validated admin API key
        
    Raises:
        HTTPException: If the admin API key is missing or invalid
    """
    # Get admin API key from file or environment
    configured_admin_key = settings.get_admin_api_key()
    
    # Check if ADMIN_API_KEY is configured
    if not configured_admin_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured. Please set ADMIN_API_KEY or ADMIN_API_KEY_FILE."
        )
    
    # Check if API key was provided
    if not admin_key:
        _enforce_auth_failure_budget(request=request, kind="admin")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. This endpoint requires 'X-Admin-Key' header. Use the 'Authorize' button in Swagger UI to provide your admin key."
        )
    
    # Verify the API key (constant-time comparison)
    if not secrets.compare_digest(str(admin_key or ""), str(configured_admin_key or "")):
        _enforce_auth_failure_budget(request=request, kind="admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key. The provided 'X-Admin-Key' does not match the configured ADMIN_API_KEY."
        )
    
    return admin_key


async def verify_restore_key(request: Request, restore_key: str = Security(restore_key_header)) -> str:
    """
    Verify the restore API key provided in the X-Restore-Key header.
    
    This is used for destructive restore operations that overwrite the database.
    
    Args:
        restore_key: The restore API key from the request header
        
    Returns:
        The validated restore API key
        
    Raises:
        HTTPException: If the restore API key is missing or invalid
    """
    # Get restore API key from file or environment
    configured_restore_key = settings.get_restore_api_key()
    
    # Check if BACKUP_RESTORE_API_KEY is configured
    if not configured_restore_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restore API key not configured. Please set BACKUP_RESTORE_API_KEY or BACKUP_RESTORE_API_KEY_FILE."
        )
    
    # Check if API key was provided
    if not restore_key:
        _enforce_auth_failure_budget(request=request, kind="restore")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. This endpoint requires 'X-Restore-Key' header. Use the 'Authorize' button in Swagger UI to provide your restore key."
        )
    
    # Verify the API key (constant-time comparison)
    if not secrets.compare_digest(str(restore_key or ""), str(configured_restore_key or "")):
        _enforce_auth_failure_budget(request=request, kind="restore")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid restore API key. The provided 'X-Restore-Key' does not match the configured BACKUP_RESTORE_API_KEY."
        )

    if request.method.upper() == "POST" and "restore" in request.url.path:
        _enforce_operation_budget(request=request, kind="restore")
    
    return restore_key


async def verify_delete_key(request: Request, delete_key: str = Security(delete_key_header)) -> str:
    """
    Verify the delete API key provided in the X-Delete-Key header.

    This is used for destructive delete operations.

    In DEBUG mode, when BACKUP_DELETE_API_KEY is not configured, this falls back
    to using the configured admin key as delete key.

    Args:
        delete_key: The delete API key from the request header

    Returns:
        The validated delete API key

    Raises:
        HTTPException: If the delete API key is missing or invalid
    """
    configured_delete_key = settings.get_delete_api_key()

    if not configured_delete_key and settings.DEBUG:
        configured_delete_key = settings.get_admin_api_key()

    if not configured_delete_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Delete API key not configured. Please set BACKUP_DELETE_API_KEY or BACKUP_DELETE_API_KEY_FILE. "
                "(Tip: in DEBUG mode you can also set ADMIN_API_KEY and use it as X-Delete-Key.)"
            ),
        )

    if not delete_key:
        _enforce_auth_failure_budget(request=request, kind="delete")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing API key. This endpoint requires 'X-Delete-Key' header. "
                "Use the 'Authorize' button in Swagger UI to provide your delete key."
            ),
        )

    if not secrets.compare_digest(str(delete_key or ""), str(configured_delete_key or "")):
        _enforce_auth_failure_budget(request=request, kind="delete")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Invalid delete API key. The provided 'X-Delete-Key' does not match the configured BACKUP_DELETE_API_KEY."
            ),
        )

    if request.method.upper() == "DELETE":
        _enforce_operation_budget(request=request, kind="delete")

    return delete_key
