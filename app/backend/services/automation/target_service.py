"""Target CRUD service for backup automation."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

import asyncpg
import psycopg2
from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import encrypt_secrets, is_config_encryption_enabled
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import target_to_dict
from models.sql.backup_automation import AuditEvent


def _is_running_in_docker() -> bool:
    """Detect whether the process is running inside a Docker container.

    Returns:
        bool: True when running in Docker, False otherwise.
    """

    if os.path.exists("/.dockerenv"):
        return True

    cgroup_paths = ["/proc/1/cgroup", "/proc/self/cgroup"]
    for path in cgroup_paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    if "docker" in f.read():
                        return True
        except OSError:
            continue

    return False


def _normalize_local_test_db_address(db_type: str, host: str, port: int) -> tuple[str, int]:
    """Normalize host/port for local test DB connections when running in Docker.

    The Admin UI runs in the user's browser on the host machine. The API runs inside
    a Docker container. When the UI submits "localhost" plus a host-mapped port
    (e.g. 5434 for test-postgres), "localhost" is interpreted inside the container
    and will not reach the target DB.

    This helper maps common local test DB inputs to Docker Compose service DNS names
    and container-internal ports.

    Why do we return a different port than the user entered?
        Docker publishes container ports to the host using `HOST_PORT:CONTAINER_PORT`.
        The user enters the host-exposed port (e.g. 5434), but the API container must
        connect to the database service via the Docker network, which uses the
        container port (e.g. 5432) and the service DNS name.

        Example mappings come from:
            local-deployment/docker-compose.test-databases.yml
        - test-postgres: "5434:5432" (host 5434, container 5432)
        - test-mysql:    "3306:3306" (host 3306, container 3306)
        - test-neo4j:    "7688:7687" (host 7688, container 7687)

    Args:
        db_type: Database type.
        host: Input host.
        port: Input port.

    Returns:
        tuple[str, int]: Normalized (host, port).
    """

    if not _is_running_in_docker():
        return host, port

    localhost_aliases = {"localhost", "127.0.0.1", "::1"}
    if host not in localhost_aliases:
        return host, port

    if db_type == "postgresql" and port == 5434:
        return "test-postgres", 5432

    if db_type == "mysql" and port == 3306:
        return "test-mysql", 3306

    if db_type == "neo4j" and port == 7688:
        return "test-neo4j", 7687

    # Fallback: allow connecting to services running on the host machine.
    # Docker Desktop provides host.docker.internal for reaching the host.
    return "host.docker.internal", port


class TargetService:
    """Service for managing backup targets."""

    def __init__(self, handler: SQLHandler):
        """Initialize the service.

        Args:
            handler: SQL handler.
        """

        self.handler = handler
        self.repo = AutomationRepository()

    async def list_targets(self) -> List[Dict[str, Any]]:
        """List targets.

        Returns:
            List[Dict[str, Any]]: Target dicts.
        """

        async with self.handler.AsyncSessionLocal() as session:
            items = await self.repo.list_targets(session)
            return [target_to_dict(t) for t in items]

    async def test_connection(self, *, db_type: str, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to a database target.

        Args:
            db_type: Database type.
            config: Public configuration (host, port, database).
            secrets: Secrets (username, password).

        Returns:
            Dict[str, Any]: Connection test result.

        Raises:
            ValueError: If connection fails.
        """

        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "")
        username = secrets.get("username") or secrets.get("user") or config.get("user") or ""
        password = secrets.get("password") or ""

        try:
            port_int = int(port) if port is not None else 0
        except (TypeError, ValueError):
            port_int = 0

        if port_int <= 0:
            if db_type == "postgresql":
                port_int = 5432
            elif db_type == "mysql":
                port_int = 3306
            elif db_type == "neo4j":
                port_int = 7687

        if port_int > 0:
            host, port_int = _normalize_local_test_db_address(db_type=db_type, host=host, port=port_int)

        try:
            if db_type == "postgresql":
                # Test PostgreSQL connection
                conn = psycopg2.connect(
                    host=host,
                    port=port_int,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=10
                )
                conn.close()
                return {"db_type": db_type, "host": host, "port": port_int, "database": database}
            
            elif db_type == "mysql":
                # Test MySQL connection
                import pymysql
                conn = pymysql.connect(
                    host=host,
                    port=port_int,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=10
                )
                conn.close()
                return {"db_type": db_type, "host": host, "port": port_int, "database": database}
            
            elif db_type == "sqlite":
                # Test SQLite connection
                import sqlite3
                db_path = config.get("path") or config.get("file") or database
                if not db_path:
                    raise ValueError("Missing SQLite path")

                if not os.path.exists(db_path):
                    raise ValueError(f"SQLite file does not exist: {db_path}")

                conn = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True)
                conn.close()
                return {"db_type": db_type, "path": db_path}
            
            elif db_type == "neo4j":
                # Test Neo4j connection
                from neo4j import GraphDatabase
                uri = f"bolt://{host}:{port_int}"
                if username or password:
                    driver = GraphDatabase.driver(uri, auth=(username, password))
                else:
                    driver = GraphDatabase.driver(uri)
                driver.verify_connectivity()
                driver.close()
                return {"db_type": db_type, "uri": uri}
            
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
        except Exception as exc:
            raise ValueError(f"Connection test failed: {str(exc)}")

    async def create_target(self, *, name: str, db_type: str, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Create a target.

        Args:
            name: Target name.
            db_type: Database type.
            config: Public configuration.
            secrets: Secrets (encrypted at rest).

        Returns:
            Dict[str, Any]: Created target.

        Raises:
            ValueError: If encryption is not configured but secrets are provided.
        """

        if secrets and not is_config_encryption_enabled():
            raise ValueError("Secrets provided but CONFIG_ENCRYPTION_KEY is not configured")

        async with self.handler.AsyncSessionLocal() as session:
            encrypted = encrypt_secrets(secrets) if secrets else None
            target = await self.repo.create_target(
                session,
                name=name,
                db_type=db_type,
                config=config or {},
                config_encrypted=encrypted,
            )

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="target_create",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        target_id=target.id,
                        target_name=target.name,
                        details={"db_type": target.db_type},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return target_to_dict(target)

    async def update_target(
        self,
        target_id: str,
        *,
        name: Optional[str] = None,
        db_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a target.

        Args:
            target_id: Target id.
            name: New name.
            db_type: New db type.
            config: New config.
            secrets: New secrets.
            is_active: Active flag.

        Returns:
            Dict[str, Any]: Updated target.

        Raises:
            ValueError: If target not found or encryption missing.
        """

        async with self.handler.AsyncSessionLocal() as session:
            target = await self.repo.get_target(session, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")

            before = {"name": target.name, "db_type": target.db_type, "is_active": target.is_active}

            secrets_provided = secrets is not None
            encrypted = None
            if secrets_provided:
                if secrets and not is_config_encryption_enabled():
                    raise ValueError("Secrets provided but CONFIG_ENCRYPTION_KEY is not configured")
                encrypted = encrypt_secrets(secrets) if secrets else None

            updated = await self.repo.update_target(
                session,
                target,
                name=name,
                db_type=db_type,
                config=config,
                config_encrypted=encrypted,
                is_active=is_active,
                secrets_provided=secrets_provided,
            )

            try:
                now = datetime.now(timezone.utc)
                after = {"name": updated.name, "db_type": updated.db_type, "is_active": updated.is_active}
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="target_update",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        target_id=updated.id,
                        target_name=updated.name,
                        details={"before": before, "after": after},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
            return target_to_dict(updated)

    async def delete_target(self, target_id: str) -> None:
        """Delete a target.

        Args:
            target_id: Target id.

        Raises:
            ValueError: If target not found.
        """

        async with self.handler.AsyncSessionLocal() as session:
            target = await self.repo.get_target(session, target_id)
            if not target:
                raise ValueError(f"Target not found: {target_id}")
            target_name = target.name
            await self.repo.delete_target(session, target)

            try:
                now = datetime.now(timezone.utc)
                session.add(
                    AuditEvent(
                        id=str(uuid.uuid4()),
                        operation="target_delete",
                        trigger="manual",
                        status="success",
                        started_at=now,
                        finished_at=now,
                        target_id=target_id,
                        target_name=target_name,
                        details={},
                    )
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
