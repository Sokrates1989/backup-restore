"""
User model for SQLAlchemy.

This model represents users in the application with authentication support.
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Create Base - will be properly initialized when database handler is ready
Base = declarative_base()


class User(Base):
    """
    User model with authentication fields.
    
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
    __tablename__ = "users"
    
    # Primary key - user ID from authentication provider
    id = Column(String, primary_key=True)
    
    # User information
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps - automatically managed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def create_user_table():
    """
    Create the users table in the database.
    
    Call this function once to initialize the table schema.
    """
    from backend.database import get_database_handler
    from backend.database.sql_handler import SQLHandler
    
    handler = get_database_handler()
    if isinstance(handler, SQLHandler):
        # Bind our Base metadata to the handler's engine
        Base.metadata.bind = handler.engine
        # Create only this specific table
        Base.metadata.create_all(handler.engine, tables=[User.__table__])
        print("✅ User table created successfully")
        return {"status": "success", "message": "User table created"}
    else:
        print("⚠️ Not using SQL database, skipping table creation")
        return {"status": "error", "message": "SQL database not configured"}
