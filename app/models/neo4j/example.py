"""
Example Neo4j node model demonstrating basic CRUD operations.

This is a template example showing how to:
1. Use Pydantic models for validation (API layer)
2. Execute Cypher queries directly (no ORM needed!)
3. Leverage Neo4j's schema-free nature
4. Work with graph database concepts

Neo4j Advantage: Schema-free! No migrations, no rigid table definitions.
Just write Cypher queries and let Neo4j handle the rest.

To create your own node models:
1. Copy this file and rename it (e.g., user_node.py, product_node.py)
2. Define Pydantic model for API validation
3. Add static methods with Cypher queries
4. No migrations needed - Neo4j is schema-free!
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class ExampleNode(BaseModel):
    """
    Example node model for Neo4j graph database.
    
    Uses Pydantic for validation and static methods for Cypher queries.
    This is the Neo4j-native approach - simple, flexible, schema-free!
    
    In Neo4j, this will be stored as:
    (:ExampleNode {id: "uuid", name: "...", description: "...", created_at: "...", updated_at: "..."})
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Sample Node",
                "description": "This is a sample Neo4j node",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None
            }
        }
