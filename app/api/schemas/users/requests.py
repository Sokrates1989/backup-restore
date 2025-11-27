"""
Request schemas for user endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreateRequest(BaseModel):
    """Schema for creating a new user."""
    id: str = Field(..., description="User ID from authentication provider")
    email: EmailStr = Field(..., description="User email address")
    username: Optional[str] = Field(None, max_length=255, description="Username (auto-generated from email if not provided)")
    first_name: Optional[str] = Field(None, max_length=255, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=255, description="User's last name")


class UserUpdateRequest(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    username: Optional[str] = Field(None, max_length=255, description="New username")
    first_name: Optional[str] = Field(None, max_length=255, description="New first name")
    last_name: Optional[str] = Field(None, max_length=255, description="New last name")


class UsernameUpdateRequest(BaseModel):
    """Schema for updating only the username."""
    username: str = Field(..., min_length=1, max_length=255, description="New username")
