# Testing Guide

Quick reference for testing the API with different databases.

## 🚀 Quick Test (Windows)

### Test with PostgreSQL
```bash
# Start services
start-postgres.bat

# In another terminal, test the API
test-api.bat
```

### Test with Neo4j
```bash
# Start services
start-neo4j.bat

# In another terminal, test the API
test-api.bat
```

## 🚀 Quick Test (Linux/Mac)

### Test with PostgreSQL
```bash
# Start services
cp .env.postgres.example .env
docker-compose -f docker-compose.postgres.yml up --build

# In another terminal, test the API
curl http://localhost:8000/test/db-test
curl http://localhost:8000/test/db-info
```

### Test with Neo4j
```bash
# Start services
cp .env.neo4j.example .env
docker-compose -f docker-compose.neo4j.yml up --build

# In another terminal, test the API
curl http://localhost:8000/test/db-test
curl http://localhost:8000/test/db-info
```

## 📋 What Gets Tested

### Database Endpoints

1. **Connection Test** (`/test/db-test`)
   - Tests database connectivity
   - Returns connection status

2. **Database Info** (`/test/db-info`)
   - Shows which database type is active
   - Returns database details

3. **Sample Query** (`/test/db-sample-query`)
   - Executes a simple query
   - Demonstrates database operations

### File Endpoints

1. **File Count** (`/files/file-count`)
   - Counts files in mounted directory
   - Tests file service

2. **List Extensions** (`/files/list-extensions`)
   - Lists all file extensions
   - Tests file operations

## 🎯 Expected Results

### PostgreSQL Response

```json
{
  "status": "success",
  "message": "Database connection successful",
  "database_type": "postgresql"
}
```

### Neo4j Response

```json
{
  "status": "success",
  "message": "Database connection successful",
  "database_type": "neo4j"
}
```

## 🔍 Manual Testing

### Open Swagger UI

Visit: http://localhost:8000/docs

**Test endpoints:**
1. Click on `/test/db-test`
2. Click "Try it out"
3. Click "Execute"
4. View response

### Access Databases Directly

**PostgreSQL:**
```bash
docker-compose -f docker-compose.postgres.yml exec postgres psql -U postgres -d apidb
```

**Neo4j:**
- Open browser: http://localhost:7474
- Login: neo4j / password

## 🔄 Switch Between Databases

### From PostgreSQL to Neo4j

```bash
# Stop PostgreSQL
docker-compose -f docker-compose.postgres.yml down

# Start Neo4j
start-neo4j.bat  # Windows
# or
cp .env.neo4j.example .env && docker-compose -f docker-compose.neo4j.yml up -d
```

### From Neo4j to PostgreSQL

```bash
# Stop Neo4j
docker-compose -f docker-compose.neo4j.yml down

# Start PostgreSQL
start-postgres.bat  # Windows
# or
cp .env.postgres.example .env && docker-compose -f docker-compose.postgres.yml up -d
```

## 📊 Verify Structure

The template demonstrates the clean separation:

### Routes (HTTP Layer)
- `app/api/routes/test.py` - Database test endpoints
- `app/api/routes/files.py` - File operation endpoints

### Services (Business Logic)
- `app/backend/services/database_service.py` - Database operations
- `app/backend/services/file_service.py` - File operations

### Database Layer (Auto Neo4j/SQL)
- `app/backend/database/factory.py` - Automatically chooses database
- `app/backend/database/neo4j_handler.py` - Neo4j implementation
- `app/backend/database/sql_handler.py` - SQL implementation

## 🎓 Next Steps

After testing:

1. **Read**: `docs/HOW_TO_ADD_ENDPOINT.md` - Learn how to add your own endpoints
2. **Explore**: `docs/PROJECT_STRUCTURE.md` - Understand the structure
3. **Build**: Create your own services and routes

## 🐛 Troubleshooting

### Services won't start

**Check Docker is running:**
```bash
docker ps
```

**Check ports are free:**
```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5432
netstat -ano | findstr :7687

# Linux/Mac
lsof -i :8000
lsof -i :5432
lsof -i :7687
```

### Database connection fails

**Wait for services to be healthy:**
```bash
docker-compose -f docker-compose.postgres.yml ps
```

Look for "healthy" status.

### Can't access Swagger UI

**Check app logs:**
```bash
docker-compose -f docker-compose.postgres.yml logs -f app
```

## 📚 Full Documentation

- **Docker Setup**: `docs/DOCKER_SETUP.md`
- **How to Add Endpoint**: `docs/HOW_TO_ADD_ENDPOINT.md`
- **Project Structure**: `docs/PROJECT_STRUCTURE.md`

Happy testing! 🚀
