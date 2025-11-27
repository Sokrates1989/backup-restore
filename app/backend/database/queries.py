"""
Database query helpers and utilities.
Provides a clean interface for executing database queries.
"""
from typing import Any, Dict, List, Optional
from .factory import get_database_handler
from .neo4j_handler import Neo4jHandler
from .sql_handler import SQLHandler


async def test_database_connection() -> Dict[str, Any]:
    """
    Test database connection and execute a simple query.
    
    Returns:
        dict: Connection status and query results
    """
    handler = get_database_handler()
    
    # Test connection
    connection_result = await handler.test_connection()
    
    # For Neo4j, also run a test query
    if isinstance(handler, Neo4jHandler):
        try:
            query_result = handler.test_query()
            return {
                "status": "success",
                "connection": connection_result,
                "query_result": query_result
            }
        except Exception as e:
            return {
                "status": "partial_success",
                "connection": connection_result,
                "query_error": str(e)
            }
    
    # For SQL databases, run a simple query
    elif isinstance(handler, SQLHandler):
        try:
            query_result = await handler.execute_query("SELECT 1 as test")
            return {
                "status": "success",
                "connection": connection_result,
                "query_result": query_result
            }
        except Exception as e:
            return {
                "status": "partial_success",
                "connection": connection_result,
                "query_error": str(e)
            }
    
    return {
        "status": "success",
        "connection": connection_result
    }


async def execute_query(query: str, params: Optional[Dict] = None) -> List[Any]:
    """
    Execute a database query using the configured handler.
    
    Args:
        query: Query string (Cypher for Neo4j, SQL for SQL databases)
        params: Optional query parameters
        
    Returns:
        List of query results
    """
    handler = get_database_handler()
    return await handler.execute_query(query, params)
