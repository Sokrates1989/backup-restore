"""
Response schemas for user endpoints.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserMutationResponse(BaseModel):
    """Schema for user creation/update responses."""
    status: str
    message: str
    data: Optional[UserResponse] = None
