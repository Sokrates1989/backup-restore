"""Response models for Neo4j example routes."""
from typing import List, Optional

from pydantic import BaseModel


class ExampleNodeResponse(BaseModel):
    """Response payload representing a single Neo4j example node."""

    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Sample Node",
                "description": "This is a sample Neo4j node",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        }


class ExampleNodeListResponse(BaseModel):
    """Response payload for a list of Neo4j example nodes."""

    total: int
    offset: int
    limit: int
    data: List[ExampleNodeResponse]
