"""Response models for SQL example routes."""
from typing import List, Optional

from pydantic import BaseModel


class ExampleResponse(BaseModel):
    """Response payload for a single SQL example record."""

    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Sample Example",
                "description": "This is a sample SQL example record",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        }


class ExampleListResponse(BaseModel):
    """Response payload for listing SQL example records."""

    status: str
    data: List[ExampleResponse]
    pagination: dict


class ExampleMutationResponse(BaseModel):
    """Standard response for create/update/delete operations."""

    status: str
    message: str
    data: ExampleResponse | None = None


class ExampleDetailResponse(BaseModel):
    """Response payload for retrieving a single SQL example record."""

    status: str
    data: ExampleResponse
