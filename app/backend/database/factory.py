"""
Database factory for creating the appropriate database handler based on configuration.
"""
from typing import Optional
from .base import BaseDatabaseHandler
from .neo4j_handler import Neo4jHandler
from .sql_handler import SQLHandler


class DatabaseFactory:
    """Factory class for creating database handlers."""
    
    _instance: Optional[BaseDatabaseHandler] = None
    
    @classmethod
    def create_handler(
        cls,
        db_type: str,
        **kwargs
    ) -> BaseDatabaseHandler:
        """
        Create a database handler based on the specified type.
        
        Args:
            db_type: Type of database ('neo4j', 'postgresql', 'mysql', 'sqlite', etc.)
            **kwargs: Database-specific configuration parameters
            
        Returns:
            BaseDatabaseHandler: Appropriate database handler instance
            
        Raises:
            ValueError: If database type is not supported
        """
        db_type = db_type.lower()
        
        if db_type == "neo4j":
            return Neo4jHandler(
                url=kwargs.get("url", ""),
                user=kwargs.get("user", ""),
                password=kwargs.get("password", "")
            )
        elif db_type in ["postgresql", "postgres", "mysql", "sqlite", "sql"]:
            return SQLHandler(
                database_url=kwargs.get("database_url", ""),
                echo=kwargs.get("echo", False)
            )
        else:
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: neo4j, postgresql, mysql, sqlite"
            )
    
    @classmethod
    def get_instance(cls) -> Optional[BaseDatabaseHandler]:
        """
        Get the current database handler instance.
        
        Returns:
            Current database handler instance or None
        """
        return cls._instance
    
    @classmethod
    def set_instance(cls, handler: BaseDatabaseHandler):
        """
        Set the database handler instance.
        
        Args:
            handler: Database handler to set as the current instance
        """
        cls._instance = handler
    
    @classmethod
    def close_instance(cls):
        """Close and clear the current database handler instance."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_database_handler() -> BaseDatabaseHandler:
    """
    Get the current database handler instance.
    
    Returns:
        Current database handler
        
    Raises:
        RuntimeError: If no database handler has been initialized
    """
    handler = DatabaseFactory.get_instance()
    if handler is None:
        raise RuntimeError(
            "Database handler not initialized. "
            "Please initialize it in your application startup."
        )
    return handler
