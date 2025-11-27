"""
Service layer for ExampleNode CRUD operations with Neo4j.

Neo4j-Native Approach:
- Direct Cypher queries (no ORM complexity!)
- Schema-free (no migrations needed!)
- Simple and flexible
- Follows Neo4j best practices

This service demonstrates:
1. Creating nodes with MERGE/CREATE
2. Reading nodes with MATCH
3. Updating properties with SET
4. Deleting nodes with DELETE
5. Pagination and filtering

To create your own Neo4j services:
1. Copy this file and rename it
2. Write Cypher queries for your use case
3. No migrations, no schema definitions needed!
"""
from typing import List, Optional
from datetime import datetime
from models.neo4j.example import ExampleNode
from backend.database import get_database_handler


class ExampleNodeService:
    """
    Service for managing ExampleNode instances in Neo4j.
    
    Uses direct Cypher queries - the Neo4j-native way!
    Simple, flexible, and schema-free.
    """
    
    def __init__(self):
        """Initialize the service with Neo4j database handler."""
        handler = get_database_handler()
        
        # Verify we're using Neo4j
        if handler.db_type != "neo4j":
            raise RuntimeError("ExampleNodeService requires Neo4j database")
        
        self.driver = handler.driver
    
    def create(self, name: str, description: Optional[str] = None) -> ExampleNode:
        """
        Create a new ExampleNode in Neo4j using direct Cypher.
        
        Args:
            name: Node name (required)
            description: Node description (optional)
            
        Returns:
            Created ExampleNode instance
        """
        # Create node with Pydantic (generates ID and timestamp)
        node = ExampleNode(name=name, description=description)
        
        # Simple Cypher CREATE query
        query = """
        CREATE (n:ExampleNode $props)
        RETURN n
        """
        
        # Execute and return
        with self.driver.session() as session:
            result = session.run(query, props=node.model_dump())
            record = result.single()
            
            if not record:
                raise Exception("Failed to create node")
            
            # Return Pydantic model from Neo4j properties
            return ExampleNode(**dict(record["n"]))
    
    def get_by_id(self, node_id: str) -> Optional[ExampleNode]:
        """
        Retrieve an ExampleNode by ID using simple MATCH.
        
        Args:
            node_id: UUID of the node
            
        Returns:
            ExampleNode if found, None otherwise
        """
        query = """
        MATCH (n:ExampleNode {id: $id})
        RETURN n
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=node_id)
            record = result.single()
            
            if not record:
                return None
            
            return ExampleNode(**dict(record["n"]))
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        name_filter: Optional[str] = None
    ) -> List[ExampleNode]:
        """
        Retrieve all ExampleNodes with optional filtering and pagination.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            name_filter: Optional filter for name (case-insensitive contains)
            
        Returns:
            List of ExampleNode instances
        """
        # Build query with optional filter
        if name_filter:
            query = """
            MATCH (n:ExampleNode)
            WHERE toLower(n.name) CONTAINS toLower($name_filter)
            RETURN n
            ORDER BY n.created_at DESC
            SKIP $skip
            LIMIT $limit
            """
            params = {"skip": skip, "limit": limit, "name_filter": name_filter}
        else:
            query = """
            MATCH (n:ExampleNode)
            RETURN n
            ORDER BY n.created_at DESC
            SKIP $skip
            LIMIT $limit
            """
            params = {"skip": skip, "limit": limit}
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            return [ExampleNode(**dict(record["n"])) for record in result]
    
    def count(self, name_filter: Optional[str] = None) -> int:
        """
        Count total number of ExampleNodes.
        
        Args:
            name_filter: Optional filter for name (case-insensitive contains)
            
        Returns:
            Total count of nodes
        """
        if name_filter:
            query = """
            MATCH (n:ExampleNode)
            WHERE toLower(n.name) CONTAINS toLower($name_filter)
            RETURN count(n) as count
            """
            params = {"name_filter": name_filter}
        else:
            query = """
            MATCH (n:ExampleNode)
            RETURN count(n) as count
            """
            params = {}
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            record = result.single()
            return record["count"] if record else 0
    
    def update(
        self,
        node_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[ExampleNode]:
        """
        Update an ExampleNode's properties using SET.
        
        Args:
            node_id: UUID of the node to update
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Updated ExampleNode if found, None otherwise
        """
        # Build update properties
        updates = {"updated_at": datetime.utcnow().isoformat()}
        
        if name is not None:
            updates["name"] = name
        
        if description is not None:
            updates["description"] = description
        
        # Simple Cypher UPDATE query
        query = """
        MATCH (n:ExampleNode {id: $id})
        SET n += $updates
        RETURN n
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=node_id, updates=updates)
            record = result.single()
            
            if not record:
                return None
            
            return ExampleNode(**dict(record["n"]))
    
    def delete(self, node_id: str) -> bool:
        """
        Delete an ExampleNode using simple DELETE.
        
        Args:
            node_id: UUID of the node to delete
            
        Returns:
            True if deleted, False if not found
        """
        query = """
        MATCH (n:ExampleNode {id: $id})
        DELETE n
        RETURN count(n) as deleted
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=node_id)
            record = result.single()
            return record["deleted"] > 0 if record else False
    
    def delete_all(self) -> int:
        """
        Delete all ExampleNodes (use with caution!).
        
        Returns:
            Number of nodes deleted
        """
        query = """
        MATCH (n:ExampleNode)
        DELETE n
        RETURN count(n) as deleted
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            record = result.single()
            return record["deleted"] if record else 0
