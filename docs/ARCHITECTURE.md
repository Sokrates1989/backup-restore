# Architecture Overview

This document describes the architecture and design principles of the FastAPI Python API Template.

## Design Principles

### 1. Separation of Concerns

The codebase is organized into distinct layers:

- **API Layer** (`app/api/`): HTTP routing, request/response handling
- **Backend Layer** (`app/backend/`): Business logic and database operations
- **Models Layer** (`app/models/`): Data models and schemas
- **Main** (`app/main.py`): Application entry point and lifecycle management

### 2. Modular Database Support

The database layer uses a factory pattern to support multiple database types:

```
app/backend/database/
├── base.py              # Abstract interface (BaseDatabaseHandler)
├── factory.py           # Factory for creating handlers
├── neo4j_handler.py     # Neo4j implementation
├── sql_handler.py       # SQL implementation (PostgreSQL, MySQL, SQLite)
├── init_db.py           # Initialization logic
└── queries.py           # Query helpers
```

**Benefits:**
- Easy to switch between databases
- Simple to add new database types
- Consistent interface across all handlers
- Testable and maintainable

### 3. Clean Code Organization

#### API Layer (`app/api/`)

```
api/
├── routes/              # Route handlers
│   ├── test.py         # Test endpoints
│   └── files.py        # File operations
└── settings.py         # Configuration management
```

**Responsibilities:**
- HTTP request/response handling
- Input validation
- Route organization
- Configuration management

#### Backend Layer (`app/backend/`)

```
backend/
└── database/           # Database abstraction
    ├── handlers/       # Database implementations
    ├── init_db.py     # Initialization
    └── queries.py     # Query helpers
```

**Responsibilities:**
- Database connection management
- Query execution
- Business logic
- Data transformation

#### Models Layer (`app/models/`)

```
models/
├── __init__.py
└── example_sql_models.py  # SQLAlchemy models (for SQL databases)
```

**Responsibilities:**
- Data structure definitions
- ORM models (for SQL databases)
- Schema validation

## Application Lifecycle

### Startup Sequence

1. **Load Configuration** (`settings.py`)
   - Read environment variables from `.env`
   - Validate configuration

2. **Initialize Database** (`init_db.py`)
   - Determine database type from `DB_TYPE`
   - Create appropriate handler via factory
   - Test connection
   - Set global instance

3. **Start FastAPI Application** (`main.py`)
   - Register routes
   - Setup middleware
   - Start server

### Request Flow

```
HTTP Request
    ↓
FastAPI Router (app/api/routes/)
    ↓
Route Handler
    ↓
Database Query Helper (app/backend/database/queries.py)
    ↓
Database Handler (Neo4j or SQL)
    ↓
Database
    ↓
Response
```

### Shutdown Sequence

1. **Close Database Connection** (`init_db.py`)
2. **Cleanup Resources**
3. **Stop Server**

## Database Architecture

### Factory Pattern

The `DatabaseFactory` class manages database handler creation:

```python
# Automatic initialization in main.py
await initialize_database()

# Get handler anywhere in the app
handler = get_database_handler()

# Execute queries
results = await handler.execute_query("...")
```

### Handler Interface

All database handlers implement `BaseDatabaseHandler`:

```python
class BaseDatabaseHandler(ABC):
    @abstractmethod
    def close(self): pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]: pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Any]: pass
```

### Adding New Database Types

1. Create new handler class inheriting from `BaseDatabaseHandler`
2. Implement all abstract methods
3. Add to `DatabaseFactory.create_handler()`
4. Update configuration in `settings.py` and `.env.template`

Example:

```python
# app/backend/database/mongodb_handler.py
from .base import BaseDatabaseHandler

class MongoDBHandler(BaseDatabaseHandler):
    def __init__(self, connection_string: str):
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

## Configuration Management

### Environment-Based Configuration

All configuration is managed through environment variables:

```python
# app/api/settings.py
class Settings(BaseSettings):
    DB_TYPE: Literal["neo4j", "postgresql", "mysql", "sqlite"]
    NEO4J_URL: str
    DATABASE_URL: str
    # ...
    
    class Config:
        env_file = ".env"
```

### Configuration Hierarchy

1. `.env` file (local development)
2. Environment variables (production)
3. Default values (fallback)

## Code Quality Standards

### 1. Type Hints

All functions use type hints:

```python
async def execute_query(query: str, params: Optional[Dict] = None) -> List[Any]:
    pass
```

### 2. Docstrings

All public functions have docstrings:

```python
def initialize_database():
    """
    Initialize database handler based on configuration.
    
    Returns:
        dict: Result of connection test with status and message
    """
```

### 3. Error Handling

Proper error handling with informative messages:

```python
try:
    result = await handler.test_connection()
except Exception as e:
    return {"status": "error", "message": str(e)}
```

### 4. Async/Await

Database operations use async/await for better performance:

```python
async def test_database_connection() -> Dict[str, Any]:
    handler = get_database_handler()
    return await handler.test_connection()
```

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
# Test database factory
def test_create_neo4j_handler():
    handler = DatabaseFactory.create_handler(
        db_type="neo4j",
        url="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )
    assert isinstance(handler, Neo4jHandler)
```

### Integration Tests

Test component interactions:

```python
# Test database connection
async def test_database_connection():
    await initialize_database()
    result = await test_database_connection()
    assert result["status"] == "success"
```

### API Tests

Test HTTP endpoints:

```python
# Test endpoint
def test_db_test_endpoint(client):
    response = client.get("/test/db-test")
    assert response.status_code == 200
```

## Security Considerations

### 1. Environment Variables

Sensitive data stored in environment variables:
- Database passwords
- API keys
- Secret keys

### 2. SQL Injection Prevention

Use parameterized queries:

```python
# Good
await handler.execute_query(
    "SELECT * FROM users WHERE id = :id",
    {"id": user_id}
)

# Bad - vulnerable to SQL injection
await handler.execute_query(f"SELECT * FROM users WHERE id = {user_id}")
```

### 3. Connection Security

- Use SSL/TLS for database connections
- Validate certificates
- Use strong passwords

## Performance Optimization

### 1. Connection Pooling

SQL handler uses connection pooling via SQLAlchemy:

```python
async_engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20
)
```

### 2. Async Operations

All database operations are async to avoid blocking:

```python
async def get_users():
    results = await handler.execute_query("SELECT * FROM users")
    return results
```

### 3. Caching

Redis integration for caching frequently accessed data.

## Deployment

### Docker

The application is containerized for consistent deployment:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

Different configurations for different environments:

- **Development**: `.env` with local database
- **Staging**: Environment variables with staging database
- **Production**: Environment variables with production database

## Monitoring and Logging

### Logging

Structured logging throughout the application:

```python
print(f"🔧 Initializing {settings.DB_TYPE} database...")
print(f"✅ {result['message']}")
print(f"❌ {result['message']}")
```

### Health Checks

Health check endpoint for monitoring:

```python
@app.get("/health")
def check_health():
    return {"status": "OK"}
```

### Database Connection Test

Dedicated endpoint for database testing:

```python
@app.get("/test/db-test")
async def test_database():
    return await test_database_connection()
```

## Future Enhancements

### Potential Improvements

1. **Database Migrations**: Add Alembic for SQL schema migrations
2. **Connection Retry Logic**: Automatic reconnection on failure
3. **Query Caching**: Cache frequently executed queries
4. **Metrics Collection**: Prometheus metrics for monitoring
5. **Rate Limiting**: API rate limiting for production
6. **Authentication**: JWT-based authentication
7. **API Versioning**: Version API endpoints

## Summary

This architecture provides:

- ✅ **Flexibility**: Easy to switch databases
- ✅ **Maintainability**: Clean separation of concerns
- ✅ **Scalability**: Async operations and connection pooling
- ✅ **Testability**: Modular design for easy testing
- ✅ **Security**: Environment-based configuration
- ✅ **Performance**: Optimized database operations

The modular design allows the template to grow with your needs while maintaining code quality and organization.
