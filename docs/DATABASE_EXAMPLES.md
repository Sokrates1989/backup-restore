# Database-Specific CRUD Examples

This template provides **database-specific CRUD examples** that demonstrate best practices for each database type.

## Overview

The template conditionally registers different example routes based on your `DB_TYPE`:

| Database Type | Routes | Model Type | Use Case |
|--------------|--------|------------|----------|
| **PostgreSQL/MySQL/SQLite** | `/examples/` | SQLAlchemy ORM | Relational data with tables |
| **Neo4j** | `/example-nodes/` | Graph nodes | Graph data with relationships |

## SQL Databases (PostgreSQL, MySQL, SQLite)

### Endpoint: `/examples/`

**Files:**
- Model: `app/models/sql/example.py` (SQLAlchemy)
- Service: `app/backend/services/sql/example_service.py`
- Routes: `app/api/routes/sql/examples.py`

**Features:**
- ✅ SQLAlchemy ORM models
- ✅ Automatic migrations with Alembic
- ✅ UUID primary keys
- ✅ Automatic timestamps
- ✅ Full CRUD operations

**Example Usage:**

```bash
# Create an example
curl -X POST http://localhost:8081/examples/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Example", "description": "Testing SQL database"}'

# List all examples
curl http://localhost:8081/examples/

# Get specific example
curl http://localhost:8081/examples/{id}

# Update example
curl -X PUT http://localhost:8081/examples/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete example
curl -X DELETE http://localhost:8081/examples/{id}
```

**Test Script:**
```powershell
.\testing\test-crud-example.ps1
```

## Neo4j Graph Database

### Endpoint: `/example-nodes/`

**Files:**
- Model: `app/models/neo4j/example_node.py` (Pydantic model - simple!)
- Service: `app/backend/services/neo4j/example_node_service.py` (Direct Cypher queries)
- Routes: `app/api/routes/neo4j/example_nodes.py`

**Neo4j Advantages:**
- ✅ **Schema-free** - No migrations needed!
- ✅ **Simple Pydantic models** - Just for API validation
- ✅ **Direct Cypher queries** - No ORM complexity
- ✅ **Flexible** - Add properties anytime, no schema changes
- ✅ **Graph-native** - Perfect for relationships

**Features:**
- ✅ UUID node identifiers
- ✅ Automatic timestamps
- ✅ Full CRUD operations
- ✅ Name filtering support
- ✅ Pagination

**Example Usage:**

```bash
# Create a node
curl -X POST http://localhost:8082/example-nodes/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Node", "description": "Testing Neo4j"}'

# List all nodes
curl http://localhost:8082/example-nodes/

# Filter by name
curl http://localhost:8082/example-nodes/?name=Test

# Get specific node
curl http://localhost:8082/example-nodes/{id}

# Update node
curl -X PUT http://localhost:8082/example-nodes/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Node"}'

# Delete node
curl -X DELETE http://localhost:8082/example-nodes/{id}

# Delete all nodes (testing only!)
curl -X DELETE http://localhost:8082/example-nodes/
```

**Test Script:**
```powershell
.\testing\test-crud-example-nodes.ps1
```

## How It Works

### Conditional Route Registration

The `app/main.py` file conditionally registers routes based on `DB_TYPE`:

```python
# Conditionally include database-specific routers
if settings.DB_TYPE in ["postgresql", "postgres", "mysql", "sqlite"]:
    # SQL-specific routes - uses SQLAlchemy models
    from api.routes import examples
    app.include_router(examples.router)
    print(f"✅ Registered SQL-specific routes (/examples/) for {settings.DB_TYPE}")
    
elif settings.DB_TYPE == "neo4j":
    # Neo4j-specific routes - uses graph database nodes
    from api.routes import example_nodes
    app.include_router(example_nodes.router)
    print(f"✅ Registered Neo4j-specific routes (/example-nodes/) for {settings.DB_TYPE}")
```

### Startup Logs

**With PostgreSQL:**
```
✅ Registered SQL-specific routes (/examples/) for postgresql
🔄 Running database migrations...
```

**With Neo4j:**
```
✅ Registered Neo4j-specific routes (/example-nodes/) for neo4j
⚠️  Migrations skipped: DB_TYPE=neo4j (only SQL databases supported)
```

## Creating Your Own Models

### For SQL Databases

1. Copy `app/models/sql/example.py` to `app/models/sql/your_model.py`
2. Modify the table name and columns
3. Copy `app/backend/services/sql/example_service.py` to `app/backend/services/sql/your_service.py`
4. Copy `app/api/routes/sql/examples.py` to `app/api/routes/sql/your_routes.py`
5. Create an Alembic migration:
   ```bash
   docker compose exec app pdm run alembic revision --autogenerate -m "Add your_model table"
   ```

### For Neo4j (Schema-Free!)

1. Copy `app/models/neo4j/example_node.py` to `app/models/neo4j/your_node.py`
   - Simple Pydantic model for API validation
   - No complex class definitions needed!
2. Copy `app/backend/services/neo4j/example_node_service.py` to `app/backend/services/neo4j/your_service.py`
   - Write Cypher queries directly
   - No ORM, no complexity
3. Copy `app/api/routes/neo4j/example_nodes.py` to `app/api/routes/neo4j/your_routes.py`
4. **No migrations needed** - Neo4j is schema-free!
5. **No schema definitions** - Just write Cypher and go!

**Example Cypher Query:**
```python
# Create a node - that's it!
query = """
CREATE (n:YourNode {id: $id, name: $name})
RETURN n
"""
```

## API Documentation

When the application is running, visit:
- **Swagger UI**: http://localhost:8081/docs
- **ReDoc**: http://localhost:8081/redoc

The API documentation will show only the routes available for your current database type.

## Benefits of This Approach

✅ **Clean separation** - SQL and graph examples don't interfere  
✅ **No runtime errors** - Routes only registered if they'll work  
✅ **Easy to understand** - Clear examples for each database type  
✅ **Production-ready** - Proper error handling and validation  
✅ **Testable** - Dedicated test scripts for each database type  

## Switching Between Databases

To switch from PostgreSQL to Neo4j (or vice versa):

1. Update `.env`:
   ```bash
   # For PostgreSQL
   DB_TYPE=postgresql
   DB_USER=postgres
   DB_PASSWORD=postgres
   
   # For Neo4j
   DB_TYPE=neo4j
   DB_USER=neo4j
   DB_PASSWORD=neo4jpassword
   ```

2. Restart with the appropriate docker-compose file:
   ```bash
   # PostgreSQL
   docker compose -f local-deployment/docker-compose.postgres.yml up
   
   # Neo4j
   docker compose -f local-deployment/docker-compose.neo4j.yml up
   ```

3. The correct example routes will be automatically registered!

## Next Steps

- Explore the example code to understand the patterns
- Create your own models following the examples
- Modify the examples to fit your use case
- Remove the examples when you're ready for production

For more information, see:
- [DATABASE.md](DATABASE.md) - Database configuration guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Application architecture
