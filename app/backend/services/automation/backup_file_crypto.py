"""Backup file encryption helpers.

This module implements streaming encryption/decryption for backup artifacts using a
user-provided password.

The intent is to support schedule-level backup encryption: scheduled backups can be
encrypted before upload, and restores can decrypt the artifact before applying it.

The encrypted file format is:
    [MAGIC(8)][VERSION(1)][SALT(16)][IV(16)][ITERATIONS(4)][CIPHERTEXT...][HMAC(32)]

Encryption uses:
    - AES-256-CTR for streaming encryption
    - HMAC-SHA256 for integrity
    - PBKDF2-HMAC-SHA256 for key derivation

All operations are implemented in a streaming manner to avoid loading large backups
into memory.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


MAGIC = b"BRBKENC1"
VERSION = 1
SALT_LEN = 16
IV_LEN = 16
HMAC_LEN = 32
HEADER_LEN = 8 + 1 + SALT_LEN + IV_LEN + 4
DEFAULT_ITERATIONS = 200_000
DEFAULT_CHUNK_SIZE = 1024 * 1024


class BackupEncryptionError(RuntimeError):
    """Raised when backup encryption/decryption fails."""


@dataclass(frozen=True)
class EncryptedHeader:
    """Parsed header for an encrypted backup file."""

    salt: bytes
    iv: bytes
    iterations: int


def _derive_keys(*, password: str, salt: bytes, iterations: int) -> tuple[bytes, bytes]:
    """Derive encryption + HMAC keys from a password.

    Args:
        password: User-provided password.
        salt: Random salt.
        iterations: PBKDF2 iteration count.

    Returns:
        tuple[bytes, bytes]: (enc_key, hmac_key).

    Raises:
        BackupEncryptionError: When password is empty.
    """

    if not str(password or "").strip():
        raise BackupEncryptionError("Encryption password is required")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=64,
        salt=salt,
        iterations=int(iterations),
    )
    key_material = kdf.derive(password.encode("utf-8"))
    return key_material[:32], key_material[32:]


def is_encrypted_backup_file(path: Path) -> bool:
    """Return True if the file appears to be encrypted by this module.

    Args:
        path: File path.

    Returns:
        bool: True when the header contains the expected magic bytes.
    """

    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def _read_header(path: Path) -> EncryptedHeader:
    """Read and validate encrypted backup header.

    Args:
        path: Encrypted file path.

    Returns:
        EncryptedHeader: Parsed header.

    Raises:
        BackupEncryptionError: When header is missing or invalid.
    """

    try:
        with open(path, "rb") as f:
            header = f.read(HEADER_LEN)
    except OSError as exc:
        raise BackupEncryptionError(f"Failed to read encrypted backup header: {exc}") from exc

    if len(header) < HEADER_LEN:
        raise BackupEncryptionError("Encrypted backup is truncated (header)")

    if header[: len(MAGIC)] != MAGIC:
        raise BackupEncryptionError("Backup does not appear to be encrypted")

    version = header[len(MAGIC)]
    if version != VERSION:
        raise BackupEncryptionError(f"Unsupported encrypted backup version: {version}")

    offset = len(MAGIC) + 1
    salt = header[offset : offset + SALT_LEN]
    offset += SALT_LEN
    iv = header[offset : offset + IV_LEN]
    offset += IV_LEN
    iterations = struct.unpack(">I", header[offset : offset + 4])[0]

    return EncryptedHeader(salt=salt, iv=iv, iterations=int(iterations))


def encrypt_file(
    *,
    input_path: Path,
    output_path: Path,
    password: str,
    iterations: int = DEFAULT_ITERATIONS,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> None:
    """Encrypt a backup artifact to an output file.

    Args:
        input_path: Path to plaintext backup artifact.
        output_path: Destination path for encrypted artifact.
        password: User-provided password.
        iterations: PBKDF2 iteration count.
        chunk_size: Streaming chunk size.

    Raises:
        BackupEncryptionError: When encryption fails.
    """

    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    enc_key, hmac_key = _derive_keys(password=password, salt=salt, iterations=int(iterations))

    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(iv))
    encryptor = cipher.encryptor()
    mac = hmac.HMAC(hmac_key, hashes.SHA256())

    header = MAGIC + bytes([VERSION]) + salt + iv + struct.pack(">I", int(iterations))

    try:
        with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
            fout.write(header)

            while True:
                chunk = fin.read(int(chunk_size))
                if not chunk:
                    break
                out = encryptor.update(chunk)
                if out:
                    mac.update(out)
                    fout.write(out)

            final = encryptor.finalize()
            if final:
                mac.update(final)
                fout.write(final)

            fout.write(mac.finalize())
    except Exception as exc:
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
        raise BackupEncryptionError(f"Failed to encrypt backup file: {exc}") from exc


def decrypt_file(
    *,
    input_path: Path,
    output_path: Path,
    password: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> None:
    """Decrypt an encrypted backup artifact to an output file.

    Args:
        input_path: Encrypted artifact.
        output_path: Destination path for decrypted bytes.
        password: User-provided password.
        chunk_size: Streaming chunk size.

    Raises:
        BackupEncryptionError: When decryption fails or password is wrong.
    """

    header = _read_header(input_path)
    enc_key, hmac_key = _derive_keys(password=password, salt=header.salt, iterations=header.iterations)

    try:
        total_size = input_path.stat().st_size
    except OSError as exc:
        raise BackupEncryptionError(f"Failed to stat encrypted backup: {exc}") from exc

    min_size = HEADER_LEN + HMAC_LEN
    if total_size < min_size:
        raise BackupEncryptionError("Encrypted backup is truncated")

    ciphertext_size = total_size - HEADER_LEN - HMAC_LEN

    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(header.iv))
    decryptor = cipher.decryptor()
    mac = hmac.HMAC(hmac_key, hashes.SHA256())

    tmp_output = Path(str(output_path) + ".tmp")

    try:
        with open(input_path, "rb") as fin, open(tmp_output, "wb") as fout:
            fin.seek(HEADER_LEN)

            remaining = int(ciphertext_size)
            while remaining > 0:
                to_read = min(int(chunk_size), remaining)
                chunk = fin.read(to_read)
                if not chunk:
                    raise BackupEncryptionError("Encrypted backup is truncated (ciphertext)")
                remaining -= len(chunk)

                mac.update(chunk)
                out = decryptor.update(chunk)
                if out:
                    fout.write(out)

            tag = fin.read(HMAC_LEN)
            if len(tag) != HMAC_LEN:
                raise BackupEncryptionError("Encrypted backup is truncated (HMAC)")

            try:
                mac.verify(tag)
            except Exception as exc:
                raise BackupEncryptionError("Invalid encryption password or corrupted backup") from exc

            final = decryptor.finalize()
            if final:
                fout.write(final)

        tmp_output.replace(output_path)
    except BackupEncryptionError:
        try:
            if tmp_output.exists():
                tmp_output.unlink()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            if tmp_output.exists():
                tmp_output.unlink()
        except Exception:
            pass
        raise BackupEncryptionError(f"Failed to decrypt backup file: {exc}") from exc


def decrypt_to_temporary_file(*, encrypted_path: Path, password: str, suffix: str = "") -> Path:
    """Decrypt an encrypted backup to a temporary file on disk.

    Args:
        encrypted_path: Path to encrypted backup artifact.
        password: Encryption password.
        suffix: Optional suffix for the temporary file.

    Returns:
        Path: Decrypted temporary file path.

    Raises:
        BackupEncryptionError: When decryption fails.
    """

    import tempfile

    fd, tmp_name = tempfile.mkstemp(suffix=suffix or ".decrypted")
    os.close(fd)
    out_path = Path(tmp_name)

    try:
        decrypt_file(input_path=encrypted_path, output_path=out_path, password=password)
        return out_path
    except Exception:
        try:
            if out_path.exists():
                out_path.unlink()
        except Exception:
            pass
        raise
