# Dependency Management - How It Works

## Overview

This project uses a **build-time dependency installation** approach where packages are installed directly into the Docker image, not persisted in volumes.

## Architecture

```
┌─────────────────────────────────┐
│  Dependency Management          │
│  Container (dev)                │
│                                 │
│  - pdm add/update/remove        │
│  - Updates pdm.lock file        │
│  - Changes persist to host      │
└────────────┬────────────────────┘
             │
             │ pdm.lock updated on host
             ▼
┌─────────────────────────────────┐
│  Host File System               │
│                                 │
│  - pyproject.toml               │
│  - pdm.lock ◄─── UPDATED        │
└────────────┬────────────────────┘
             │
             │ Docker build reads pdm.lock
             ▼
┌─────────────────────────────────┐
│  Backend Container (app)        │
│                                 │
│  - Dockerfile copies pdm.lock   │
│  - RUN pdm install --prod       │
│  - .venv built INTO image       │
│  - No volume persistence        │
└─────────────────────────────────┘
```

## Why No Volume for .venv?

### ❌ Previous Approach (Volume-Based)
```yaml
volumes:
  - pdm-venv:/app/.venv  # Persisted across rebuilds
```

**Problems:**
- Stale dependencies after updating `pdm.lock`
- Required manual volume cleanup
- Hard to debug version mismatches
- Not following Docker best practices

### ✅ Current Approach (Image-Based)
```dockerfile
RUN pip install pdm && pdm install --prod
# .venv is part of the image layers
```

**Benefits:**
- Dependencies always match `pdm.lock` from build
- Rebuild = fresh dependencies
- Predictable, reproducible builds
- Standard Docker pattern

## Workflow

### Updating Dependencies

```powershell
# Option 1: Use quick-start (recommended)
.\quick-start.ps1
# Choose option 3: Both - Dependency Management and then start backend

# Option 2: Manual
.\manage-python-project-dependencies.ps1
# Inside container: pdm update, pdm add package, etc.
# Exit when done

# Rebuild backend (removes old volumes automatically)
docker compose -f docker-compose.postgres.yml down -v
docker compose -f docker-compose.postgres.yml up --build
```

### How Docker Detects Changes

Docker automatically invalidates cache when `pdm.lock` changes:

1. **Layer caching**: `COPY pyproject.toml pdm.lock ./`
   - If file content changes → cache miss
   - Next layer (`RUN pdm install`) re-executes

2. **No manual cache busting needed**
   - Docker's built-in mechanism works correctly
   - Just use `--build` flag

## Verifying Installation

Use the `/packages/list` endpoint:

```powershell
$headers = @{ "X-API-Key" = "dev-key-12345" }
$response = Invoke-RestMethod -Uri "http://localhost:8081/packages/list" -Headers $headers
$response.packages | Format-Table
```

Compare with PDM in dependency management container:

```bash
docker compose -f docker-compose-python-dependency-management.yml run --rm dev pdm list
```

Versions should match exactly.

## Common Issues

### Issue: Backend has old package versions after update

**Cause:** Old image or volumes still present

**Solution:**
```powershell
# Remove everything and rebuild
docker compose -f docker-compose.postgres.yml down -v
docker compose -f docker-compose.postgres.yml up --build
```

### Issue: `--build` doesn't seem to rebuild

**Cause:** Docker sees no changes in `pdm.lock`

**Solution:**
1. Verify `pdm.lock` was actually updated on host
2. Check file timestamp: `Get-Item pdm.lock | Select-Object LastWriteTime`
3. Force rebuild: `docker compose build --no-cache`

### Issue: Slow builds after dependency changes

**Cause:** `--no-cache` rebuilds everything

**Solution:**
- Use `--build` (not `--no-cache`) for normal rebuilds
- Docker only rebuilds layers after `pdm.lock` change
- Base image layers remain cached

## Best Practices

### 1. Always Remove Volumes After Dependency Updates

```powershell
docker compose down -v  # -v removes volumes
docker compose up --build
```

### 2. Commit pdm.lock

```bash
git add pdm.lock pyproject.toml
git commit -m "Update dependencies"
```

### 3. Document Dependency Changes

```bash
git commit -m "Update fastapi to 0.121.0

- Adds new response model features
- Fixes security issue CVE-2024-XXXX
- Required for /packages endpoint"
```

### 4. Test After Updates

1. Check `/packages/list` endpoint
2. Run your application tests
3. Verify critical functionality

## Technical Details

### Why This Works

1. **Docker Layer Caching**
   - Each `COPY` and `RUN` creates a layer
   - Layers are cached by content hash
   - When `pdm.lock` changes, its layer hash changes
   - All subsequent layers are invalidated

2. **No Volume = No Persistence**
   - `.venv` exists only in image
   - Each container gets fresh copy from image
   - Rebuild = new `.venv` with new packages

3. **Code Mounting Still Works**
   - We mount `./app` directories for live reload
   - But NOT `.venv` or `pdm.lock`
   - Code changes don't require rebuild
   - Dependency changes do require rebuild

### Performance Considerations

**Build Time:**
- First build: ~30-60 seconds (downloads all packages)
- Rebuild after code change: <1 second (cached)
- Rebuild after dependency change: ~10-20 seconds (only reinstalls changed packages)

**Runtime:**
- No performance difference vs volume approach
- `.venv` is in image, loaded into container memory
- Fast package imports

**Disk Space:**
- Each image version contains full `.venv`
- Old images can be pruned: `docker image prune`
- Typical image size: ~500MB-1GB

## Migration from Volume-Based Approach

If you were using the old volume-based approach:

```powershell
# 1. Stop and remove everything
docker compose down -v

# 2. Remove old volume manually (if it persists)
docker volume rm python-api-template_pdm-venv

# 3. Rebuild with new approach
docker compose up --build
```

The new approach is simpler and more reliable!
