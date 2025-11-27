# Database Backend Module

This module provides a flexible, modular database backend that supports multiple database types including Neo4j and SQL databases (PostgreSQL, MySQL, SQLite).

## Architecture

The database backend is organized into the following components:

```
backend/database/
├── __init__.py           # Module exports
├── base.py               # Abstract base class for all database handlers
├── factory.py            # Factory pattern for creating database handlers
├── neo4j_handler.py      # Neo4j implementation
├── sql_handler.py        # SQL database implementation (SQLAlchemy)
├── models_example.py     # Example SQLAlchemy models
└── README.md            # This file
```

## Configuration

### 1. Environment Variables

Configure your database in `.env` file:

```bash
# Database Type (neo4j, postgresql, mysql, sqlite)
DB_TYPE=neo4j

# Neo4j Configuration (when DB_TYPE=neo4j)
NEO4J_URL=bolt://localhost:7687
DB_USER=neo4j
DB_PASSWORD=password

# SQL Configuration (when DB_TYPE=postgresql, mysql, or sqlite)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 2. Supported Database Types

- **neo4j**: Neo4j graph database
- **postgresql**: PostgreSQL relational database
- **mysql**: MySQL relational database
- **sqlite**: SQLite file-based database

## Usage

### Basic Usage

The database handler is automatically initialized in `main.py` on application startup:

```python
from backend.database import get_database_handler

# Get the current database handler
handler = get_database_handler()

# Test connection
result = await handler.test_connection()

# Execute a query
results = await handler.execute_query("SELECT * FROM users")
```

### Neo4j Usage

```python
from backend.database import get_database_handler
from backend.database.neo4j_handler import Neo4jHandler

handler = get_database_handler()

if isinstance(handler, Neo4jHandler):
    # Execute Cypher query
    results = await handler.execute_query(
        "MATCH (n:User) RETURN n LIMIT 10"
    )
```

### SQL Database Usage

```python
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler

handler = get_database_handler()

if isinstance(handler, SQLHandler):
    # Execute SQL query
    results = await handler.execute_query(
        "SELECT * FROM users WHERE active = :active",
        {"active": True}
    )
    
    # Get database session for ORM operations
    async for session in handler.get_db():
        # Use session for SQLAlchemy ORM operations
        pass
```

### Creating SQL Models

1. Copy `models_example.py` to `models.py`
2. Uncomment and modify the example models
3. Define your models using SQLAlchemy:

```python
from sqlalchemy import Column, String, Integer
from backend.database import get_database_handler

handler = get_database_handler()
Base = handler.Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
```

4. Create tables:

```python
from backend.database.models_example import create_tables

create_tables()
```

## Switching Database Types

To switch between database types:

1. Update `DB_TYPE` in your `.env` file
2. Configure the appropriate connection settings
3. Restart your application

The application will automatically use the correct database handler.

## Adding New Database Types

To add support for a new database type:

1. Create a new handler class in `backend/database/` that inherits from `BaseDatabaseHandler`
2. Implement all abstract methods from `BaseDatabaseHandler`
3. Update `factory.py` to include your new handler
4. Update `.env.template` and `settings.py` with new configuration options

Example:

```python
# backend/database/mongodb_handler.py
from .base import BaseDatabaseHandler

class MongoDBHandler(BaseDatabaseHandler):
    def __init__(self, connection_string: str, **kwargs):
        # Initialize MongoDB connection
        pass
    
    def close(self):
        # Close connection
        pass
    
    async def test_connection(self):
        # Test connection
        pass
    
    async def execute_query(self, query, params=None):
        # Execute query
        pass
```

Then update `factory.py`:

```python
elif db_type == "mongodb":
    return MongoDBHandler(
        connection_string=kwargs.get("connection_string", "")
    )
```

## Migration from Old Structure

If you're migrating from the old `backend/Neo4jHandler.py`:

1. The old `Neo4jHandler` class is now at `backend/database/neo4j_handler.py`
2. Update imports:
   ```python
   # Old
   from backend.Neo4jHandler import Neo4jHandler
   
   # New
   from backend.database import get_database_handler
   # or
   from backend.database.neo4j_handler import Neo4jHandler
   ```
3. Use the factory pattern instead of direct instantiation:
   ```python
   # Old
   handler = Neo4jHandler()
   
   # New
   handler = get_database_handler()
   ```

## Best Practices

1. **Always use the factory**: Use `get_database_handler()` instead of directly instantiating handlers
2. **Type checking**: Use `isinstance()` to check handler type before using database-specific features
3. **Connection management**: The factory manages a single instance; don't create multiple handlers
4. **Error handling**: Always wrap database operations in try-except blocks
5. **Async operations**: Use `await` for all database operations

## Testing

Test your database connection:

```bash
curl http://localhost:8000/test/db-test
```

This will return connection status and basic query results.
