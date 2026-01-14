"""Security headers middleware.

This module provides a lightweight Content Security Policy (CSP) setup that is
intended to harden the static admin UI served by this application.

The policy is deliberately conservative and is only applied to HTML responses
coming from the bundled website (text/html). It is not applied to Swagger UI
(/docs) to avoid breaking FastAPI's documentation assets.
"""

from __future__ import annotations

from fastapi import FastAPI, Request


_DEFAULT_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "img-src 'self' data:; "
    "style-src 'self'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'"
)

_EXCLUDED_PREFIXES = (
    "/docs",
    "/redoc",
)

_EXCLUDED_PATHS = (
    "/openapi.json",
)


def _should_apply_csp(*, request: Request, content_type: str) -> bool:
    """Return True when the CSP header should be applied.

    Args:
        request: Incoming request.
        content_type: Response content-type header value.

    Returns:
        bool: True when CSP should be applied.
    """

    path = request.url.path or ""
    if path in _EXCLUDED_PATHS:
        return False

    for prefix in _EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False

    return "text/html" in (content_type or "").lower()


async def add_security_headers(request: Request, call_next):
    """Add security headers to UI HTML responses.

    Args:
        request: Incoming request.
        call_next: Next ASGI middleware/callable.

    Returns:
        Response: The downstream response with CSP applied when appropriate.
    """

    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    )

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").lower()
    is_https = forwarded_proto == "https" or (request.url.scheme or "").lower() == "https"
    if is_https:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    content_type = response.headers.get("content-type", "")
    if _should_apply_csp(request=request, content_type=content_type):
        response.headers.setdefault("Content-Security-Policy", _DEFAULT_CSP)

    return response


def setup_security_headers_middleware(app: FastAPI) -> None:
    """Register the security headers middleware.

    Args:
        app: The FastAPI application instance.

    Returns:
        None
    """

    app.middleware("http")(add_security_headers)
