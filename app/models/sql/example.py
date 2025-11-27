"""
Example SQLAlchemy model demonstrating basic CRUD operations.

This is a template example showing how to:
1. Define a database table with SQLAlchemy
2. Use proper column types and constraints
3. Implement timestamps

To create your own models:
1. Copy this file and rename it (e.g., user.py, product.py)
2. Modify the table name and columns
3. Import in your service layer
4. Run create_tables() to initialize the schema
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid


# Create Base - will be properly initialized when database handler is ready
Base = declarative_base()


class Example(Base):
    """
    Example model with basic fields.
    
    Demonstrates:
    - UUID primary key
    - Text fields with constraints
    - Automatic timestamps
    """
    __tablename__ = "examples"
    
    # Primary key - UUID as string
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Text field - required
    name = Column(String(255), nullable=False, index=True)
    
    # Text field - optional, longer content
    description = Column(Text, nullable=True)
    
    # Timestamps - automatically managed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def create_example_table():
    """
    Create the examples table in the database.
    
    Call this function once to initialize the table schema.
    You can call it from a startup script or manually.
    """
    from backend.database import get_database_handler
    from backend.database.sql_handler import SQLHandler
    
    handler = get_database_handler()
    if isinstance(handler, SQLHandler):
        # Bind our Base metadata to the handler's engine
        Base.metadata.bind = handler.engine
        # Create only this specific table
        Base.metadata.create_all(handler.engine, tables=[Example.__table__])
        print("✅ Example table created successfully")
        return {"status": "success", "message": "Example table created"}
    else:
        print("⚠️ Not using SQL database, skipping table creation")
        return {"status": "error", "message": "SQL database not configured"}
