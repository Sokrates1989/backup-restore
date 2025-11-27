# CRUD Operations Example Guide

This guide demonstrates how to create database tables and implement full CRUD (Create, Read, Update, Delete) operations in this template.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [File Structure](#file-structure)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [API Endpoints](#api-endpoints)
6. [Testing the API](#testing-the-api)

---

## Overview

The example demonstrates a complete CRUD implementation with:
- **Model**: `Example` table with ID, name, description, and timestamps
- **Service**: Business logic for all CRUD operations
- **Routes**: RESTful API endpoints
- **Validation**: Request/response validation with Pydantic

### Database Schema

```sql
CREATE TABLE examples (
    id VARCHAR PRIMARY KEY,           -- UUID
    name VARCHAR(255) NOT NULL,       -- Required text field
    description TEXT,                 -- Optional text field
    created_at TIMESTAMP NOT NULL,    -- Auto-generated
    updated_at TIMESTAMP              -- Auto-updated
);
```

---

## Quick Start

### 1. Ensure PostgreSQL is Running

Make sure your database is configured in `.env`:

```bash
# PostgreSQL Configuration
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/dbname
```

### 2. Start the Application

```bash
# Using quick-start script
./quick-start.sh

# Or using Docker Compose
docker-compose up
```

### 3. Initialize the Table

Call the initialization endpoint once:

```bash
curl -X POST http://localhost:8000/examples/initialize
```

### 4. Create Your First Example

```bash
curl -X POST http://localhost:8000/examples/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Example",
    "description": "This is a test example"
  }'
```

---

## File Structure

The CRUD example consists of three main files:

```
app/
├── models/
│   └── example.py              # Database model (SQLAlchemy)
├── backend/
│   └── services/
│       └── example_service.py  # Business logic layer
└── api/
    ├── routes/
    │   └── examples.py         # API endpoints (FastAPI)
    └── schemas/
        └── sql/examples/       # Request/response models used by the routes
```

### Layer Responsibilities

| Layer | File | Purpose |
|-------|------|---------|
| **Model** | `models/example.py` | Defines database schema, table structure, and data validation |
| **Service** | `backend/services/example_service.py` | Contains business logic, database operations, error handling |
| **Schemas** | `api/schemas/sql/examples/` | Pydantic request/response models shared across routes |
| **Routes** | `api/routes/examples.py` | HTTP endpoints importing schemas, returning responses |

---

## Step-by-Step Guide

### Step 1: Create Your Model

**File**: `app/models/your_model.py`

```python
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
import uuid

def get_base():
    """Get SQLAlchemy Base from the database handler."""
    from backend.database import get_database_handler
    from backend.database.sql_handler import SQLHandler
    
    handler = get_database_handler()
    if isinstance(handler, SQLHandler):
        return handler.Base
    else:
        raise RuntimeError("SQL handler not initialized")

Base = get_base()

class YourModel(Base):
    __tablename__ = "your_table_name"
    
    # Define your columns
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert model to dictionary for JSON responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

**Common Column Types**:
- `String(length)` - VARCHAR with max length
- `Text` - Unlimited text
- `Integer` - Whole numbers
- `Float` - Decimal numbers
- `Boolean` - True/False
- `DateTime` - Timestamps
- `JSON` - JSON data (PostgreSQL)

### Step 2: Create Your Service

**File**: `app/backend/services/your_service.py`

```python
from typing import Dict, Any
from sqlalchemy import select
from models.your_model import YourModel
from backend.database import get_database_handler
from backend.database.sql_handler import SQLHandler

class YourService:
    def __init__(self):
        self.handler = get_database_handler()
        if not isinstance(self.handler, SQLHandler):
            raise RuntimeError("Service requires SQL database")
    
    async def create_item(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new item."""
        async with self.handler.AsyncSessionLocal() as session:
            try:
                new_item = YourModel(name=name, description=description)
                session.add(new_item)
                await session.commit()
                await session.refresh(new_item)
                return {"status": "success", "data": new_item.to_dict()}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
    
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get a single item by ID."""
        async with self.handler.AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(YourModel).where(YourModel.id == item_id)
                )
                item = result.scalar_one_or_none()
                if item:
                    return {"status": "success", "data": item.to_dict()}
                return {"status": "error", "message": "Item not found"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
    
    async def update_item(self, item_id: str, name: str = None, description: str = None) -> Dict[str, Any]:
        """Update an existing item."""
        async with self.handler.AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(YourModel).where(YourModel.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    return {"status": "error", "message": "Item not found"}
                
                if name is not None:
                    item.name = name
                if description is not None:
                    item.description = description
                
                await session.commit()
                await session.refresh(item)
                return {"status": "success", "data": item.to_dict()}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
    
    async def delete_item(self, item_id: str) -> Dict[str, Any]:
        """Delete an item."""
        async with self.handler.AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(YourModel).where(YourModel.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    return {"status": "error", "message": "Item not found"}
                
                await session.delete(item)
                await session.commit()
                return {"status": "success", "message": "Item deleted"}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
```

### Step 3: Create Your Routes

**File**: `app/api/routes/your_routes.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.your_service import YourService

router = APIRouter(tags=["your-resource"], prefix="/your-resource")
service = YourService()

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

@router.post("/", status_code=201)
async def create_item(item: ItemCreate):
    result = await service.create_item(name=item.name, description=item.description)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.get("/{item_id}")
async def get_item(item_id: str):
    result = await service.get_item(item_id)
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.put("/{item_id}")
async def update_item(item_id: str, item: ItemUpdate):
    result = await service.update_item(item_id, name=item.name, description=item.description)
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.delete("/{item_id}")
async def delete_item(item_id: str):
    result = await service.delete_item(item_id)
    if result["status"] == "error":
        if "not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=500, detail=result["message"])
    return result
```

### Step 4: Register Your Routes

**File**: `app/main.py`

```python
from api.routes import your_routes

app.include_router(your_routes.router)
```

---

## API Endpoints

The example provides the following RESTful endpoints:

### Initialize Table

```http
POST /examples/initialize
```

Creates the database table. Call once before using other endpoints.

**Response**:
```json
{
  "status": "success",
  "message": "Example table created"
}
```

---

### Create Example

```http
POST /examples/
Content-Type: application/json

{
  "name": "Example Name",
  "description": "Optional description"
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "message": "Example created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Example Name",
    "description": "Optional description",
    "created_at": "2024-01-01T12:00:00+00:00",
    "updated_at": null
  }
}
```

---

### Get Example by ID

```http
GET /examples/{example_id}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Example Name",
    "description": "Optional description",
    "created_at": "2024-01-01T12:00:00+00:00",
    "updated_at": null
  }
}
```

**Response** (404 Not Found):
```json
{
  "detail": "Example with id {id} not found"
}
```

---

### List All Examples

```http
GET /examples/?limit=100&offset=0
```

**Query Parameters**:
- `limit` (optional): Max results (1-1000, default: 100)
- `offset` (optional): Skip N results (default: 0)

**Response** (200 OK):
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Example 1",
      "description": "First example",
      "created_at": "2024-01-01T12:00:00+00:00",
      "updated_at": null
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 100,
    "offset": 0,
    "count": 1
  }
}
```

---

### Update Example (Rename)

```http
PUT /examples/{example_id}
Content-Type: application/json

{
  "name": "New Name",
  "description": "Updated description"
}
```

**Note**: At least one field must be provided.

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Example updated successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "New Name",
    "description": "Updated description",
    "created_at": "2024-01-01T12:00:00+00:00",
    "updated_at": "2024-01-01T12:30:00+00:00"
  }
}
```

---

### Delete Example

```http
DELETE /examples/{example_id}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Example {id} deleted successfully"
}
```

---

## Testing the API

### Using cURL

```bash
# 1. Initialize table
curl -X POST http://localhost:8000/examples/initialize

# 2. Create an example
curl -X POST http://localhost:8000/examples/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Example", "description": "Testing CRUD"}'

# 3. List all examples
curl http://localhost:8000/examples/

# 4. Get specific example (replace {id} with actual ID)
curl http://localhost:8000/examples/{id}

# 5. Update example
curl -X PUT http://localhost:8000/examples/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# 6. Delete example
curl -X DELETE http://localhost:8000/examples/{id}
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Initialize table
response = requests.post(f"{BASE_URL}/examples/initialize")
print(response.json())

# Create example
data = {"name": "Python Example", "description": "Created with Python"}
response = requests.post(f"{BASE_URL}/examples/", json=data)
example = response.json()
print(example)

# Get the ID
example_id = example["data"]["id"]

# Get example
response = requests.get(f"{BASE_URL}/examples/{example_id}")
print(response.json())

# Update example
update_data = {"name": "Updated Python Example"}
response = requests.put(f"{BASE_URL}/examples/{example_id}", json=update_data)
print(response.json())

# Delete example
response = requests.delete(f"{BASE_URL}/examples/{example_id}")
print(response.json())
```

### Using FastAPI Swagger UI

1. Start the application
2. Open browser: `http://localhost:8000/docs`
3. Expand the `/examples` endpoints
4. Click "Try it out" on any endpoint
5. Fill in the parameters and click "Execute"

---

## Best Practices

### 1. **Separation of Concerns**
- **Models**: Only database schema
- **Services**: Business logic and database operations
- **Routes**: HTTP handling only

### 2. **Error Handling**
- Always use try/except in services
- Return consistent response format
- Use appropriate HTTP status codes

### 3. **Validation**
- Use Pydantic models for request validation
- Add field constraints (min_length, max_length, etc.)
- Validate business rules in services

### 4. **Database Sessions**
- Always use async context managers
- Commit on success, rollback on error
- Close sessions properly

### 5. **API Design**
- Follow REST conventions
- Use proper HTTP methods (GET, POST, PUT, DELETE)
- Return meaningful status codes
- Include pagination for list endpoints

---

## Common Patterns

### Adding Relationships

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String)
    posts = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True)
    title = Column(String)
    user_id = Column(String, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
```

### Adding Indexes

```python
class Example(Base):
    __tablename__ = "examples"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)  # Unique index
    name = Column(String, index=True)                # Regular index
```

### Adding Constraints

```python
from sqlalchemy import CheckConstraint

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    price = Column(Float, CheckConstraint('price > 0'))
    quantity = Column(Integer, CheckConstraint('quantity >= 0'))
```

---

## Troubleshooting

### Table Already Exists Error
If you get "table already exists", the table was already created. Skip the initialization step.

### Connection Error
Check your `.env` file and ensure PostgreSQL is running:
```bash
docker-compose ps
```

### Import Errors
Make sure all files are in the correct directories and imports use the correct paths.

### Async/Await Errors
All database operations must use `async`/`await` with the async session.

---

## Next Steps

1. **Add Authentication**: Protect endpoints with JWT tokens
2. **Add Filtering**: Implement search and filter parameters
3. **Add Sorting**: Allow sorting by different fields
4. **Add Validation**: Add more complex business rules
5. **Add Tests**: Write unit and integration tests

For more information, see:
- [DATABASE.md](./DATABASE.md) - Database configuration
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Project architecture
