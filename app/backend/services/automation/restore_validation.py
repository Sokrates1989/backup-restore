"""Restore safety and backup compatibility validation.

This module provides conservative checks to reduce the risk of restoring an
incompatible backup into a target database (e.g. restoring a Neo4j `.cypher`
export into a SQLite target).

Validation is intentionally lightweight (header/snippet based) and optimized for
backups produced by this project.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
from pathlib import Path
from typing import List, Optional, Sequence


_SQLITE_MAGIC = b"SQLite format 3\x00"
_GZIP_MAGIC = b"\x1f\x8b"


@dataclass(frozen=True)
class BackupCompatibility:
    """Outcome of backup compatibility validation."""

    detected_kind: str
    detected_sql_flavor: Optional[str]
    warnings: List[str]


def canonical_db_type(db_type: str) -> str:
    """Normalize db_type values.

    Args:
        db_type: Raw db_type.

    Returns:
        str: Canonical db_type.
    """

    raw = str(db_type or "").strip().lower()
    if raw == "postgres":
        return "postgresql"
    return raw


def allowed_backup_name_extensions_for_db_type(db_type: str) -> Sequence[str]:
    """Return allowed filename suffixes for backups of the given db_type.

    Args:
        db_type: Target db_type.

    Returns:
        Sequence[str]: Allowed suffixes (including multi-part ones like `.sql.gz`).
    """

    def _with_encryption_suffixes(values: Sequence[str]) -> Sequence[str]:
        expanded = list(values)
        for suf in values:
            expanded.append(f"{suf}.enc")
        return tuple(expanded)

    t = canonical_db_type(db_type)
    if t == "neo4j":
        return _with_encryption_suffixes((".cypher", ".cypher.gz"))
    if t in ("postgresql", "mysql"):
        return _with_encryption_suffixes((".sql", ".sql.gz"))
    if t == "sqlite":
        return _with_encryption_suffixes((".db", ".db.gz"))
    return ()


def is_backup_name_compatible_with_db_type(*, db_type: str, backup_name: str) -> bool:
    """Check whether a backup filename looks compatible with a target db_type.

    Args:
        db_type: Target db_type.
        backup_name: Backup filename or display name.

    Returns:
        bool: True when the suffix matches allowed suffixes.
    """

    name = str(backup_name or "").lower()
    allowed = allowed_backup_name_extensions_for_db_type(db_type)
    return bool(allowed) and any(name.endswith(suf) for suf in allowed)


def _read_decompressed_head(path: Path, *, max_bytes: int = 64 * 1024) -> bytes:
    """Read a small header/snippet from a file, transparently decompressing gzip.

    Args:
        path: File path.
        max_bytes: Maximum bytes to read after decompression.

    Returns:
        bytes: Head bytes.

    Raises:
        ValueError: If gzip decompression fails.
    """

    with open(path, "rb") as f:
        head = f.read(2)

    if head == _GZIP_MAGIC:
        try:
            with gzip.open(path, "rb") as gf:
                return gf.read(max_bytes)
        except Exception as exc:
            raise ValueError(f"Backup appears to be gzip but cannot be decompressed: {exc}")

    with open(path, "rb") as f:
        return f.read(max_bytes)


def detect_backup_kind(*, backup_path: Path) -> tuple[str, Optional[str], List[str]]:
    """Detect a backup kind from a local file.

    Args:
        backup_path: Path to the downloaded backup file.

    Returns:
        tuple[str, Optional[str], List[str]]: (kind, sql_flavor, warnings).

    Raises:
        ValueError: If the file is unreadable or malformed.
    """

    if not backup_path.exists():
        raise ValueError(f"Backup file not found: {backup_path}")

    warnings: List[str] = []
    head_bytes = _read_decompressed_head(backup_path)

    if head_bytes.startswith(_SQLITE_MAGIC):
        return "sqlite_db", None, warnings

    text = head_bytes.decode("utf-8", errors="ignore")
    upper = text.upper()

    # Heuristic detection for Neo4j cypher exports.
    if "MATCH (" in upper or "DETACH DELETE" in upper or "CALL DB." in upper:
        return "cypher", None, warnings

    # SQL-like content.
    sql_markers = (
        "CREATE TABLE",
        "INSERT INTO",
        "DROP TABLE",
        "BEGIN TRANSACTION",
        "COMMIT",
        "SET ",
    )
    if any(m in upper for m in sql_markers):
        sql_flavor: Optional[str] = None
        if "POSTGRESQL DATABASE DUMP" in upper or "PG_DUMP" in upper or "SET STATEMENT_TIMEOUT" in upper:
            sql_flavor = "postgresql"
        elif "MYSQL DUMP" in upper or "MARIADB" in upper or "/*!" in text:
            sql_flavor = "mysql"
            if "MARIADB" in upper:
                warnings.append("Backup appears to be a MariaDB/MySQL dump. Restoring to a MySQL-compatible target should work, but syntax edge cases are possible.")
        return "sql", sql_flavor, warnings

    return "unknown", None, warnings


def validate_backup_compatibility(*, target_db_type: str, backup_path: Path) -> BackupCompatibility:
    """Validate whether a backup file is compatible with a restore target.

    Args:
        target_db_type: db_type of the restore target.
        backup_path: Path to the downloaded backup file.

    Returns:
        BackupCompatibility: Detection result and warnings.

    Raises:
        ValueError: If the backup is clearly incompatible or cannot be validated.
    """

    target = canonical_db_type(target_db_type)
    kind, sql_flavor, warnings = detect_backup_kind(backup_path=backup_path)

    if target == "sqlite":
        if kind != "sqlite_db":
            raise ValueError("Selected backup does not look like a SQLite database file")
        return BackupCompatibility(detected_kind=kind, detected_sql_flavor=sql_flavor, warnings=warnings)

    if target == "neo4j":
        if kind != "cypher":
            raise ValueError("Selected backup does not look like a Neo4j cypher export")
        return BackupCompatibility(detected_kind=kind, detected_sql_flavor=sql_flavor, warnings=warnings)

    if target in ("postgresql", "mysql"):
        if kind != "sql":
            raise ValueError("Selected backup does not look like a SQL dump")

        if sql_flavor and sql_flavor != target:
            raise ValueError(f"Selected SQL dump looks like '{sql_flavor}' and is not compatible with target '{target}'")

        return BackupCompatibility(detected_kind=kind, detected_sql_flavor=sql_flavor, warnings=warnings)

    raise ValueError(f"Unsupported target db_type: {target_db_type}")
