# Build and Test Scripts

This directory contains scripts for testing and building the Docker image.

## Scripts

### `rebuild-and-push.sh` / `rebuild-and-push.ps1`

Rebuilds the Docker image and pushes it to Docker Hub.

**Usage (Linux/Mac):**
```bash
./rebuild-and-push.sh
```

**Usage (Windows):**
```powershell
.\rebuild-and-push.ps1
```

**What it does:**
1. Reads the version from `pyproject.toml`
2. Builds the Docker image with that version tag
3. Tags the image as `latest`
4. Pushes both tags to Docker Hub

**Requirements:**
- Docker installed and running
- Logged in to Docker Hub (`docker login`)
- Appropriate permissions to push to the repository

### `test-migration-fix.sh`

Tests that the migration system can construct `DATABASE_URL` from individual components (important for Docker Swarm deployments).

**Usage:**
```bash
./test-migration-fix.sh
```

**What it tests:**
- Alembic can load configuration without `DATABASE_URL` set
- Database URL is properly constructed from `DB_HOST`, `DB_USER`, `DB_PASSWORD`, etc.
- Migration system works with component-based configuration

## After Building

After building and pushing a new image:

1. **Update your Docker Swarm deployment:**
   ```bash
   docker service update --image sokrates1989/python-api-template:VERSION your-stack_api
   ```

2. **Verify migrations ran successfully:**
   ```bash
   docker service logs your-stack_api --tail 50
   ```

   Look for detailed per-migration status:
   ```
   ⏩ Applying: 001 - Initial examples table
   ✅ SUCCESS: 001 - Initial examples table
   ⏩ Applying: 002 - Add categories table
   ✅ SUCCESS: 002 - Add categories table
   ```

3. **Test the API:**
   ```bash
   curl https://your-api-domain.com/examples/
   ```

## See Also

- [AUTOMATIC_MIGRATIONS.md](../docs/AUTOMATIC_MIGRATIONS.md) - How automatic migrations work
- [PRODUCTION-IMAGE-BUILD.md](../docs/PRODUCTION-IMAGE-BUILD.md) - Production image building guide
- [DOCKER_SETUP.md](../docs/DOCKER_SETUP.md) - Docker setup and configuration
