# Quick CRUD Reference

A condensed cheat sheet for implementing CRUD operations.

## 🚀 Quick Start (3 Steps)

### 1. Create Model (`app/models/your_model.py`)

```python
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
import uuid

def get_base():
    from backend.database import get_database_handler
    from backend.database.sql_handler import SQLHandler
    handler = get_database_handler()
    return handler.Base if isinstance(handler, SQLHandler) else None

Base = get_base()

class YourModel(Base):
    __tablename__ = "your_table"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

### 2. Create Service (`app/backend/services/your_service.py`)

```python
from sqlalchemy import select, func
from models.your_model import YourModel
from backend.database import get_database_handler

class YourService:
    def __init__(self):
        self.handler = get_database_handler()
    
    async def create(self, name: str, description: str = None):
        async with self.handler.AsyncSessionLocal() as session:
            try:
                item = YourModel(name=name, description=description)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return {"status": "success", "data": item.to_dict()}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
    
    async def get(self, item_id: str):
        async with self.handler.AsyncSessionLocal() as session:
            result = await session.execute(
                select(YourModel).where(YourModel.id == item_id)
            )
            item = result.scalar_one_or_none()
            return {"status": "success", "data": item.to_dict()} if item else \
                   {"status": "error", "message": "Not found"}
    
    async def list(self, limit: int = 100, offset: int = 0):
        async with self.handler.AsyncSessionLocal() as session:
            result = await session.execute(
                select(YourModel).limit(limit).offset(offset)
            )
            items = result.scalars().all()
            return {"status": "success", "data": [i.to_dict() for i in items]}
    
    async def update(self, item_id: str, name: str = None, description: str = None):
        async with self.handler.AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(YourModel).where(YourModel.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    return {"status": "error", "message": "Not found"}
                
                if name: item.name = name
                if description: item.description = description
                
                await session.commit()
                await session.refresh(item)
                return {"status": "success", "data": item.to_dict()}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
    
    async def delete(self, item_id: str):
        async with self.handler.AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(YourModel).where(YourModel.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    return {"status": "error", "message": "Not found"}
                
                await session.delete(item)
                await session.commit()
                return {"status": "success", "message": "Deleted"}
            except Exception as e:
                await session.rollback()
                return {"status": "error", "message": str(e)}
```

### 3. Create Routes (`app/api/routes/your_routes.py`)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.your_service import YourService

router = APIRouter(tags=["items"], prefix="/items")
service = YourService()

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

@router.post("/", status_code=201)
async def create(item: ItemCreate):
    result = await service.create(item.name, item.description)
    if result["status"] == "error":
        raise HTTPException(500, result["message"])
    return result

@router.get("/{item_id}")
async def get(item_id: str):
    result = await service.get(item_id)
    if result["status"] == "error":
        raise HTTPException(404, result["message"])
    return result

@router.get("/")
async def list_items(limit: int = 100, offset: int = 0):
    return await service.list(limit, offset)

@router.put("/{item_id}")
async def update(item_id: str, item: ItemUpdate):
    result = await service.update(item_id, item.name, item.description)
    if result["status"] == "error":
        status = 404 if "not found" in result["message"].lower() else 500
        raise HTTPException(status, result["message"])
    return result

@router.delete("/{item_id}")
async def delete(item_id: str):
    result = await service.delete(item_id)
    if result["status"] == "error":
        status = 404 if "not found" in result["message"].lower() else 500
        raise HTTPException(status, result["message"])
    return result
```

### 4. Register Routes (`app/main.py`)

```python
from api.routes import your_routes

app.include_router(your_routes.router)
```

---

## 📊 Common Column Types

```python
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON

# Text
name = Column(String(255))          # VARCHAR with limit
description = Column(Text)          # Unlimited text

# Numbers
age = Column(Integer)               # Whole numbers
price = Column(Float)               # Decimals
quantity = Column(Integer, default=0)

# Boolean
is_active = Column(Boolean, default=True)

# Timestamps
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# JSON (PostgreSQL)
metadata = Column(JSON)

# Constraints
email = Column(String, unique=True, nullable=False, index=True)
```

---

## 🔍 Common Query Patterns

### Filter by Field
```python
result = await session.execute(
    select(Model).where(Model.name == "value")
)
```

### Multiple Conditions (AND)
```python
from sqlalchemy import and_

result = await session.execute(
    select(Model).where(
        and_(Model.name == "value", Model.is_active == True)
    )
)
```

### Multiple Conditions (OR)
```python
from sqlalchemy import or_

result = await session.execute(
    select(Model).where(
        or_(Model.name == "value1", Model.name == "value2")
    )
)
```

### Like/Contains
```python
result = await session.execute(
    select(Model).where(Model.name.like("%search%"))
)
```

### Ordering
```python
result = await session.execute(
    select(Model).order_by(Model.created_at.desc())
)
```

### Count
```python
from sqlalchemy import func

result = await session.execute(
    select(func.count()).select_from(Model)
)
count = result.scalar()
```

---

## 🧪 Testing Commands

```bash
# Initialize table
curl -X POST http://localhost:8000/examples/initialize

# Create
curl -X POST http://localhost:8000/examples/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "description": "Description"}'

# List
curl http://localhost:8000/examples/

# Get by ID
curl http://localhost:8000/examples/{id}

# Update
curl -X PUT http://localhost:8000/examples/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete
curl -X DELETE http://localhost:8000/examples/{id}
```

---

## 🔗 Relationships

### One-to-Many
```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    posts = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
```

### Many-to-Many
```python
from sqlalchemy import Table

# Association table
user_roles = Table('user_roles', Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('role_id', String, ForeignKey('roles.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    roles = relationship("Role", secondary=user_roles, back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True)
    users = relationship("User", secondary=user_roles, back_populates="roles")
```

---

## ⚠️ Common Pitfalls

1. **Forgetting `await`**: All database operations must use `await`
2. **Not rolling back**: Always rollback on exceptions
3. **Not refreshing**: Use `await session.refresh(obj)` after commit to get updated fields
4. **Forgetting imports**: Import `func` for timestamps, `select` for queries
5. **Wrong session usage**: Use `AsyncSessionLocal()` as async context manager

---

## 📚 See Also

- [CRUD_EXAMPLE.md](./CRUD_EXAMPLE.md) - Full detailed guide
- [DATABASE.md](./DATABASE.md) - Database configuration
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Project structure
