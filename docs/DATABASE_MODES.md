# Database Modes: Local vs External

This guide explains how to configure the API to use either local Docker databases or external databases.

## Overview

The API supports two database modes:

1. **Local Mode** (`DB_MODE=local`) - Starts database containers in Docker
2. **External Mode** (`DB_MODE=external`) - Connects to existing external databases

## Configuration

### Environment Variable: `DB_MODE`

Add this to your `.env` file:

```bash
# Database Mode: local or external
DB_MODE=local    # or external
```

## Local Mode (Docker Databases)

### When to Use
- Development and testing
- Quick setup without external dependencies
- Learning and experimentation
- CI/CD pipelines

### How It Works
- Starts database containers automatically
- Data stored in `.docker/` directory
- Easy to reset and clean up
- No external database required

### Configuration Examples

#### Local PostgreSQL

```bash
# .env or copy from .env.postgres.example
DB_TYPE=postgresql
DB_MODE=local

# Docker service names (not localhost!)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/apidb
DB_NAME=apidb
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
```

**Docker Compose:** `docker-compose.postgres.yml`
- Starts PostgreSQL 16 container
- Data: `.docker/postgres-data/`
- Access: localhost:5432

#### Local Neo4j

```bash
# .env or copy from .env.neo4j.example
DB_TYPE=neo4j
DB_MODE=local

# Docker service names (not localhost!)
NEO4J_URL=bolt://neo4j:7687
DB_USER=neo4j
DB_PASSWORD=password
```

**Docker Compose:** `docker-compose.neo4j.yml`
- Starts Neo4j 5 container
- Data: `.docker/neo4j-data/`
- Logs: `.docker/neo4j-logs/`
- Browser: http://localhost:7474
- Bolt: localhost:7687

### Starting Local Mode

**Automatic (using quick-start.sh):**
```bash
./quick-start.sh
# Automatically detects DB_MODE and starts correct containers
```

**Manual:**
```bash
# PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# Neo4j
docker-compose -f docker-compose.neo4j.yml up -d
```

**Windows (testing scripts):**
```bash
cd testing
start-postgres.bat  # or start-neo4j.bat
```

## External Mode (Existing Databases)

### When to Use
- Production deployments
- Connecting to managed database services (AWS RDS, Azure Database, etc.)
- Using existing company databases
- Shared development databases

### How It Works
- Connects to external database servers
- No database containers started
- Only API container runs
- Data managed externally

### Configuration Examples

#### External PostgreSQL

```bash
# .env or copy from .env.postgres-external.example
DB_TYPE=postgresql
DB_MODE=external

# External server (use actual hostname/IP)
DATABASE_URL=postgresql://myuser:mypassword@db.example.com:5432/production_db
DB_NAME=production_db
DB_USER=myuser
DB_PASSWORD=mypassword
DB_PORT=5432
```

**Docker Compose:** `docker-compose.yml`
- Only starts API + Redis containers
- No database containers
- Connects to external server

#### External Neo4j

```bash
# .env or copy from .env.neo4j-external.example
DB_TYPE=neo4j
DB_MODE=external

# External server (use actual hostname/IP)
NEO4J_URL=bolt://neo4j.example.com:7687
DB_USER=neo4j
DB_PASSWORD=production_password
```

**Docker Compose:** `docker-compose.yml`
- Only starts API + Redis containers
- No database containers
- Connects to external Neo4j server

### Starting External Mode

**Automatic (using quick-start):**
```bash
# Linux/Mac
./quick-start.sh

# Windows PowerShell
.\quick-start.ps1

# Automatically detects DB_MODE=external and uses docker-compose.yml
```

**Manual:**
```bash
docker-compose -f docker-compose.yml up -d
```

## Comparison

| Feature | Local Mode | External Mode |
|---------|-----------|---------------|
| **Setup** | Automatic | Manual (database must exist) |
| **Data Location** | `.docker/` folder | External server |
| **Containers** | API + Database + Redis | API only |
| **Network** | Docker internal | External network |
| **Use Case** | Development, Testing | Production, Shared |
| **Data Persistence** | Local directory | External server |
| **Cleanup** | Delete `.docker/` folder | Managed externally |

## Quick Start Examples

### Example 1: Local PostgreSQL Development

```bash
# 1. Copy example config
cp .env.postgres.example .env

# 2. Start (automatic detection)
./quick-start.sh

# 3. Access
# API: http://localhost:8000/docs
# PostgreSQL: localhost:5432
```

### Example 2: External Production Database

```bash
# 1. Copy external example
cp .env.postgres-external.example .env

# 2. Edit with your database details
nano .env
# Update: DATABASE_URL, DB_USER, DB_PASSWORD

# 3. Start (automatic detection)
./quick-start.sh

# 4. Access
# API: http://localhost:8000/docs
# Database: Your external server
```

### Example 3: Local Neo4j for Testing

```bash
# 1. Copy example config
cp .env.neo4j.example .env

# 2. Start
cd testing
start-neo4j.bat  # Windows
# or
./quick-start.sh  # Linux/Mac

# 3. Access
# API: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
```

## Switching Between Modes

### From Local to External

```bash
# 1. Stop local containers
docker-compose -f docker-compose.postgres.yml down

# 2. Update .env
DB_MODE=external
DATABASE_URL=postgresql://user:pass@external-server:5432/db

# 3. Restart
./quick-start.sh
```

### From External to Local

```bash
# 1. Stop API
docker-compose -f docker-compose.external.yml down

# 2. Update .env
DB_MODE=local
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/apidb

# 3. Restart
./quick-start.sh
```

## Available .env Templates

```
.env.template                    # General template with both modes
.env.postgres.example            # Local PostgreSQL
.env.postgres-external.example   # External PostgreSQL
.env.neo4j.example              # Local Neo4j
.env.neo4j-external.example     # External Neo4j
```

## Docker Compose Files

```
docker-compose.yml               # Basic (app + redis) - for external databases
docker-compose.postgres.yml      # Local PostgreSQL + Redis + App
docker-compose.neo4j.yml         # Local Neo4j + Redis + App
```

## Automatic Detection

The `quick-start.sh` (Linux/Mac) or `quick-start.ps1` (Windows) script automatically detects your configuration:

```bash
# Reads from .env:
DB_TYPE=postgresql  # or neo4j, mysql, sqlite
DB_MODE=local       # or external

# Selects compose file:
# - DB_MODE=external → docker-compose.yml
# - DB_TYPE=neo4j + DB_MODE=local → docker-compose.neo4j.yml
# - DB_TYPE=postgresql + DB_MODE=local → docker-compose.postgres.yml
```

## Troubleshooting

### Local Mode Issues

**Database won't start:**
```bash
# Check logs
docker-compose -f docker-compose.postgres.yml logs postgres

# Reset data
docker-compose -f docker-compose.postgres.yml down
rm -rf .docker/postgres-data
docker-compose -f docker-compose.postgres.yml up -d
```

**Port already in use:**
```bash
# Change port in .env
DB_PORT=5433  # Instead of 5432
```

### External Mode Issues

**Can't connect to database:**
- Verify hostname/IP is correct
- Check firewall rules
- Ensure database allows remote connections
- Verify credentials

**Network issues:**
```bash
# Test connection from host
psql -h db.example.com -U myuser -d mydb  # PostgreSQL
cypher-shell -a bolt://neo4j.example.com:7687 -u neo4j  # Neo4j
```

## Best Practices

### Development
- Use **local mode** for development
- Keep `.docker/` in `.gitignore`
- Use example configs as templates

### Production
- Use **external mode** for production
- Use managed database services
- Store credentials securely (environment variables, secrets manager)
- Never commit `.env` with production credentials

### Testing
- Use **local mode** for CI/CD
- Reset data between test runs
- Use separate test databases

## Summary

- **Local Mode**: Quick setup, Docker manages everything, perfect for development
- **External Mode**: Production-ready, connects to existing databases, managed externally
- **Automatic**: `quick-start.sh` detects mode and starts correct containers
- **Flexible**: Easy to switch between modes by changing `.env`

Choose the mode that fits your use case and let the system handle the rest! 🚀
