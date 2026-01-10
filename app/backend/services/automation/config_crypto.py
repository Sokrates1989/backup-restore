"""Encryption helpers for storing sensitive configuration values.

The backup automation tables store public/non-sensitive configuration in JSON
columns and secrets in an encrypted text blob (`config_encrypted`).

Encryption uses a symmetric key provided via `CONFIG_ENCRYPTION_KEY` or
`CONFIG_ENCRYPTION_KEY_FILE`.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from api.settings import settings


class ConfigEncryptionError(RuntimeError):
    """Raised when configuration encryption or decryption fails."""


def is_config_encryption_enabled() -> bool:
    """Return True if a config encryption key is configured.

    Returns:
        bool: True when a non-empty config encryption key is configured.
    """

    return bool(settings.get_config_encryption_key())


def _normalize_fernet_key(raw_key: str) -> bytes:
    """Normalize a user-provided key into a valid Fernet key.

    Fernet keys must be urlsafe-base64-encoded 32-byte values.

    The application accepts either:
    - A valid Fernet key string
    - An arbitrary string, which will be deterministically derived into a Fernet
      key using SHA-256.

    Args:
        raw_key: Key from environment variable or secret file.

    Returns:
        bytes: A Fernet key suitable for `cryptography.fernet.Fernet`.

    Raises:
        ConfigEncryptionError: When raw_key is empty.
    """

    if not raw_key:
        raise ConfigEncryptionError(
            "CONFIG_ENCRYPTION_KEY is not configured. Provide CONFIG_ENCRYPTION_KEY or CONFIG_ENCRYPTION_KEY_FILE."
        )

    candidate = raw_key.strip().encode("utf-8")

    try:
        decoded = base64.urlsafe_b64decode(candidate)
        if len(decoded) == 32:
            return candidate
    except Exception:
        pass

    digest = hashlib.sha256(candidate).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    """Create a Fernet instance using the configured encryption key.

    Returns:
        Fernet: Fernet instance.

    Raises:
        ConfigEncryptionError: When no encryption key is configured.
    """

    raw_key = settings.get_config_encryption_key()
    key = _normalize_fernet_key(raw_key)
    return Fernet(key)


def encrypt_secrets(secrets: Optional[Dict[str, Any]]) -> Optional[str]:
    """Encrypt a secrets dictionary into a token string.

    Args:
        secrets: Secrets dictionary.

    Returns:
        Optional[str]: Encrypted token, or None when secrets is empty.

    Raises:
        ConfigEncryptionError: When encryption fails or key is missing.
    """

    if not secrets:
        return None

    try:
        token = get_fernet().encrypt(json.dumps(secrets).encode("utf-8"))
        return token.decode("utf-8")
    except Exception as exc:
        raise ConfigEncryptionError(f"Failed to encrypt secrets: {exc}") from exc


def decrypt_secrets(token: Optional[str]) -> Dict[str, Any]:
    """Decrypt a token string into a secrets dictionary.

    Args:
        token: Encrypted token.

    Returns:
        Dict[str, Any]: Decrypted secrets (empty dict when token is empty).

    Raises:
        ConfigEncryptionError: When decryption fails.
    """

    if not token:
        return {}

    try:
        raw = get_fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ConfigEncryptionError("Decrypted secrets payload is not a JSON object")
        return data
    except InvalidToken as exc:
        raise ConfigEncryptionError("Invalid encryption token or wrong CONFIG_ENCRYPTION_KEY") from exc
    except Exception as exc:
        raise ConfigEncryptionError(f"Failed to decrypt secrets: {exc}") from exc
