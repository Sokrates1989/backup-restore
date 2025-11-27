"""
Example service - demonstrates CRUD operations for the Example model.

This service shows best practices for:
- Creating records
- Reading records (single and list)
- Updating records
- Deleting records
- Error handling

Use this as a template for your own services.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.sql.example import Example, Base
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler


class ExampleService:
    """Service for managing Example records."""
    
    def __init__(self):
        """Initialize the service with database handler."""
        self.handler = get_database_handler()
        if not isinstance(self.handler, SQLHandler):
            raise RuntimeError("ExampleService requires SQL database (PostgreSQL/MySQL/SQLite)")
    
    async def create_example(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new example record.
        
        Args:
            name: Name of the example (required)
            description: Optional description
            
        Returns:
            Dictionary with created example data
        """
        async with self.handler.AsyncSessionLocal() as session:
            try:
                # Create new instance
                new_example = Example(
                    name=name,
                    description=description
                )
                
                # Add to session and commit
                session.add(new_example)
                await session.commit()
                await session.refresh(new_example)
                
                return {
                    "status": "success",
                    "message": "Example created successfully",
                    "data": new_example.to_dict()
                }
            except Exception as e:
                await session.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to create example: {str(e)}"
                }
    
    async def get_example(self, example_id: str) -> Dict[str, Any]:
        """
        Get a single example by ID.
        
        Args:
            example_id: UUID of the example
            
        Returns:
            Dictionary with example data or error
        """
        async with self.handler.AsyncSessionLocal() as session:
            try:
                # Query by primary key
                result = await session.execute(
                    select(Example).where(Example.id == example_id)
                )
                example = result.scalar_one_or_none()
                
                if example:
                    return {
                        "status": "success",
                        "data": example.to_dict()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Example with id {example_id} not found"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to get example: {str(e)}"
                }
    
    async def list_examples(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        List all examples with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Dictionary with list of examples
        """
        async with self.handler.AsyncSessionLocal() as session:
            try:
                # Query with pagination
                result = await session.execute(
                    select(Example)
                    .order_by(Example.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                examples = result.scalars().all()
                
                # Get total count
                count_result = await session.execute(
                    select(func.count()).select_from(Example)
                )
                total = count_result.scalar()
                
                return {
                    "status": "success",
                    "data": [example.to_dict() for example in examples],
                    "pagination": {
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "count": len(examples)
                    }
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to list examples: {str(e)}"
                }
    
    async def update_example(
        self, 
        example_id: str, 
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing example (rename or update description).
        
        Args:
            example_id: UUID of the example to update
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Dictionary with updated example data
        """
        async with self.handler.AsyncSessionLocal() as session:
            try:
                # First check if exists
                result = await session.execute(
                    select(Example).where(Example.id == example_id)
                )
                example = result.scalar_one_or_none()
                
                if not example:
                    return {
                        "status": "error",
                        "message": f"Example with id {example_id} not found"
                    }
                
                # Update fields if provided
                if name is not None:
                    example.name = name
                if description is not None:
                    example.description = description
                
                await session.commit()
                await session.refresh(example)
                
                return {
                    "status": "success",
                    "message": "Example updated successfully",
                    "data": example.to_dict()
                }
            except Exception as e:
                await session.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to update example: {str(e)}"
                }
    
    async def delete_example(self, example_id: str) -> Dict[str, Any]:
        """
        Delete an example by ID.
        
        Args:
            example_id: UUID of the example to delete
            
        Returns:
            Dictionary with deletion status
        """
        async with self.handler.AsyncSessionLocal() as session:
            try:
                # Check if exists first
                result = await session.execute(
                    select(Example).where(Example.id == example_id)
                )
                example = result.scalar_one_or_none()
                
                if not example:
                    return {
                        "status": "error",
                        "message": f"Example with id {example_id} not found"
                    }
                
                # Delete the record
                await session.delete(example)
                await session.commit()
                
                return {
                    "status": "success",
                    "message": f"Example {example_id} deleted successfully"
                }
            except Exception as e:
                await session.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to delete example: {str(e)}"
                }
    
    async def initialize_table(self) -> Dict[str, Any]:
        """
        Initialize the example table in the database.
        
        Returns:
            Dictionary with initialization status
        """
        from models.example import create_example_table
        return create_example_table()
