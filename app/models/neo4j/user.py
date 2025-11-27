"""
User node model for Neo4j graph database.

This model represents users in the application with authentication support.
Neo4j is schema-free, so no migrations are needed!
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid


class UserNode(BaseModel):
    """
    User node model for Neo4j graph database.
    
    Uses Pydantic for validation. In Neo4j, this will be stored as:
    (:User {id: "uuid", email: "...", username: "...", ...})
    
    Attributes:
        id: Unique user identifier (from authentication provider)
        email: User's email address
        username: User's username (editable, derived from email if not provided)
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user account is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
    """
    
    id: str  # User ID from authentication provider
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "user-123",
                "email": "user@example.com",
                "username": "John Doe",
                "first_name": "John",
                "last_name": "Doe",
                "is_active": True,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None
            }
        }
