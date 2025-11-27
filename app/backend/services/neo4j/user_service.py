"""
Service layer for User node CRUD operations with Neo4j.

Neo4j-Native Approach:
- Direct Cypher queries (no ORM complexity!)
- Schema-free (no migrations needed!)
- Simple and flexible
"""
from typing import Optional, Dict, Any
from datetime import datetime
from models.neo4j.user import UserNode
from backend.database import get_database_handler


class UserService:
    """
    Service for managing User nodes in Neo4j.
    
    Uses direct Cypher queries - the Neo4j-native way!
    """
    
    def __init__(self):
        """Initialize the service with Neo4j database handler."""
        handler = get_database_handler()
        
        # Verify we're using Neo4j
        if handler.db_type != "neo4j":
            raise RuntimeError("UserService requires Neo4j database")
        
        self.driver = handler.driver
    
    async def create_user(
        self,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user node in Neo4j.
        
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
            check_query = """
            MATCH (u:User {id: $id})
            RETURN u
            """
            
            with self.driver.session() as session:
                result = session.run(check_query, id=user_id)
                if result.single():
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} already exists",
                        "data": None
                    }
                
                # Check if email already exists
                email_check_query = """
                MATCH (u:User {email: $email})
                RETURN u
                """
                result = session.run(email_check_query, email=email)
                if result.single():
                    return {
                        "status": "error",
                        "message": f"Email {email} already registered",
                        "data": None
                    }
                
                # Create user node
                user = UserNode(
                    id=user_id,
                    email=email,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                
                create_query = """
                CREATE (u:User $props)
                RETURN u
                """
                
                result = session.run(create_query, props=user.model_dump())
                record = result.single()
                
                if not record:
                    return {
                        "status": "error",
                        "message": "Failed to create user",
                        "data": None
                    }
                
                created_user = UserNode(**dict(record["u"]))
                return {
                    "status": "success",
                    "message": "User created successfully",
                    "data": created_user.model_dump()
                }
                
        except Exception as e:
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
            query = """
            MATCH (u:User {id: $id})
            RETURN u
            """
            
            with self.driver.session() as session:
                result = session.run(query, id=user_id)
                record = result.single()
                
                if not record:
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} not found",
                        "data": None
                    }
                
                user = UserNode(**dict(record["u"]))
                return {
                    "status": "success",
                    "message": "User retrieved successfully",
                    "data": user.model_dump()
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
        try:
            with self.driver.session() as session:
                # Check if user exists
                check_query = """
                MATCH (u:User {id: $id})
                RETURN u
                """
                result = session.run(check_query, id=user_id)
                if not result.single():
                    return {
                        "status": "error",
                        "message": f"User with ID {user_id} not found",
                        "data": None
                    }
                
                # Build update properties
                updates = {"updated_at": datetime.utcnow().isoformat()}
                
                if email is not None:
                    # Check if new email is already in use
                    email_check_query = """
                    MATCH (u:User {email: $email})
                    WHERE u.id <> $user_id
                    RETURN u
                    """
                    result = session.run(email_check_query, email=email, user_id=user_id)
                    if result.single():
                        return {
                            "status": "error",
                            "message": "Email already in use",
                            "data": None
                        }
                    updates["email"] = email
                
                if username is not None:
                    # Check if new username is already in use
                    username_check_query = """
                    MATCH (u:User {username: $username})
                    WHERE u.id <> $user_id
                    RETURN u
                    """
                    result = session.run(username_check_query, username=username, user_id=user_id)
                    if result.single():
                        return {
                            "status": "error",
                            "message": "Username already in use",
                            "data": None
                        }
                    updates["username"] = username
                
                if first_name is not None:
                    updates["first_name"] = first_name
                
                if last_name is not None:
                    updates["last_name"] = last_name
                
                # Update user
                update_query = """
                MATCH (u:User {id: $id})
                SET u += $updates
                RETURN u
                """
                
                result = session.run(update_query, id=user_id, updates=updates)
                record = result.single()
                
                if not record:
                    return {
                        "status": "error",
                        "message": "Failed to update user",
                        "data": None
                    }
                
                updated_user = UserNode(**dict(record["u"]))
                return {
                    "status": "success",
                    "message": "User updated successfully",
                    "data": updated_user.model_dump()
                }
                
        except Exception as e:
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
