# 🚀 FastAPI Python API Template

A production-ready FastAPI template with multi-database support, Redis cache, Docker-based development, and modern Python dependency management.

## 📚 Table of Contents

1. [📖 Overview](#-overview)
2. [📋 Prerequisites](#-prerequisites)
3. [🚀 Quick Start](#-quick-start)
4. [🔧 Dependency Management](#-dependency-management)
5. [📁 Project Structure](#-project-structure)
6. [⚙️ Configuration](#-configuration)
7. [🧪 API Tests](#-api-tests)
8. [🐳 Docker Commands](#-docker-commands)
9. [🔄 Development Workflow](#-development-workflow)
10. [🏗️ Docker Image Build & Deploy](#-docker-image-build--deploy)
11. [✨ Benefits](#-benefits)
12. [📚 Additional Information](#-additional-information)
13. [⚠️ Deprecated: Alternative Installation Methods](#-deprecated-alternative-installation-methods)

## 📖 Overview

This template is a clean and extensible FastAPI project with:

- ✅ FastAPI framework with automatic documentation
- ✅ **Multi-database support**: Neo4j, PostgreSQL, MySQL, SQLite
- ✅ Redis integration as caching layer
- ✅ Docker & Docker Compose for reproducible environments
- ✅ Environment variable-based configuration
- ✅ Modular architecture with clean separation of concerns
- ✅ Modern Python dependency management with PDM

## 📋 Prerequisites

**Only requirement:** Docker must be installed and running.

- [Download Docker Desktop](https://www.docker.com/get-started)
- Start Docker Desktop

> **Important:** No local Python, Poetry, or PDM installation required! Everything runs in Docker containers.

## 🚀 Quick Start

### Guided Setup (Recommended)

On first run, the quick-start scripts will launch an **interactive setup wizard** that helps you configure:
- Docker image name and version
- Python version
- Database type (PostgreSQL or Neo4j)
- Database mode (local Docker or external)
- API settings (port, debug mode)

**Windows PowerShell:**
```powershell
.\quick-start.ps1
```

**Linux/Mac:**
```bash
./quick-start.sh
```

The script will:
- ✅ Check Docker installation
- ✅ Create `.env` from template
- ✅ Detect database type (PostgreSQL/Neo4j) and mode (local/external)
- ✅ Start the correct containers automatically

### Option 1: Quick Start with PostgreSQL (Manual)

**Windows:**
```bash
# Automatically sets up and starts PostgreSQL + Redis + API
cd testing
start-postgres.bat
```

**Linux/Mac:**
```bash
# Copy environment configuration
cp .env.postgres.example .env

# Start services
docker-compose -f docker-compose.postgres.yml up --build
```

**Access:**
- **API**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (user: postgres, password: postgres)

### Option 2: Quick Start with Neo4j (Manual)

**Windows:**
```bash
# Automatically sets up and starts Neo4j + Redis + API
cd testing
start-neo4j.bat
```

**Linux/Mac:**
```bash
# Copy environment configuration
cp .env.neo4j.example .env

# Start services
docker-compose -f docker-compose.neo4j.yml up --build
```

**Access:**
- **API**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, password: password)

### Test the API

**Windows:**
```bash
test-api.bat
```

**Linux/Mac:**
```bash
curl http://localhost:8000/test/db-test
curl http://localhost:8000/test/db-info
curl http://localhost:8000/test/db-sample-query
```

### Detailed Setup

For complete setup instructions, see **[docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md)**

## 🔧 Dependency Management

### Automatic Setup (on first quick-start.sh)
Initial dependency management is executed automatically:
```bash
./manage-python-project-dependencies.sh initial-run
```
- 🔄 Updates PDM lock files automatically
- 🚀 Prepares Docker builds
- 📦 Runs `pdm install` in container
- ⚡ Non-interactive, runs in background

### Interactive Dependency Management
For manual package management:
```bash
./manage-python-project-dependencies.sh
```

**In the interactive container:**
```bash
# Add packages
pdm add requests
pdm add pytest --dev

# Remove packages
pdm remove requests

# Install dependencies
pdm install

# Update lock file
pdm lock

# Exit container
exit
```

**Important PDM commands:**
- `pdm add <package>` - Add package
- `pdm remove <package>` - Remove package
- `pdm install` - Install all dependencies
- `pdm update` - Update all packages
- `pdm list` - Show installed packages
- `pdm lock` - Update lock file
- `exit` - Exit container

### Modes Overview
| Mode | Command | Usage |
|------|---------|-------|
| **Initial** | `./manage-python-project-dependencies.sh initial-run` | Automatic setup on first start |
| **Interactive** | `./manage-python-project-dependencies.sh` | Manual package management |

## 📁 Project Structure

```
python-api-template/
├── app/                          # Main application code
│   ├── api/                      # API layer
│   │   ├── routes/              # Route handlers
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── settings.py          # Configuration
│   ├── backend/                  # Backend layer
│   │   └── database/            # Database handlers
│   │       ├── base.py          # Abstract base class
│   │       ├── factory.py       # Database factory
│   │       ├── neo4j_handler.py # Neo4j implementation
│   │       ├── sql_handler.py   # SQL implementation
│   │       ├── init_db.py       # Initialization
│   │       └── queries.py       # Query helpers
│   ├── models/                   # Data models
│   │   └── example_sql_models.py
│   ├── mounted_data/             # Example data for volume mounts
│   └── main.py                   # FastAPI application entrypoint
├── docs/                         # Documentation
│   ├── DATABASE.md              # Database guide
│   ├── QUICK_START.md           # Quick start guide
│   └── README-DE.md             # German README
├── python-dependency-management/ # Dockerized dependency management tools
├── .env.template                # Environment variable template
├── docker-compose.yml           # Docker services configuration
├── Dockerfile                   # Docker build file
├── pyproject.toml              # Project metadata and dependencies
├── quick-start.sh              # Smart onboarding script
└── manage-python-project-dependencies.sh # Dependency management
```

## ⚙️ Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | API Port | `8000` |
| `REDIS_URL` | Redis connection | `redis://redis:6379` |
| `DB_TYPE` | Database type | `neo4j` |
| `NEO4J_URL` | Neo4j connection (if DB_TYPE=neo4j) | - |
| `DB_USER` | Database user (Neo4j) | - |
| `DB_PASSWORD` | Database password (Neo4j) | - |
| `DATABASE_URL` | SQL database URL (if DB_TYPE=postgresql/mysql/sqlite) | - |

### Example .env (Neo4j)
```env
PORT=8000
REDIS_URL=redis://redis:6379
DB_TYPE=neo4j
NEO4J_URL=bolt://localhost:7687
DB_USER=neo4j
DB_PASSWORD=password
```

### Example .env (PostgreSQL)
```env
PORT=8000
REDIS_URL=redis://redis:6379
DB_TYPE=postgresql
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

## 🧪 API Tests

**Available endpoints:**
- `GET /` - Visitor counter (Redis)
- `GET /cache/{key}` - Get cache value
- `POST /cache/{key}` - Set cache value
- `GET /health` - Health check
- `GET /version` - Show version
- `GET /test/db-test` - Test database connection
- `POST /examples/` - Create example (CRUD demo)
- `GET /examples/` - List examples (CRUD demo)
- `GET /examples/{id}` - Get example (CRUD demo)
- `PUT /examples/{id}` - Update example (CRUD demo)
- `DELETE /examples/{id}` - Delete example (CRUD demo)

## 🐳 Docker Commands

```bash
# Start backend
docker compose up --build

# Stop backend
docker compose down

# Show logs
docker compose logs -f

# Rebuild containers
docker compose up --build --force-recreate

# Dependency Management
./manage-python-project-dependencies.sh
```

## 🔄 Development Workflow

### First Setup (one-time)
1. **Clone project:** `git clone ...`
2. **Quick Start:** `./quick-start.sh` (runs everything automatically)
3. **Test API:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Daily Development
1. **Start backend:** `./quick-start.sh` (with selection menu)
2. **Change code:** Automatic reload in Docker
3. **Add packages:** `./manage-python-project-dependencies.sh` → `pdm add <package>`
4. **Test API:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Deployment
```bash
docker compose up --build
```

### Reset (if problems occur)
```bash
# Delete setup marker for complete restart
rm .setup-complete
./quick-start.sh
```

## 🏗️ Docker Image Build & Deploy

```bash
# Set image tag
export IMAGE_TAG=0.1.0

# Docker Registry Login
docker login registry.gitlab.com -u gitlab+deploy-token-XXXXXX -p YOUR_DEPLOY_TOKEN

# Build & Push (Linux/amd64 for Azure)
docker buildx build --platform linux/amd64 --build-arg IMAGE_TAG=$IMAGE_TAG \
  -t registry.gitlab.com/speedie3/fastapi-redis-api-test:$IMAGE_TAG --push .
```

## ✨ Benefits

- **🚀 Smart Onboarding:** Automatic setup on first run
- **🎯 Adaptive UX:** Different menus for first vs. repeated usage
- **🔒 Consistent Environment:** All developers use the same Docker environment
- **⚡ Fast Dependency Management:** PDM with uv backend, automatic lock updates
- **🛠️ No Local Tools:** Only Docker required
- **🔄 Automatic Reload:** Code changes are immediately applied
- **🔐 Secure Configuration:** 1Password integration for production settings
- **🧘 Stress-free Setup:** Everything runs automatically, first time may take longer

## 📚 Additional Information

### Database Support

This template supports multiple database backends:
- **Neo4j**: Graph database for connected data
- **PostgreSQL**: Powerful relational database
- **MySQL**: Popular relational database
- **SQLite**: Lightweight file-based database

See `docs/DATABASE.md` for detailed database configuration and usage.

### Documentation

- **Database Backup & Restore**: `docs/DATABASE_BACKUP.md` - Complete backup/restore via API ⭐ **NEW**
- **Migration Guide**: `docs/MIGRATION_GUIDE.md` - Real-world schema changes (add tables, columns, relationships) ⭐ **NEW**
- **Database Examples**: `docs/DATABASE_EXAMPLES.md` - SQL vs Neo4j CRUD examples ⭐ **NEW**
- **Database Migrations**: `docs/DATABASE_MIGRATIONS.md` - Production-ready schema management ⭐
- **CRUD Example**: `docs/CRUD_EXAMPLE.md` - Complete CRUD operations guide ⭐
- **Quick CRUD Reference**: `docs/QUICK_CRUD_REFERENCE.md` - Quick reference cheat sheet ⭐
- **Docker Setup**: `docs/DOCKER_SETUP.md` - Complete Docker setup guide ⭐
- **How to Add Endpoint**: `docs/HOW_TO_ADD_ENDPOINT.md` - Step-by-step guide ⭐
- **Database Credentials**: `docs/DATABASE_CREDENTIALS.md` - Security & credential management ⭐
- **Project Structure**: `docs/PROJECT_STRUCTURE.md` - Structure explanation
- **Quick Start**: `docs/QUICK_START.md` - Get started quickly
- **Database Guide**: `docs/DATABASE.md` - Database configuration and usage
- **Architecture**: `docs/ARCHITECTURE.md` - Architecture overview
- **German README**: `docs/README-DE.md` - Deutsche Dokumentation

### Deployment

- **Registry:** GitLab Container Registry
- **Deployment:** Azure Container Apps compatible
- **Setup Marker:** `.setup-complete` is automatically created/deleted

---

## ⚠️ Deprecated: Alternative Installation Methods

> **Note:** The following methods are deprecated and no longer recommended. Use the Docker workflow above instead.

<details>
<summary>🔽 Local Poetry Installation (Deprecated)</summary>

```bash
# Not recommended - only for legacy purposes
curl -sSL https://install.python-poetry.org | python3 -
poetry install
poetry run uvicorn main:app --reload
```

</details>

<details>
<summary>🔽 Local PDM Installation (Deprecated)</summary>

```bash
# Not recommended - only for legacy purposes
pipx install pdm
pdm install
pdm run uvicorn main:app --reload
```

</details>

<details>
<summary>🔽 Pip Installation (Deprecated)</summary>

```bash
# Not recommended - only for legacy purposes
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

</details>
