"""Target CRUD service for backup automation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import asyncpg
import psycopg2
from backend.database.sql_handler import SQLHandler
from backend.services.automation.config_crypto import encrypt_secrets, is_config_encryption_enabled
from backend.services.automation.repository import AutomationRepository
from backend.services.automation.serializers import target_to_dict


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
        username = secrets.get("username", "")
        password = secrets.get("password", "")

        try:
            if db_type == "postgresql":
                # Test PostgreSQL connection
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=10
                )
                conn.close()
                return {"db_type": db_type, "host": host, "port": port, "database": database}
            
            elif db_type == "mysql":
                # Test MySQL connection
                import pymysql
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=10
                )
                conn.close()
                return {"db_type": db_type, "host": host, "port": port, "database": database}
            
            elif db_type == "sqlite":
                # Test SQLite connection
                import sqlite3
                db_path = config.get("path", database)
                conn = sqlite3.connect(db_path)
                conn.close()
                return {"db_type": db_type, "path": db_path}
            
            elif db_type == "neo4j":
                # Test Neo4j connection
                from neo4j import GraphDatabase
                uri = f"bolt://{host}:{port}"
                driver = GraphDatabase.driver(uri, auth=(username, password))
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
            await self.repo.delete_target(session, target)
