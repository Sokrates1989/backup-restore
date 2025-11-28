# Quick Start Guide

Get started with the **Database Backup & Restore Service** in minutes.

## Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

## Setup Steps

### 1. Clone and Navigate

```bash
git clone <your-repo-url>
cd backup-restore
```

### 2. Configure Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env and set your database type
# Options: neo4j, postgresql, mysql, sqlite
```

### 3. Choose Your Database

#### Option A: Neo4j (Default)

```bash
# .env
DB_TYPE=neo4j
NEO4J_URL=bolt://localhost:7687
DB_USER=neo4j
DB_PASSWORD=password
```

Start Neo4j:
```bash
docker run -d -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

#### Option B: PostgreSQL

```bash
# .env
DB_TYPE=postgresql
DATABASE_URL=postgresql://postgres:password@localhost:5432/mydb
```

Start PostgreSQL:
```bash
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=mydb \
  postgres:latest
```

#### Option C: SQLite (No setup needed)

```bash
# .env
DB_TYPE=sqlite
DATABASE_URL=sqlite:///./database.db
```

### 4. Start the Application

```bash
# Using Docker Compose (recommended)
docker-compose up

# Or run locally
uvicorn app.main:app --reload
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Database test
curl http://localhost:8000/test/db-test

# API documentation
open http://localhost:8000/docs
```

## Project Structure

```
backup-restore/
├── app/
│   ├── api/                    # API layer
│   │   ├── routes/            # Backup/restore endpoints
│   │   │   ├── sql_backup.py  # SQL backup & restore
│   │   │   └── neo4j_backup.py# Neo4j backup & restore
│   │   └── settings.py        # Configuration
│   ├── backend/               # Backup services
│   │   └── services/
│   │       ├── sql/backup_service.py
│   │       └── neo4j/backup_service.py
│   └── main.py                # Application entry point
├── docs/                      # Documentation
│   ├── DATABASE_BACKUP.md    # Backup & restore guide
│   └── QUICK_START.md        # This file
├── .env.template             # Environment template
└── docker-compose.yml        # Docker configuration
```

## Next Steps

1. **Add your models**: Edit `app/models/` for SQL databases
2. **Create routes**: Add new routes in `app/api/routes/`
3. **Read the docs**: Check `docs/DATABASE.md` for detailed database usage
4. **Customize**: Modify the template to fit your needs

## Common Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up --build
```

## Troubleshooting

### Database connection failed

- Check if database server is running
- Verify connection settings in `.env`
- Check firewall/network settings

### Port already in use

- Change `PORT` in `.env`
- Or stop the conflicting service

### Module not found

- Run `poetry install` or `pdm install`
- Rebuild Docker image: `docker-compose up --build`

## Getting Help

- Check `docs/DATABASE.md` for database-specific help
- Review API docs at `http://localhost:8000/docs`
- Check logs: `docker-compose logs`
