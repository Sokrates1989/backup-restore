"""Security utilities for API authentication.

This module validates Keycloak-issued JWT bearer tokens and enforces
role-based access control (RBAC) for backup access, execution, and
configuration operations.
"""
from __future__ import annotations

from typing import Optional, Sequence

from fastapi import Security, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Bearer token for Keycloak JWT authentication
bearer_scheme = HTTPBearer(auto_error=False)

BACKUP_READ_ROLE = "backup:read"
BACKUP_CREATE_ROLE = "backup:create"
BACKUP_RUN_ROLE = "backup:run"
BACKUP_CONFIG_ROLE = "backup:configure"
BACKUP_RESTORE_ROLE = "backup:restore"
BACKUP_DELETE_ROLE = "backup:delete"
BACKUP_DOWNLOAD_ROLE = "backup:download"
BACKUP_HISTORY_ROLE = "backup:history"
BACKUP_ADMIN_ROLE = "backup:admin"

BACKUP_ACCESS_ROLES = (
    BACKUP_ADMIN_ROLE,
    BACKUP_READ_ROLE,
    BACKUP_CREATE_ROLE,
    BACKUP_RUN_ROLE,
    BACKUP_CONFIG_ROLE,
    BACKUP_RESTORE_ROLE,
    BACKUP_DELETE_ROLE,
    BACKUP_DOWNLOAD_ROLE,
    BACKUP_HISTORY_ROLE,
)

BACKUP_RUN_ROLES = (
    BACKUP_ADMIN_ROLE,
    BACKUP_CREATE_ROLE,
    BACKUP_RUN_ROLE,
)

BACKUP_CONFIGURATION_ROLES = (
    BACKUP_ADMIN_ROLE,
    BACKUP_CONFIG_ROLE,
)


BACKUP_DOWNLOAD_ROLES = (
    BACKUP_ADMIN_ROLE,
    BACKUP_DOWNLOAD_ROLE,
)

BACKUP_HISTORY_ROLES = (
    BACKUP_ADMIN_ROLE,
    BACKUP_HISTORY_ROLE,
)

def _validate_keycloak_roles(
    bearer_token: Optional[HTTPAuthorizationCredentials],
    required_roles: Sequence[str],
) -> str:
    """Validate a Keycloak bearer token and enforce required roles.

    Args:
        bearer_token: Bearer token credentials from Authorization header.
        required_roles: Roles required to access the endpoint.

    Returns:
        str: Identifier for the authenticated user.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """

    if bearer_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from api.keycloak_auth import get_keycloak_auth

    keycloak = get_keycloak_auth()
    if keycloak is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Keycloak authentication is not configured. "
                "Set KEYCLOAK_ENABLED=true and configure Keycloak settings. "
                "If Keycloak is running but the realm is not set up, run the bootstrap: "
                "./quick-start.ps1 (or .sh) -> Option 16 'Bootstrap Keycloak'"
            ),
        )

    try:
        user = keycloak.validate_token(bearer_token.credentials)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.has_any_role(list(required_roles)):
        required_text = ", ".join(required_roles)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied. Required role(s): "
                f"{required_text}. Your roles: {', '.join(user.roles)}"
            ),
        )

    return f"keycloak:{user.username}"


async def verify_admin_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for backup access endpoints.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(bearer_token, BACKUP_ACCESS_ROLES)


async def verify_run_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for backup execution endpoints.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(bearer_token, BACKUP_RUN_ROLES)


async def verify_config_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for configuration endpoints.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(bearer_token, BACKUP_CONFIGURATION_ROLES)


async def verify_restore_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for restore operations.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(
        bearer_token,
        (BACKUP_ADMIN_ROLE, BACKUP_RESTORE_ROLE),
    )


async def verify_delete_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for delete operations.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(
        bearer_token,
        (BACKUP_ADMIN_ROLE, BACKUP_DELETE_ROLE),
    )


async def verify_download_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for download operations.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(
        bearer_token,
        BACKUP_DOWNLOAD_ROLES,
    )


async def verify_history_key(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Verify Keycloak authentication for history/audit access.

    Args:
        bearer_token: Bearer token credentials from Authorization header.

    Returns:
        str: Authenticated user identifier.

    Raises:
        HTTPException: If authentication fails or roles are insufficient.
    """
    return _validate_keycloak_roles(
        bearer_token,
        BACKUP_HISTORY_ROLES,
    )
