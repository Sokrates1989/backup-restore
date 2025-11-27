"""
Example SQLAlchemy models for SQL databases.
Uncomment and modify these when using PostgreSQL, MySQL, or SQLite.

To use these models:
1. Rename this file to match your domain (e.g., user_models.py)
2. Uncomment the model classes below
3. Import Base from the SQL handler
4. Run create_tables() to initialize the database schema
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid


# Example: Get Base from SQL handler
# from backend.database import get_database_handler
# from backend.database.sql_handler import SQLHandler
# 
# handler = get_database_handler()
# if isinstance(handler, SQLHandler):
#     Base = handler.Base
# else:
#     raise RuntimeError("SQL handler not initialized")


# Example User model
# class User(Base):
#     __tablename__ = "users"
#     
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
#     username = Column(String, unique=True, index=True, nullable=False)
#     email = Column(String, unique=True, index=True, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     
#     # Relationships
#     items = relationship("Item", back_populates="owner")


# Example Item model
# class Item(Base):
#     __tablename__ = "items"
#     
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
#     title = Column(String, nullable=False)
#     description = Column(Text)
#     owner_id = Column(String, ForeignKey("users.id"))
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     
#     # Relationships
#     owner = relationship("User", back_populates="items")


# Helper function to create tables
# def create_tables():
#     """Create all database tables."""
#     from backend.database import get_database_handler
#     from backend.database.sql_handler import SQLHandler
#     
#     handler = get_database_handler()
#     if isinstance(handler, SQLHandler):
#         handler.create_tables()
#         print("✅ Database tables created successfully")
#     else:
#         print("⚠️ Not using SQL database, skipping table creation")
