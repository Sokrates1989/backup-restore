"""
Security utilities for API authentication.

This module provides authentication via:
1. API keys (X-Admin-Key, X-Restore-Key, X-Delete-Key headers)
2. Keycloak JWT tokens (Authorization: Bearer <token> header)

When Keycloak is enabled (KEYCLOAK_ENABLED=true), both authentication methods
are supported. JWT tokens take precedence over API keys when both are provided.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets
from typing import Deque, Dict, Optional

from fastapi import Depends, Request, Security, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from api.settings import settings

# Define the API key headers
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
restore_key_header = APIKeyHeader(name="X-Restore-Key", auto_error=False)
delete_key_header = APIKeyHeader(name="X-Delete-Key", auto_error=False)

# Bearer token for Keycloak JWT authentication
bearer_scheme = HTTPBearer(auto_error=False)


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


async def verify_admin_key(
    request: Request,
    admin_key: str = Security(admin_key_header),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify authentication via API key or Keycloak JWT token.
    
    When Keycloak is enabled, accepts either:
    - Bearer token in Authorization header (JWT from Keycloak)
    - X-Admin-Key header (legacy API key authentication)
    
    Args:
        request: The FastAPI request object
        admin_key: The admin API key from the request header
        bearer_token: Bearer token credentials from Authorization header
        
    Returns:
        The validated admin API key or "keycloak:<username>" for JWT auth
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try Keycloak JWT authentication first if enabled
    if settings.KEYCLOAK_ENABLED and bearer_token:
        try:
            from api.keycloak_auth import get_keycloak_auth
            keycloak = get_keycloak_auth()
            if keycloak:
                user = keycloak.validate_token(bearer_token.credentials)
                # Check if user has admin or viewer role (read access)
                if user.has_any_role(["admin", "operator", "viewer"]):
                    return f"keycloak:{user.username}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required role: admin, operator, or viewer. Your roles: {', '.join(user.roles)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Fall back to API key authentication
    configured_admin_key = settings.get_admin_api_key()
    
    # Check if ADMIN_API_KEY is configured
    if not configured_admin_key:
        if settings.KEYCLOAK_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please provide a Bearer token or X-Admin-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured. Please set ADMIN_API_KEY or ADMIN_API_KEY_FILE."
        )
    
    # Check if API key was provided
    if not admin_key:
        _enforce_auth_failure_budget(request=request, kind="admin")
        if settings.KEYCLOAK_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please provide a Bearer token or X-Admin-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )
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


async def verify_restore_key(
    request: Request,
    restore_key: str = Security(restore_key_header),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify authentication for restore operations via API key or Keycloak JWT token.
    
    When Keycloak is enabled, users with 'admin' or 'operator' role can perform restores.
    
    Args:
        request: The FastAPI request object
        restore_key: The restore API key from the request header
        bearer_token: Bearer token credentials from Authorization header
        
    Returns:
        The validated restore API key or "keycloak:<username>" for JWT auth
        
    Raises:
        HTTPException: If authentication fails or user lacks restore permission
    """
    # Try Keycloak JWT authentication first if enabled
    if settings.KEYCLOAK_ENABLED and bearer_token:
        try:
            from api.keycloak_auth import get_keycloak_auth
            keycloak = get_keycloak_auth()
            if keycloak:
                user = keycloak.validate_token(bearer_token.credentials)
                # Check if user has admin or operator role (restore access)
                if user.has_any_role(["admin", "operator"]):
                    if request.method.upper() == "POST" and "restore" in request.url.path:
                        _enforce_operation_budget(request=request, kind="restore")
                    return f"keycloak:{user.username}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Restore operations require 'admin' or 'operator' role. Your roles: {', '.join(user.roles)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Fall back to API key authentication
    configured_restore_key = settings.get_restore_api_key()
    
    # Check if BACKUP_RESTORE_API_KEY is configured
    if not configured_restore_key:
        if settings.KEYCLOAK_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for restore operations. Please provide a Bearer token or X-Restore-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )
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


async def verify_delete_key(
    request: Request,
    delete_key: str = Security(delete_key_header),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify authentication for delete operations via API key or Keycloak JWT token.

    When Keycloak is enabled, only users with 'admin' role can perform deletes.

    In DEBUG mode with API key auth, when BACKUP_DELETE_API_KEY is not configured,
    this falls back to using the configured admin key as delete key.

    Args:
        request: The FastAPI request object
        delete_key: The delete API key from the request header
        bearer_token: Bearer token credentials from Authorization header

    Returns:
        The validated delete API key or "keycloak:<username>" for JWT auth

    Raises:
        HTTPException: If authentication fails or user lacks delete permission
    """
    # Try Keycloak JWT authentication first if enabled
    if settings.KEYCLOAK_ENABLED and bearer_token:
        try:
            from api.keycloak_auth import get_keycloak_auth
            keycloak = get_keycloak_auth()
            if keycloak:
                user = keycloak.validate_token(bearer_token.credentials)
                # Only admin role can perform deletes
                if user.has_role("admin"):
                    if request.method.upper() == "DELETE":
                        _enforce_operation_budget(request=request, kind="delete")
                    return f"keycloak:{user.username}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Delete operations require 'admin' role. Your roles: {', '.join(user.roles)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fall back to API key authentication
    configured_delete_key = settings.get_delete_api_key()

    if not configured_delete_key and settings.DEBUG:
        configured_delete_key = settings.get_admin_api_key()

    if not configured_delete_key:
        if settings.KEYCLOAK_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for delete operations. Please provide a Bearer token or X-Delete-Key header.",
                headers={"WWW-Authenticate": "Bearer"},
            )
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
