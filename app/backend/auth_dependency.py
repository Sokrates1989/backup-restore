"""AWS Cognito JWT authentication dependency for FastAPI endpoints."""

from __future__ import annotations

from typing import Dict

import requests
from fastapi import Depends, HTTPException, Request, status
from jose import jwk, jwt
from jose.exceptions import JWTClaimsError, JWTError, ExpiredSignatureError
from jose.utils import base64url_decode

from api.settings import settings


def _get_cognito_jwks() -> Dict[str, Dict[str, str]]:
    """Fetch the JWKS for the configured Cognito user pool."""
    region = (settings.AWS_REGION or "").strip()
    user_pool = (settings.get_cognito_user_pool_id() or "").strip()

    if not region or not user_pool:
        raise RuntimeError("AWS Cognito configuration is missing")

    jwks_url = (
        f"https://cognito-idp.{region}.amazonaws.com/"
        f"{user_pool}/.well-known/jwks.json"
    )

    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    jwks = response.json()

    if "keys" not in jwks:
        raise ValueError("Invalid JWKS payload returned by Cognito")

    return jwks


def _verify_cognito_token(token: str) -> Dict[str, str]:
    """Verify a JWT access token issued by Cognito."""
    jwks = _get_cognito_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")

    if not kid:
        raise ValueError("Token header missing 'kid'")

    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if not key:
        raise ValueError("Matching JWK not found for token")

    public_key = jwk.construct(key)
    message, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode())

    if not public_key.verify(message.encode(), decoded_signature):
        raise ValueError("Token signature verification failed")

    issuer = (
        f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/"
        f"{settings.get_cognito_user_pool_id()}"
    )

    audience = settings.get_cognito_app_client_id()
    if audience == "app_client_id_is_not_set":
        audience = None

    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
    )

    if claims.get("token_use") != "access":
        raise ValueError("Token is not an access token")

    return claims


async def verify_jwt_token_dependency(request: Request) -> Dict[str, str]:
    """FastAPI dependency to validate Cognito-issued JWT tokens."""

    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )

    token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token is required",
        )

    try:
        claims = _verify_cognito_token(token)
    except (ValueError, ExpiredSignatureError, JWTClaimsError, JWTError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {exc}",
        ) from exc
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Cognito JWKS",
        ) from exc
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification error: {exc}",
        ) from exc

    return {
        "sub": claims.get("sub"),
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
        "username": claims.get("cognito:username") or claims.get("username"),
        "claims": claims,
    }


def get_user_id_from_token(user_info: Dict[str, str] = Depends(verify_jwt_token_dependency)) -> str:
    """Helper dependency returning the authenticated user's ID."""

    user_id = user_info.get("user_id") or user_info.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return user_id
