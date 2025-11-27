"""Request models for Neo4j example routes."""
from typing import Optional

from pydantic import BaseModel, Field


class ExampleNodeCreateRequest(BaseModel):
    """Request payload for creating a new Neo4j example node."""

    name: str = Field(..., min_length=1, max_length=255, description="Node name")
    description: Optional[str] = Field(None, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Sample Node",
                "description": "This is a sample Neo4j node",
            }
        }


class ExampleNodeUpdateRequest(BaseModel):
    """Request payload for updating a Neo4j example node."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name")
    description: Optional[str] = Field(None, description="New description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Node Name",
                "description": "Updated description",
            }
        }
