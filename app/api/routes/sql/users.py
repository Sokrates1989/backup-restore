"""
User management routes with JWT authentication.

This module provides endpoints for user CRUD operations with authentication.
Users can only access and modify their own data.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from backend.services.sql.user_service import UserService
from backend.auth_dependency import verify_jwt_token_dependency, get_user_id_from_token
from api.schemas.users.requests import (
    UserCreateRequest,
    UserUpdateRequest,
    UsernameUpdateRequest,
)
from api.schemas.users.responses import (
    UserResponse,
    UserMutationResponse,
)

router = APIRouter(tags=["users"], prefix="/users")


# Helper function to get service instance
def get_service() -> UserService:
    """Get UserService instance."""
    return UserService()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreateRequest,
    user_info: dict = Depends(verify_jwt_token_dependency)
):
    """
    Create a new user.
    
    Requires JWT authentication. The user ID in the request must match
    the authenticated user's ID from the token.
    
    Request body:
    - id: User ID from authentication provider (must match token)
    - email: User email address
    - username: Optional username (auto-generated from email if not provided)
    - first_name: Optional first name
    - last_name: Optional last name
    
    Returns:
    - 201: User created successfully
    - 400: User already exists or validation error
    - 403: User ID doesn't match authenticated user
    - 500: Database error
    """
    # Verify that the user is creating their own account
    token_user_id = user_info.get("user_id") or user_info.get("sub")
    if user.id != token_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create user account for another user"
        )
    
    service = get_service()
    result = await service.create_user(
        user_id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    if result["status"] == "error":
        if "already exists" in result["message"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return UserMutationResponse(**result)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user_id: str = Depends(get_user_id_from_token)
):
    """
    Get a user by ID.
    
    Requires JWT authentication. Users can only retrieve their own information.
    
    Path parameters:
    - user_id: User ID
    
    Returns:
    - 200: User found
    - 403: Not authorized to access this user
    - 404: User not found
    - 500: Database error
    """
    # Verify that the user is accessing their own data
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's information"
        )
    
    service = get_service()
    result = await service.get_user(user_id)
    
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return UserResponse(**result["data"])


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdateRequest,
    current_user_id: str = Depends(get_user_id_from_token)
):
    """
    Update a user's information.
    
    Requires JWT authentication. Users can only update their own information.
    
    Path parameters:
    - user_id: User ID
    
    Request body:
    - email: Optional new email
    - username: Optional new username
    - first_name: Optional new first name
    - last_name: Optional new last name
    
    At least one field must be provided.
    
    Returns:
    - 200: User updated successfully
    - 400: No fields provided or validation error
    - 403: Not authorized to update this user
    - 404: User not found
    - 500: Database error
    """
    # Verify that the user is updating their own data
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's information"
        )
    
    # Check if at least one field is provided
    if all(v is None for v in [
        user_update.email,
        user_update.username,
        user_update.first_name,
        user_update.last_name
    ]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update"
        )
    
    service = get_service()
    result = await service.update_user(
        user_id=user_id,
        email=user_update.email,
        username=user_update.username,
        first_name=user_update.first_name,
        last_name=user_update.last_name
    )
    
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
        if "already in use" in result["message"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return UserMutationResponse(**result)


@router.patch("/{user_id}/username")
async def update_username(
    user_id: str,
    username_update: UsernameUpdateRequest,
    current_user_id: str = Depends(get_user_id_from_token)
):
    """
    Update only the user's username.
    
    Requires JWT authentication. Users can only update their own username.
    
    Path parameters:
    - user_id: User ID
    
    Request body:
    - username: New username (1-255 characters)
    
    Returns:
    - 200: Username updated successfully
    - 403: Not authorized to update this user
    - 404: User not found
    - 500: Database error
    """
    # Verify that the user is updating their own data
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's username"
        )
    
    service = get_service()
    result = await service.update_username(
        user_id=user_id,
        username=username_update.username
    )
    
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return UserMutationResponse(**result)
