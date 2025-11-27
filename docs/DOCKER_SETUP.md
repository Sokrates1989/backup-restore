# Docker Setup Guide

Complete guide for running the API with Docker using PostgreSQL or Neo4j.

## Quick Start

### Option 1: PostgreSQL Setup

```bash
# 1. Copy environment file
cp .env.postgres.example .env

# 2. Start services
docker-compose -f docker-compose.postgres.yml up --build

# 3. Test the API
curl http://localhost:8000/test/db-test
```

### Option 2: Neo4j Setup

```bash
# 1. Copy environment file
cp .env.neo4j.example .env

# 2. Start services
docker-compose -f docker-compose.neo4j.yml up --build

# 3. Test the API
curl http://localhost:8000/test/db-test
```

## Detailed Setup

### PostgreSQL Setup

#### Step 1: Configure Environment

```bash
# Copy the PostgreSQL example
cp .env.postgres.example .env
```

The `.env` file will contain:
```bash
DB_TYPE=postgresql
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/apidb
DB_NAME=apidb
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
PORT=8000
DEBUG=true
REDIS_URL=redis://redis:6379
```

#### Step 2: Start Services

```bash
# Start all services (app, postgres, redis)
docker-compose -f docker-compose.postgres.yml up --build

# Or run in background
docker-compose -f docker-compose.postgres.yml up -d --build
```

#### Step 3: Verify Services

**Check logs:**
```bash
docker-compose -f docker-compose.postgres.yml logs -f app
```

**Check PostgreSQL:**
```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.postgres.yml exec postgres psql -U postgres -d apidb

# Inside psql:
\l              # List databases
\dt             # List tables
\q              # Quit
```

#### Step 4: Test API

```bash
# Test database connection
curl http://localhost:8000/test/db-test

# Get database info
curl http://localhost:8000/test/db-info

# Execute sample query
curl http://localhost:8000/test/db-sample-query

# View Swagger UI
open http://localhost:8000/docs
```

### Neo4j Setup

#### Step 1: Configure Environment

```bash
# Copy the Neo4j example
cp .env.neo4j.example .env
```

The `.env` file will contain:
```bash
DB_TYPE=neo4j
NEO4J_URL=bolt://neo4j:7687
DB_USER=neo4j
DB_PASSWORD=password
PORT=8000
DEBUG=true
REDIS_URL=redis://redis:6379
```

#### Step 2: Start Services

```bash
# Start all services (app, neo4j, redis)
docker-compose -f docker-compose.neo4j.yml up --build

# Or run in background
docker-compose -f docker-compose.neo4j.yml up -d --build
```

#### Step 3: Verify Services

**Check logs:**
```bash
docker-compose -f docker-compose.neo4j.yml logs -f app
```

**Access Neo4j Browser:**
```bash
# Open in browser
open http://localhost:7474

# Login credentials:
# Username: neo4j
# Password: password
```

**Run Cypher queries:**
```cypher
// Test connection
RETURN "Hello Neo4j" as message;

// Create a test node
CREATE (n:TestNode {name: "Test"}) RETURN n;

// List all nodes
MATCH (n) RETURN n LIMIT 10;
```

#### Step 4: Test API

```bash
# Test database connection
curl http://localhost:8000/test/db-test

# Get database info
curl http://localhost:8000/test/db-info

# Execute sample query
curl http://localhost:8000/test/db-sample-query

# View Swagger UI
open http://localhost:8000/docs
```

## Docker Compose Files

### PostgreSQL (`docker-compose.postgres.yml`)

**Services:**
- **app**: FastAPI application
- **postgres**: PostgreSQL 16 (Alpine)
- **redis**: Redis 7 (Alpine)

**Features:**
- Health checks for all services
- Persistent data volumes
- Live code reloading
- Automatic dependency management

### Neo4j (`docker-compose.neo4j.yml`)

**Services:**
- **app**: FastAPI application
- **neo4j**: Neo4j 5 Community Edition
- **redis**: Redis 7 (Alpine)

**Features:**
- APOC plugin included
- Neo4j Browser on port 7474
- Bolt protocol on port 7687
- Health checks for all services
- Persistent data volumes

## Common Commands

### Start Services

```bash
# PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# Neo4j
docker-compose -f docker-compose.neo4j.yml up -d
```

### Stop Services

```bash
# PostgreSQL
docker-compose -f docker-compose.postgres.yml down

# Neo4j
docker-compose -f docker-compose.neo4j.yml down
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.postgres.yml logs -f

# Specific service
docker-compose -f docker-compose.postgres.yml logs -f app
docker-compose -f docker-compose.postgres.yml logs -f postgres
```

### Rebuild

```bash
# Rebuild app container
docker-compose -f docker-compose.postgres.yml up --build app

# Rebuild everything
docker-compose -f docker-compose.postgres.yml up --build
```

### Clean Up

```bash
# Stop and remove containers
docker-compose -f docker-compose.postgres.yml down

# Remove volumes (deletes data!)
docker-compose -f docker-compose.postgres.yml down -v

# Remove everything including images
docker-compose -f docker-compose.postgres.yml down -v --rmi all
```

## Accessing Services

### API Endpoints

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Database Access

**PostgreSQL:**
- **Host**: localhost
- **Port**: 5432
- **Database**: apidb
- **User**: postgres
- **Password**: postgres

**Neo4j:**
- **Browser**: http://localhost:7474
- **Bolt**: bolt://localhost:7687
- **User**: neo4j
- **Password**: password

### Redis

- **Host**: localhost
- **Port**: 6379

## Switching Between Databases

### From PostgreSQL to Neo4j

```bash
# 1. Stop PostgreSQL services
docker-compose -f docker-compose.postgres.yml down

# 2. Copy Neo4j environment
cp .env.neo4j.example .env

# 3. Start Neo4j services
docker-compose -f docker-compose.neo4j.yml up -d
```

### From Neo4j to PostgreSQL

```bash
# 1. Stop Neo4j services
docker-compose -f docker-compose.neo4j.yml down

# 2. Copy PostgreSQL environment
cp .env.postgres.example .env

# 3. Start PostgreSQL services
docker-compose -f docker-compose.postgres.yml up -d
```

## Testing the Setup

### Test Script

Create a test script `test_api.sh`:

```bash
#!/bin/bash

echo "Testing API..."

# Test health
echo -e "\n1. Health Check:"
curl -s http://localhost:8000/health | jq

# Test database connection
echo -e "\n2. Database Connection:"
curl -s http://localhost:8000/test/db-test | jq

# Test database info
echo -e "\n3. Database Info:"
curl -s http://localhost:8000/test/db-info | jq

# Test sample query
echo -e "\n4. Sample Query:"
curl -s http://localhost:8000/test/db-sample-query | jq

# Test file endpoints
echo -e "\n5. File Count:"
curl -s http://localhost:8000/files/file-count | jq

echo -e "\nAll tests completed!"
```

Run it:
```bash
chmod +x test_api.sh
./test_api.sh
```

### Manual Testing

**Test Database Connection:**
```bash
curl http://localhost:8000/test/db-test
```

Expected response:
```json
{
  "status": "success",
  "message": "Database connection successful",
  "database_type": "postgresql"  // or "neo4j"
}
```

**Test Database Info:**
```bash
curl http://localhost:8000/test/db-info
```

**Test Sample Query:**
```bash
curl http://localhost:8000/test/db-sample-query
```

## Troubleshooting

### App Can't Connect to Database

**Check database is running:**
```bash
docker-compose -f docker-compose.postgres.yml ps
```

**Check database logs:**
```bash
docker-compose -f docker-compose.postgres.yml logs postgres
```

**Verify environment variables:**
```bash
docker-compose -f docker-compose.postgres.yml exec app env | grep DB
```

### Port Already in Use

**Find process using port:**
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

**Change port in `.env`:**
```bash
PORT=8001
```

### Database Connection Refused

**Wait for health check:**
```bash
# Services have health checks - wait for them to be healthy
docker-compose -f docker-compose.postgres.yml ps
```

**Check network:**
```bash
docker network ls
docker network inspect python-api-template_default
```

### Volume Permission Issues

**Reset volumes:**
```bash
docker-compose -f docker-compose.postgres.yml down -v
docker-compose -f docker-compose.postgres.yml up -d
```

## Production Considerations

### Security

**Change default passwords:**
```bash
# In .env
DB_PASSWORD=your_secure_password_here
```

**Use secrets management:**
- Docker secrets
- Environment variable injection
- Vault or similar

### Performance

**Adjust connection pools:**
```python
# In sql_handler.py
async_engine = create_async_engine(
    database_url,
    pool_size=20,      # Increase for production
    max_overflow=40,   # Increase for production
)
```

**Enable query caching:**
- Use Redis for caching
- Implement query result caching

### Monitoring

**Add health checks:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Add logging:**
- Centralized logging (ELK stack)
- Application metrics (Prometheus)

## Summary

### PostgreSQL Setup
```bash
cp .env.postgres.example .env
docker-compose -f docker-compose.postgres.yml up -d
curl http://localhost:8000/test/db-test
```

### Neo4j Setup
```bash
cp .env.neo4j.example .env
docker-compose -f docker-compose.neo4j.yml up -d
curl http://localhost:8000/test/db-test
```

### Access Points
- **API**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Neo4j Browser**: http://localhost:7474
- **Redis**: localhost:6379

The setup is now ready for testing! 🚀
