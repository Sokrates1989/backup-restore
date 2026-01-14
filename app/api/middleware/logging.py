"""Request logging middleware for debugging."""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import FastAPI, Request
from starlette.responses import Response

from api.settings import settings


_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-admin-key",
    "x-restore-key",
    "x-delete-key",
}

_SENSITIVE_JSON_KEYS = {
    "password",
    "db_password",
    "private_key",
    "private_key_passphrase",
    "service_account_json",
    "api_key",
    "token",
}


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of headers with sensitive values redacted.

    Args:
        headers: Header mapping.

    Returns:
        Dict[str, str]: Redacted headers.
    """

    redacted: Dict[str, str] = {}
    for key, value in (headers or {}).items():
        if key.lower() in _SENSITIVE_HEADER_NAMES:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def _redact_json(value: Any) -> Any:
    """Recursively redact known secret fields in a JSON-like value.

    Args:
        value: JSON-like value.

    Returns:
        Any: Redacted value.
    """

    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if str(k).lower() in _SENSITIVE_JSON_KEYS:
                out[k] = "<redacted>"
            else:
                out[k] = _redact_json(v)
        return out
    if isinstance(value, list):
        return [_redact_json(v) for v in value]
    return value


async def log_request_headers(request: Request, call_next):
    """
    Log request and response details for debugging purposes.
    
    This middleware is only active when DEBUG mode is enabled.
    """
    if request.url.path == "/health":
        return await call_next(request)

    # Output basic request info.
    print(f"🔹 Received request: {request.method} {request.url}")

    # Read and log the request headers (redacted).
    headers = _redact_headers(dict(request.headers))
    print(f"🔹 Request headers: {headers}")

    # Read and log the request body (handle non-text/binary bodies safely)
    body = await request.body()
    if body:
        body_text: str
        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            try:
                parsed = json.loads(body)
                body_text = json.dumps(_redact_json(parsed), ensure_ascii=False)
            except Exception:
                body_text = f"<invalid json body: {len(body)} bytes>"
        else:
            try:
                body_text = body.decode("utf-8")
            except UnicodeDecodeError:
                body_text = f"<non-text body: {len(body)} bytes>"

        if len(body_text) > 8192:
            body_text = body_text[:8192] + "...<truncated>"
    else:
        body_text = "No Body"
    print(f"🔹 Request body: {body_text}")

    response = await call_next(request)

    print(f"🟪 Response status: {response.status_code}")
    print(f"🟪 Response headers: {dict(response.headers)}")

    response_body = getattr(response, "body", None)
    is_streaming = getattr(response, "body_iterator", None) is not None and response_body in (None, b"")

    if is_streaming:
        print("🟪 Response body: <streaming response>")
        return response

    if isinstance(response, Response) and isinstance(response_body, (bytes, bytearray)):
        content_type = (response.headers.get("content-type") or "").lower()
        is_binary = any(
            binary_type in content_type
            for binary_type in [
                "application/octet-stream",
                "application/gzip",
                "application/zip",
                "image/",
                "video/",
                "audio/",
                "application/pdf",
            ]
        )

        if is_binary:
            print(f"🟪 Response body: <Binary content, {len(response_body)} bytes>")
        elif len(response_body) > 64 * 1024:
            print(f"🟪 Response body: <{len(response_body)} bytes, truncated>")
        elif "application/json" in content_type:
            try:
                parsed = json.loads(response_body)
                print(f"🟪 Response body: {json.dumps(_redact_json(parsed), ensure_ascii=False)}")
            except Exception:
                print(f"🟪 Response body: <invalid json body: {len(response_body)} bytes>")
        else:
            try:
                print(f"🟪 Response body: {response_body.decode('utf-8')}")
            except UnicodeDecodeError:
                print(f"🟪 Response body: <non-text body: {len(response_body)} bytes>")
    else:
        print("🟪 Response body: No Body")

    # call_next returns a streaming Response whose body_iterator can only be consumed once.
    # We iterate above to log the payload, so we must rebuild the Response to forward the body.
    # Only pass background if it exists to avoid "await None" error.
    response_kwargs = {
        "content": response_body,
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "media_type": response.media_type,
    }
    
    # Only add background if it's not None (avoids TypeError: object NoneType can't be used in 'await' expression)
    if response.background is not None:
        response_kwargs["background"] = response.background
    
    new_response = Response(**response_kwargs)
    return new_response


def setup_logging_middleware(app: FastAPI) -> None:
    """
    Configure request logging middleware for the FastAPI application.
    
    This middleware is only enabled when DEBUG mode is active.
    
    Args:
        app: The FastAPI application instance
    """
    if settings.DEBUG:
        app.middleware("http")(log_request_headers)
