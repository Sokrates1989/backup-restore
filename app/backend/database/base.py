"""
Base database handler interface.
All database implementations should inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseDatabaseHandler(ABC):
    """Abstract base class for database handlers."""
    
    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize the database handler with configuration."""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connections."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the database connection.
        
        Returns:
            Dict with status and message
        """
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Any]:
        """
        Execute a database query.
        
        Args:
            query: The query string
            params: Optional parameters for the query
            
        Returns:
            List of results
        """
        pass
