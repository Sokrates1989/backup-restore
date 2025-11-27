"""
Neo4j database handler implementation.
"""
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase
from .base import BaseDatabaseHandler


class Neo4jHandler(BaseDatabaseHandler):
    """Handler for Neo4j graph database."""
    
    def __init__(self, url: str, user: str, password: str, **kwargs):
        """
        Initialize Neo4j connection.
        
        Args:
            url: Neo4j connection URL (e.g., bolt://localhost:7687)
            user: Database username
            password: Database password
        """
        self.db_type = "neo4j"
        self.driver = GraphDatabase.driver(url, auth=(user, password))
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the Neo4j connection.
        
        Returns:
            Dict with status and message
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
                return {
                    "status": "success",
                    "message": "Neo4j connection successful",
                    "database_type": "neo4j"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Neo4j connection failed: {str(e)}",
                "database_type": "neo4j"
            }
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Any]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            params: Optional query parameters
            
        Returns:
            List of query results
        """
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    
    def test_query(self) -> List[Any]:
        """
        Execute a test query (legacy method for compatibility).
        
        Returns:
            List of nodes
        """
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN n LIMIT 1")
            return [record["n"] for record in result]
