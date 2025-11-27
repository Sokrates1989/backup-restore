"""Request models for SQL example routes."""
from typing import Optional

from pydantic import BaseModel, Field


class ExampleCreateRequest(BaseModel):
    """Request payload for creating a SQL example record."""

    name: str = Field(..., min_length=1, max_length=255, description="Name of the example")
    description: Optional[str] = Field(None, description="Optional description")


class ExampleUpdateRequest(BaseModel):
    """Request payload for updating a SQL example record."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name")
    description: Optional[str] = Field(None, description="New description")
