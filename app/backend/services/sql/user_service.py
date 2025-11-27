"""
User service for handling user-related business logic.
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler
from models.sql.user import User


class UserService:
    """Service for user-related operations."""
    
    def __init__(self):
        """Initialize the user service."""
        self.handler = get_database_handler()
        if not isinstance(self.handler, SQLHandler):
            raise ValueError("UserService requires SQL database")
    
    async def create_user(
        self,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_id: User ID from authentication provider
            email: User email address
            username: Username (auto-generated from email if not provided)
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            Dict with status, message, and data
        """
        try:
            # Generate username from email if not provided
            if not username:
                username = email.split('@')[0]
            
            # Check if user already exists
            async with self.handler.AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} already exists",
                        "data": None
                    }
                
                # Check if email already exists
                result = await session.execute(select(User).where(User.email == email))
                existing_email = result.scalar_one_or_none()
                
                if existing_email:
                    return {
                        "status": "error",
                        "message": f"Email {email} already registered",
                        "data": None
                    }
                
                # Create new user
                new_user = User(
                    id=user_id,
                    email=email,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                return {
                    "status": "success",
                    "message": "User created successfully",
                    "data": new_user.to_dict()
                }
                
        except IntegrityError as e:
            if 'session' in locals():
                await session.rollback()
            return {
                "status": "error",
                "message": f"Database integrity error: {str(e)}",
                "data": None
            }
        except Exception as e:
            if 'session' in locals():
                await session.rollback()
            return {
                "status": "error",
                "message": f"Error creating user: {str(e)}",
                "data": None
            }
    
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with status, message, and data
        """
        try:
            async with self.handler.AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} not found",
                        "data": None
                    }
                
                return {
                    "status": "success",
                    "message": "User retrieved successfully",
                    "data": user.to_dict()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving user: {str(e)}",
                "data": None
            }
    
    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            email: New email address
            username: New username
            first_name: New first name
            last_name: New last name
            
        Returns:
            Dict with status, message, and data
        """
        session = None
        try:
            async with self.handler.AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} not found",
                        "data": None
                    }
                
                # Update fields if provided
                if email is not None:
                    # Check if new email is already in use
                    result = await session.execute(
                        select(User).where(User.email == email, User.id != user_id)
                    )
                    existing_email = result.scalar_one_or_none()
                    if existing_email:
                        return {
                            "status": "error",
                            "message": "Email already in use",
                            "data": None
                        }
                    user.email = email
                
                if username is not None:
                    # Check if new username is already in use
                    result = await session.execute(
                        select(User).where(User.username == username, User.id != user_id)
                    )
                    existing_username = result.scalar_one_or_none()
                    if existing_username:
                        return {
                            "status": "error",
                            "message": "Username already in use",
                            "data": None
                        }
                    user.username = username
                
                if first_name is not None:
                    user.first_name = first_name
                
                if last_name is not None:
                    user.last_name = last_name
                
                await session.commit()
                await session.refresh(user)
                
                return {
                    "status": "success",
                    "message": "User updated successfully",
                    "data": user.to_dict()
                }
                
        except IntegrityError as e:
            if session is not None:
                await session.rollback()
            return {
                "status": "error",
                "message": f"Database integrity error: {str(e)}",
                "data": None
            }
        except Exception as e:
            if session is not None:
                await session.rollback()
            return {
                "status": "error",
                "message": f"Error updating user: {str(e)}",
                "data": None
            }
    
    async def update_username(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        Update only the user's username.
        
        Args:
            user_id: User ID
            username: New username
            
        Returns:
            Dict with status, message, and data
        """
        return await self.update_user(user_id=user_id, username=username)
