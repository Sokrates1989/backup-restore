"""
Database backend module for supporting multiple database types.
"""
from .base import BaseDatabaseHandler
from .factory import get_database_handler
from .init_db import initialize_database, close_database
from .queries import test_database_connection, execute_query

__all__ = [
    "BaseDatabaseHandler",
    "get_database_handler",
    "initialize_database",
    "close_database",
    "test_database_connection",
    "execute_query",
]
