"""
Keycloak authentication module for FastAPI.

This module provides JWT-based authentication using Keycloak as the identity provider.
It validates access tokens issued by Keycloak and extracts user information and roles.

Usage:
    from api.keycloak_auth import get_current_user, require_role

    @app.get("/protected")
    async def protected_endpoint(user: KeycloakUser = Depends(get_current_user)):
        return {"message": f"Hello {user.username}"}

    @app.get("/admin-only")
    async def admin_endpoint(user: KeycloakUser = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}
"""
from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.settings import settings

import jwt
from jwt import PyJWKClient, PyJWKClientError


@dataclass
class KeycloakUser:
    """
    Represents an authenticated Keycloak user.
    
    Attributes:
        sub: User's unique identifier (subject claim)
        username: User's preferred username
        email: User's email address
        email_verified: Whether email is verified
        name: User's full name
        given_name: User's first name
        family_name: User's last name
        roles: List of realm roles assigned to the user
        token_exp: Token expiration timestamp
        raw_token: The raw JWT token payload
    """
    sub: str
    username: str
    email: str = ""
    email_verified: bool = False
    name: str = ""
    given_name: str = ""
    family_name: str = ""
    roles: List[str] = field(default_factory=list)
    token_exp: Optional[datetime] = None
    raw_token: Dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role: Role name to check
            
        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        """
        Check if user has any of the specified roles.
        
        Args:
            roles: List of role names to check
            
        Returns:
            True if user has at least one of the roles
        """
        return bool(set(self.roles) & set(roles))


class KeycloakAuth:
    """
    Keycloak authentication handler for FastAPI.
    
    This class handles JWT token validation using Keycloak's JWKS endpoint
    and provides dependency injection functions for protecting routes.
    """

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: Optional[str] = None,
        internal_url: Optional[str] = None,
    ):
        """
        Initialize the Keycloak authentication handler.
        
        Args:
            keycloak_url: Base URL of the Keycloak server for issuer validation (e.g., http://localhost:9090)
            realm: Name of the Keycloak realm
            client_id: Client ID for the backend application
            client_secret: Client secret (optional, for confidential clients)
            internal_url: Internal URL for JWKS fetching (e.g., http://keycloak:9090 in Docker)
        """
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Use internal URL for API calls if provided, otherwise use public URL
        self.internal_url = (internal_url or keycloak_url).rstrip("/")
        
        # Build OIDC endpoints - issuer uses public URL, JWKS uses internal URL
        self.issuer = f"{self.keycloak_url}/realms/{self.realm}"
        self.jwks_uri = f"{self.internal_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self.token_endpoint = f"{self.internal_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.userinfo_endpoint = f"{self.internal_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
        
        # Initialize JWKS client (lazy loading)
        self._jwks_client: Optional[PyJWKClient] = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """
        Get or create the JWKS client for token validation.
        
        Returns:
            PyJWKClient instance
        """
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.jwks_uri, cache_keys=True)
        return self._jwks_client

    def _extract_roles(self, token_payload: Dict[str, Any]) -> List[str]:
        """
        Extract realm roles from the token payload.
        
        Args:
            token_payload: Decoded JWT payload
            
        Returns:
            List of role names
        """
        roles = []
        
        # Try to get roles from the 'roles' claim (custom mapper)
        if "roles" in token_payload:
            claim_roles = token_payload["roles"]
            if isinstance(claim_roles, list):
                roles.extend(claim_roles)
            elif isinstance(claim_roles, str):
                roles.append(claim_roles)
        
        # Also check realm_access.roles (default Keycloak structure)
        realm_access = token_payload.get("realm_access", {})
        if isinstance(realm_access, dict) and "roles" in realm_access:
            roles.extend(realm_access["roles"])
        
        # Also check resource_access for client-specific roles
        resource_access = token_payload.get("resource_access", {})
        if isinstance(resource_access, dict):
            for client_roles in resource_access.values():
                if isinstance(client_roles, dict) and "roles" in client_roles:
                    roles.extend(client_roles["roles"])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_roles = []
        for role in roles:
            if role not in seen:
                seen.add(role)
                unique_roles.append(role)
        
        return unique_roles

    def validate_token(self, token: str) -> KeycloakUser:
        """
        Validate a JWT access token and extract user information.
        
        Args:
            token: JWT access token string
            
        Returns:
            KeycloakUser object with user information
            
        Raises:
            HTTPException: If token is invalid, expired, or verification fails
        """
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account",  # Keycloak default audience
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,  # Keycloak audience can vary
                    "require": ["exp", "iat"],  # sub may not always be present
                },
            )
            
            # Extract expiration time
            exp_timestamp = payload.get("exp")
            token_exp = None
            if exp_timestamp:
                token_exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
            # Build user object - use sub, sid, or azp as fallback for user identifier
            user_id = payload.get("sub") or payload.get("sid") or payload.get("azp") or ""
            username = payload.get("preferred_username") or payload.get("azp") or user_id
            return KeycloakUser(
                sub=user_id,
                username=username,
                email=payload.get("email", ""),
                email_verified=payload.get("email_verified", False),
                name=payload.get("name", ""),
                given_name=payload.get("given_name", ""),
                family_name=payload.get("family_name", ""),
                roles=self._extract_roles(payload),
                token_exp=token_exp,
                raw_token=payload,
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except PyJWKClientError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to validate token: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache()
def get_keycloak_auth() -> Optional[KeycloakAuth]:
    """
    Get the KeycloakAuth instance based on settings.
    
    Returns:
        KeycloakAuth instance if Keycloak is enabled, None otherwise
    """
    if not settings.KEYCLOAK_ENABLED:
        return None
    
    return KeycloakAuth(
        keycloak_url=settings.KEYCLOAK_URL,
        realm=settings.KEYCLOAK_REALM,
        client_id=settings.KEYCLOAK_CLIENT_ID,
        client_secret=settings.KEYCLOAK_CLIENT_SECRET,
        internal_url=settings.KEYCLOAK_INTERNAL_URL or None,
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> KeycloakUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    This validates the JWT token from the Authorization header and returns
    the authenticated user information.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        
    Returns:
        KeycloakUser object with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    keycloak = get_keycloak_auth()
    
    if keycloak is None:
        # Keycloak disabled - return a mock admin user for backward compatibility
        return KeycloakUser(
            sub="legacy-api-key",
            username="api-key-user",
            email="",
            roles=["admin", "operator", "viewer"],
            raw_token={},
        )
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Please provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return keycloak.validate_token(credentials.credentials)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[KeycloakUser]:
    """
    FastAPI dependency to optionally get the current user.
    
    Returns None if no token is provided, otherwise validates and returns the user.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        
    Returns:
        KeycloakUser object or None
    """
    if credentials is None:
        return None
    
    keycloak = get_keycloak_auth()
    if keycloak is None:
        return None
    
    try:
        return keycloak.validate_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(*required_roles: str) -> Callable:
    """
    Create a dependency that requires the user to have at least one of the specified roles.
    
    Args:
        required_roles: One or more role names that grant access
        
    Returns:
        FastAPI dependency function
        
    Example:
        @app.get("/admin")
        async def admin_endpoint(user: KeycloakUser = Depends(require_role("admin"))):
            return {"message": "Admin access"}
            
        @app.get("/operator")
        async def operator_endpoint(user: KeycloakUser = Depends(require_role("admin", "operator"))):
            return {"message": "Operator access"}
    """
    async def role_checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if not user.has_any_role(list(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(required_roles)}. Your roles: {', '.join(user.roles)}",
            )
        return user
    
    return role_checker


def require_all_roles(*required_roles: str) -> Callable:
    """
    Create a dependency that requires the user to have ALL of the specified roles.
    
    Args:
        required_roles: Role names that are all required
        
    Returns:
        FastAPI dependency function
    """
    async def role_checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        missing_roles = [r for r in required_roles if r not in user.roles]
        if missing_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required role(s): {', '.join(missing_roles)}",
            )
        return user
    
    return role_checker
