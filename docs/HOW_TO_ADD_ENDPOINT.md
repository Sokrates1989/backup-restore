# How to Add a New Endpoint

This guide shows you exactly how to add a new endpoint to the API.

## 3-Step Process

### Step 1: Create Backend Service

Create your business logic in `app/backend/services/`

**Example:** `app/backend/services/user_service.py`

```python
"""
User service - handles user-related business logic.
"""
from typing import Dict, List


class UserService:
    """Service for user operations."""
    
    def get_users(self) -> Dict[str, List]:
        """
        Get all users.
        
        Returns:
            Dictionary with list of users
        """
        # Your business logic here
        users = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
        return {"users": users}
    
    def get_user_by_id(self, user_id: int) -> Dict:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user data or error
        """
        # Your business logic here
        if user_id == 1:
            return {"user": {"id": 1, "name": "Alice"}}
        return {"error": "User not found"}
```

### Step 2: Create Route Handler

Create your HTTP endpoints in `app/api/routes/`

**Example:** `app/api/routes/users.py`

```python
"""
Users route - handles user-related HTTP endpoints.

STRUCTURE:
- This file: HTTP request/response handling only
- Business logic: backend/services/user_service.py
"""
from fastapi import APIRouter
from backend.services.user_service import UserService

router = APIRouter(tags=["users"], prefix="/users")

# Initialize service
user_service = UserService()


@router.get("/")
def get_users():
    """Get all users."""
    return user_service.get_users()


@router.get("/{user_id}")
def get_user(user_id: int):
    """Get user by ID."""
    return user_service.get_user_by_id(user_id)
```

### Step 3: Register Route in Main

Add your router to `app/main.py`

```python
# Import your new route
from api.routes import test, files, users  # Add users here

# Register the router
app.include_router(test.router)
app.include_router(files.router)
app.include_router(users.router)  # Add this line
```

## Complete Example

Let's create a "products" endpoint from scratch:

### 1. Create Service: `app/backend/services/product_service.py`

```python
"""Product service - handles product business logic."""
from typing import Dict, List, Optional


class ProductService:
    """Service for product operations."""
    
    def __init__(self):
        # In real app, this would use database
        self.products = [
            {"id": 1, "name": "Laptop", "price": 999.99},
            {"id": 2, "name": "Mouse", "price": 29.99},
        ]
    
    def get_all_products(self) -> Dict[str, List]:
        """Get all products."""
        return {"products": self.products}
    
    def get_product(self, product_id: int) -> Dict:
        """Get product by ID."""
        product = next(
            (p for p in self.products if p["id"] == product_id),
            None
        )
        if product:
            return {"product": product}
        return {"error": "Product not found"}
    
    def search_products(self, query: str) -> Dict[str, List]:
        """Search products by name."""
        results = [
            p for p in self.products 
            if query.lower() in p["name"].lower()
        ]
        return {"products": results, "count": len(results)}
```

### 2. Create Route: `app/api/routes/products.py`

```python
"""
Products route - handles product HTTP endpoints.

STRUCTURE:
- This file: HTTP request/response handling only
- Schemas: api/schemas/products/ (Pydantic models)
- Business logic: backend/services/product_service.py
"""
from fastapi import APIRouter, Query
from backend.services.product_service import ProductService
from api.schemas.products.requests import ProductSearchRequest
from api.schemas.products.responses import ProductListResponse

router = APIRouter(tags=["products"], prefix="/products")

# Initialize service
product_service = ProductService()


@router.get("/", response_model=ProductListResponse)
def get_products():
    """Get all products."""
    return ProductListResponse(**product_service.get_all_products())


@router.get("/search", response_model=ProductListResponse)
def search_products(q: str = Query(..., description="Search query")):
    """Search products by name."""
    request = ProductSearchRequest(query=q)
    return ProductListResponse(**product_service.search_products(request.query))


@router.get("/{product_id}")
def get_product(product_id: int):
    """Get product by ID."""
    return product_service.get_product(product_id)
```

### 3. Register in `app/main.py`

```python
from api.routes import test, files, products

app.include_router(test.router)
app.include_router(files.router)
app.include_router(products.router)
```

### 4. Test Your Endpoint

```bash
# Get all products
curl http://localhost:8000/products/

# Get specific product
curl http://localhost:8000/products/1

# Search products
curl http://localhost:8000/products/search?q=laptop

# View in Swagger UI
open http://localhost:8000/docs
```

## Using Database in Your Service

If your service needs database access:

```python
"""Product service with database."""
from backend.services.database_service import DatabaseService


class ProductService:
    """Service for product operations with database."""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def get_products_from_db(self):
        """Get products from database."""
        # The database service automatically uses Neo4j or SQL
        # based on your .env configuration
        result = await self.db_service.execute_sample_query()
        return result
```

## Project Structure

```
app/
├── api/
│   ├── routes/
│   │   ├── test.py          # Example: Database endpoints
│   │   ├── files.py         # Example: File endpoints
│   │   └── products.py      # Your new endpoint
│   └── schemas/
│       └── products/        # Pydantic request/response models
├── backend/
│   ├── database/            # Database layer (auto Neo4j/SQL)
│   └── services/
│       ├── database_service.py  # Database operations
│       ├── file_service.py      # File operations
│       └── product_service.py   # Your new service
└── main.py                  # Register routes here
```

## Key Principles

### ✅ DO

- **Routes**: Only handle HTTP (request/response)
- **Services**: Contain all business logic
- **Separation**: Keep routes thin, services fat
- **Reusability**: Services can be used by multiple routes

### ❌ DON'T

- Put business logic in routes
- Access database directly from routes
- Mix HTTP concerns with business logic
- Duplicate code between routes

## Real-World Example

### Bad (Everything in Route)

```python
# ❌ DON'T DO THIS
@router.get("/users")
def get_users():
    # Business logic in route - BAD!
    if not db_connected:
        return {"error": "Database not connected"}
    
    users = []
    for row in db.execute("SELECT * FROM users"):
        users.append({
            "id": row[0],
            "name": row[1],
            "email": row[2]
        })
    
    return {"users": users}
```

### Good (Separated)

```python
# ✅ DO THIS

# Route: app/api/routes/users.py
@router.get("/users")
async def get_users():
    return await user_service.get_users()

# Service: app/backend/services/user_service.py
async def get_users(self):
    if not await self.db_service.test_connection():
        return {"error": "Database not connected"}
    
    users = await self.db_service.execute_query(
        "SELECT * FROM users"
    )
    return {"users": users}
```

## Summary

1. **Create service** in `app/backend/services/your_service.py`
2. **Create route** in `app/api/routes/your_route.py`
3. **Register route** in `app/main.py`
4. **Test** at `http://localhost:8000/docs`

That's it! The structure keeps everything clean and maintainable.

## Database Handling

The database layer automatically handles Neo4j vs SQL:

```python
# In your service
from backend.services.database_service import DatabaseService

class YourService:
    def __init__(self):
        self.db = DatabaseService()
    
    async def your_method(self):
        # This works with BOTH Neo4j and SQL
        # The database type is configured in .env
        result = await self.db.test_connection()
        return result
```

You don't need to worry about which database is being used - it's handled automatically!
