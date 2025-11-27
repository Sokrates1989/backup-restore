# Local Deployment Directory

This directory contains Docker Compose files for **local development**.

## Files

- **`docker-compose.yml`** - Base configuration (app + Redis)
- **`docker-compose.postgres.yml`** - PostgreSQL database extension
- **`docker-compose.neo4j.yml`** - Neo4j database extension
- **`docker-compose-python-dependency-management.yml`** - Python dependency management

## Usage

### Via Quick-Start Scripts (Recommended)

The easiest way to start local development:

```bash
# Linux/Mac
./quick-start.sh

# Windows
.\quick-start.ps1
```

These scripts automatically select the correct compose files based on your `.env` configuration.

### Manual Docker Compose

If you prefer to use Docker Compose directly:

#### PostgreSQL (Local)
```bash
docker compose -f local-deployment/docker-compose.postgres.yml -f local-deployment/docker-compose.yml --env-file .env up
```

#### Neo4j (Local)
```bash
docker compose -f local-deployment/docker-compose.neo4j.yml -f local-deployment/docker-compose.yml --env-file .env up
```

#### External Database
```bash
docker compose -f local-deployment/docker-compose.yml --env-file .env up
```

## Volume Mounts

The compose files mount several directories for live development:

- **`../app`** - Application code (live reload)
- **`../alembic`** - Database migrations
- **`../backups`** - Database backups (persisted to host)
- **`../app/mounted_data`** - Mounted data directory

## Ports

Default ports (configurable via `.env`):

- **API**: 8081 (or value from `PORT` in `.env`)
- **PostgreSQL**: 5432
- **Neo4j Bolt**: 7687
- **Neo4j HTTP**: 7474
- **Redis**: 6379

## Dependencies

The compose files depend on:

- **`.env`** file in project root (created by setup)
- **`Dockerfile`** in project root
- **`interactive-scripts/Dockerfile`** for dependency management

## Development Workflow

1. **Start services**: `./quick-start.sh` (or `.ps1`)
2. **Make code changes**: Files are live-reloaded
3. **View logs**: `docker compose logs -f app`
4. **Stop services**: `docker compose down`
5. **Clean restart**: `docker compose down -v && docker compose up --build`

## Troubleshooting

### Port Already in Use
Change the `PORT` value in your `.env` file.

### Database Connection Issues
- Check that database service is healthy: `docker compose ps`
- Verify credentials in `.env` match the compose file
- For external databases, ensure `DB_HOST` points to correct server

### Volume Permission Issues
On Linux, you may need to adjust ownership:
```bash
sudo chown -R $USER:$USER backups/
```
