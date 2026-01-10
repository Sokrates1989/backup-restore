# Test Databases for Backup/Restore Testing

This document describes how to use the test database setup for testing backup and restore operations across all supported database types.

## Supported Database Types

| Database | Test Port | Admin UI | Admin UI Port |
|----------|-----------|----------|---------------|
| PostgreSQL | 5434 | pgAdmin | 5050 |
| MySQL | 3306 | phpMyAdmin | 8080 |
| Neo4j | 7688 (bolt), 7475 (http) | Neo4j Browser | 7475 |
| SQLite | N/A (file-based) | SQLite Web | 8083 |

Additionally, **Adminer** is available at port **8082** as a universal database admin tool that works with PostgreSQL, MySQL, and SQLite.

## Quick Start

### Option 1: Using the Menu

1. Run `./quick-start.sh` (Mac/Linux) or `.\quick-start.ps1` (Windows)
2. Select **"Start with test databases"** from the Testing menu section

### Option 2: Manual Docker Compose

```bash
# Start everything including test databases
docker compose --env-file .env \
  -f local-deployment/docker-compose.postgres.yml \
  -f local-deployment/docker-compose.runner.yml \
  -f local-deployment/docker-compose.test-databases.yml \
  up --build
```

## Admin UI Access

### pgAdmin (PostgreSQL)
- **URL:** http://localhost:5050
- **Email:** admin@local.dev
- **Password:** admin

**Auto-connection:** The test PostgreSQL connection should be automatically created as "Test PostgreSQL" in the server list.

**Manual connection (if needed):**
1. Click "Add New Server"
2. **General tab:**
   - Name: Test PostgreSQL
3. **Connection tab:**
   - **Host:** test-postgres
   - **Port:** 5432
   - **Maintenance database:** postgres
   - **Username:** testuser
   - **Password:** testpass
4. Click **Save**

To connect to the test PostgreSQL database:
- In the object browser, expand "Test PostgreSQL"
- Right-click on "testdb" and select "Query Tool"

### phpMyAdmin (MySQL)
- **URL:** http://localhost:8080
- **Server:** test-mysql
- **Username:** root
- **Password:** rootpass

### Neo4j Browser
- **URL:** http://localhost:7475
- **Username:** neo4j
- **Password:** testpass
- **Bolt URL:** bolt://localhost:7688

### SQLite Web
- **URL:** http://localhost:8083
- **Database file:** /data/test.db (inside container)

### Adminer (Universal)
- **URL:** http://localhost:8082
- Supports PostgreSQL, MySQL, SQLite

## Connecting from Backup Manager

When adding databases in the Backup Manager UI (http://localhost:8000/), use these connection details:

### Test PostgreSQL
- **Name:** Test PostgreSQL
- **Type:** PostgreSQL
- **Host:** test-postgres
- **Port:** 5432
- **Database:** testdb
- **Username:** testuser
- **Password:** testpass

### Test MySQL
- **Name:** Test MySQL
- **Type:** MySQL
- **Host:** test-mysql
- **Port:** 3306
- **Database:** testdb
- **Username:** testuser
- **Password:** testpass

### Test Neo4j
- **Name:** Test Neo4j
- **Type:** Neo4j
- **Host:** test-neo4j
- **Port:** 7687
- **Username:** neo4j
- **Password:** testpass

### Test SQLite
- **Name:** Test SQLite
- **Type:** SQLite
- **Path:** /data/test.db

## Environment Variables

Copy `.env.test-databases` to your `.env` file or set these variables:

```bash
# PostgreSQL
TEST_POSTGRES_DB=testdb
TEST_POSTGRES_USER=testuser
TEST_POSTGRES_PASSWORD=testpass

# MySQL
TEST_MYSQL_DB=testdb
TEST_MYSQL_USER=testuser
TEST_MYSQL_PASSWORD=testpass
TEST_MYSQL_ROOT_PASSWORD=rootpass

# Neo4j
TEST_NEO4J_USER=neo4j
TEST_NEO4J_PASSWORD=testpass

# pgAdmin
PGADMIN_EMAIL=admin@local.dev
PGADMIN_PASSWORD=admin
```

## Data Persistence

All test database data is stored in the `.docker/` directory:

- `.docker/test-postgres-data/` - PostgreSQL data
- `.docker/test-mysql-data/` - MySQL data
- `.docker/test-neo4j-data/` - Neo4j data
- `.docker/test-neo4j-logs/` - Neo4j logs
- `.docker/test-sqlite-data/` - SQLite database files
- `.docker/pgadmin-data/` - pgAdmin configuration

To reset all test databases:

```bash
# Stop all containers first
docker compose -f local-deployment/docker-compose.postgres.yml \
  -f local-deployment/docker-compose.test-databases.yml down

# Remove test database data
rm -rf .docker/test-*
rm -rf .docker/pgadmin-data
```

## App's Own Database Admin UI

The app's own PostgreSQL database also has a pgAdmin instance available:

- **URL:** http://localhost:5051 (only when started with `--profile admin`)
- **Email:** admin@local.dev
- **Password:** admin

To start with admin profile:
```bash
docker compose --env-file .env \
  -f local-deployment/docker-compose.postgres.yml \
  -f local-deployment/docker-compose.runner.yml \
  --profile admin up --build
```

Or use the menu option **"Start with admin UIs only"**.
