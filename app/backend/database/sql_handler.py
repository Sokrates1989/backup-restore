"""
SQL database handler implementation using SQLAlchemy.
Supports PostgreSQL, MySQL, SQLite, and other SQL databases.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from .base import BaseDatabaseHandler


class SQLHandler(BaseDatabaseHandler):
    """Handler for SQL databases using SQLAlchemy."""
    
    def __init__(self, database_url: str, echo: bool = False, **kwargs):
        """
        Initialize SQL database connection.
        
        Args:
            database_url: SQLAlchemy database URL
                Examples:
                - PostgreSQL: postgresql://user:password@localhost:5432/dbname
                - MySQL: mysql://user:password@localhost:3306/dbname
                - SQLite: sqlite:///path/to/database.db
            echo: Whether to log SQL queries
        """
        self.database_url = database_url
        self.echo = echo
        
        # Synchronous engine for migrations and simple operations
        self.engine = create_engine(database_url, echo=echo)
        
        # Asynchronous engine for API operations
        async_url = self._get_async_url(database_url)
        self.async_engine = create_async_engine(async_url, echo=echo)
        
        # Session factories
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self.AsyncSessionLocal = sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Base class for models
        self.Base = declarative_base()
        self.metadata = MetaData()
    
    def _get_async_url(self, url: str) -> str:
        """
        Convert synchronous database URL to async version.
        
        Args:
            url: Synchronous database URL
            
        Returns:
            Async database URL
        """
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://")
        elif url.startswith("sqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://")
        return url
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            # Async engine disposal should be done in an async context
            # For now, we'll just set it to None
            self.async_engine = None
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the database connection.
        
        Returns:
            Dict with status and message
        """
        try:
            async with self.AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                return {
                    "status": "success",
                    "message": "SQL database connection successful",
                    "database_type": "sql",
                    "database_url": self._mask_password(self.database_url)
                }
        except Exception as e:
            # Print full traceback for debugging (only if DEBUG is enabled)
            if self.echo:  # echo is set to DEBUG value
                import traceback
                print(f"🔍 Debug - Full error traceback:")
                traceback.print_exc()
                print(f"🔍 Debug - Error type: {type(e).__name__}")
                print(f"🔍 Debug - Error args: {e.args}")
            return {
                "status": "error",
                "message": f"SQL database connection failed: {str(e)}",
                "database_type": "sql"
            }
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Any]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of query results as dictionaries
        """
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(text(query), params or {})
            # Convert rows to dictionaries
            rows = result.fetchall()
            if rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
            return []
    
    async def get_db(self):
        """
        Get an async database session (dependency injection).
        
        Yields:
            AsyncSession: Database session
        """
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    
    def create_tables(self):
        """Create all tables defined in the Base metadata."""
        self.Base.metadata.create_all(bind=self.engine)
    
    def _mask_password(self, url: str) -> str:
        """
        Mask password in database URL for logging.
        
        Args:
            url: Database URL
            
        Returns:
            URL with masked password
        """
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)
