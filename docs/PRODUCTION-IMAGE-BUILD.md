# Production Image Build System

This document describes the production image build system for the API template.

## 📋 Overview

The production image build system allows you to create optimized Docker images for deployment to production servers. The system is designed to:

- Build production-optimized Docker images locally
- Manage image versioning automatically
- Support CI/CD pipelines (GitHub Actions, GitLab CI)
- Avoid platform-specific scripts by using Docker for the build process

## 🏗️ Architecture

### Directory Structure

```
python-api-template/
├── Dockerfile                            # Main Dockerfile (dev + production)
├── build-image/                          # Production build directory
│   ├── Dockerfile                        # Alpine + Docker CLI for build script
│   ├── build-image.sh                    # Build script (runs in Docker)
│   ├── docker-compose.build.yml          # Docker Compose for building
│   └── README.md                         # Build documentation
├── .ci.env.template                      # CI/CD configuration template
├── .github/workflows/
│   └── build-and-push.yml.example        # GitHub Actions workflow example
└── .gitlab-ci.yml.example                # GitLab CI pipeline example
```

### Related Repository

For production deployment with Docker Swarm, see:
- [swarm-python-api-template](https://github.com/Sokrates1989/swarm-python-api-template)

### Key Components

1. **Main Dockerfile** (`Dockerfile`)
   - Single Dockerfile for both development and production
   - Configurable via build arguments
   - Ensures consistency between environments
   - Production-ready by default

2. **Build Environment** (`build-image/Dockerfile`)
   - Alpine Linux + Docker CLI
   - Provides platform-independent build environment
   - Runs the build script in a container

3. **Build Script** (`build-image/build-image.sh`)
   - Runs inside Docker container (platform-independent)
   - Prompts for image version
   - Automatically updates `.env` file
   - Builds and optionally pushes images

4. **Docker Compose Build** (`build-image/docker-compose.build.yml`)
   - Orchestrates the build process
   - Mounts Docker socket for building
   - Ensures consistent build environment

## 🚀 Usage

### Local Build

#### Option 1: Using Quick Start Scripts (Recommended)

**Windows:**
```powershell
.\quick-start.ps1
# Select option 5: Build Production Docker Image
```

**Linux/macOS:**
```bash
./quick-start.sh
# Select option 5: Production Docker Image bauen
```

#### Option 2: Direct Docker Compose

```bash
docker compose -f build-image/docker-compose.build.yml up
```

### Configuration

1. **Edit `.env` file:**

```env
# Docker image name (required)
IMAGE_NAME=your-username/your-api-name

# Docker image version (will be prompted during build)
IMAGE_VERSION=1.0.0

# Python version
PYTHON_VERSION=3.13
```

2. **Build Process:**
   - Script loads configuration from `.env`
   - Prompts you to enter/confirm image version
   - Updates `IMAGE_VERSION` in `.env` automatically
   - Builds image with tags: `IMAGE_NAME:VERSION` and `IMAGE_NAME:latest`
   - Optionally pushes to Docker registry

### Testing Production Image Locally

```bash
# Test the built image directly
docker run -p 8000:8000 --env-file .env your-username/your-api-name:0.0.1

# Or use development docker-compose
docker compose -f local-deployment/docker-compose.yml up
```

### Testing with Docker Swarm

For production-like testing with Docker Swarm, use the [swarm-python-api-template](https://github.com/Sokrates1989/swarm-python-api-template) repository.

## 🔄 CI/CD Integration

### GitHub Actions

1. **Setup:**
   ```bash
   # Copy example workflow
   cp .github/workflows/build-and-push.yml.example .github/workflows/build-and-push.yml
   
   # Create CI environment config
   cp .ci.env.template .ci.env
   ```

2. **Configure GitHub Secrets:**
   - Go to repository Settings → Secrets and variables → Actions
   - Add secrets:
     - `DOCKER_USERNAME`: Your Docker Hub username
     - `DOCKER_PASSWORD`: Your Docker Hub password or access token

3. **Edit `.ci.env`:**
   ```env
   IMAGE_NAME=your-username/your-api-name
   IMAGE_VERSION=0.0.1
   PYTHON_VERSION=3.13
   DOCKERFILE_PATH=Dockerfile
   ```

4. **Trigger Build:**
   - Push to `main` branch
   - Create a git tag: `git tag v0.0.1 && git push --tags`
   - Manual workflow dispatch from GitHub Actions UI

### GitLab CI

1. **Setup:**
   ```bash
   # Copy example pipeline
   cp .gitlab-ci.yml.example .gitlab-ci.yml
   
   # Create CI environment config
   cp .ci.env.template .ci.env
   ```

2. **Configure GitLab CI/CD Variables:**
   - Go to Settings → CI/CD → Variables
   - Add variables:
     - `DOCKER_USERNAME`: Your Docker Hub username
     - `DOCKER_PASSWORD`: Your Docker Hub password or access token

3. **Edit `.ci.env`:**
   ```env
   IMAGE_NAME=your-username/your-api-name
   IMAGE_VERSION=0.0.1
   PYTHON_VERSION=3.13
   DOCKERFILE_PATH=Dockerfile
   ```

4. **Trigger Build:**
   - Push to `main` or `master` branch
   - Create a git tag: `git tag v1.0.0 && git push --tags`

## 🐳 Container Registries

### Docker Hub

```bash
# Login
docker login

# Build and push (via script)
docker compose -f build-image/docker-compose.build.yml up
```

### GitHub Container Registry (ghcr.io)

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Update .env
IMAGE_NAME=ghcr.io/sokrates1989/python-api-template
```

### GitLab Container Registry

```bash
# Login
docker login registry.gitlab.com

# Update .env
IMAGE_NAME=registry.gitlab.com/username/project/api-name
```

## 📦 Deployment

### Docker Compose (Production Server)

Create `docker-compose.prod.yml` on your server:

```yaml
version: '3.8'

services:
  app:
    image: your-username/your-api-name:1.0.0
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
      - REDIS_URL=redis://redis:6379
      - DEBUG=false
    restart: unless-stopped
    
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: secure-password
      POSTGRES_DB: apidb
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres-data:
```

Deploy:
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Cloud Platforms

- **AWS ECS/Fargate**: Use the image in task definitions
- **Google Cloud Run**: Deploy directly from container registry
- **Azure Container Instances**: Deploy the image
- **DigitalOcean App Platform**: Deploy from Docker Hub
- **Kubernetes**: Use in deployment manifests

## 🔒 Security Best Practices

1. **Non-root User**: Production image runs as non-root user (UID 1000)
2. **Secrets Management**: Never commit `.env` or `.ci.env` to version control
3. **Registry Credentials**: Use CI/CD secrets, not hardcoded values
4. **Image Scanning**: Consider adding vulnerability scanning to CI/CD
5. **Minimal Base Image**: Uses Python slim images to reduce attack surface

## 📊 Build Configuration

The root `Dockerfile` is used for both development and production. Configuration is controlled via:

| Aspect | Development | Production |
|--------|-------------|------------|
| **Dockerfile** | `Dockerfile` | `Dockerfile` (same file) |
| **Build Args** | `IMAGE_TAG=local_docker` | `IMAGE_TAG=0.0.1` |
| **Dependencies** | `pdm install --prod` | `pdm install --prod` |
| **Code Mounting** | Volume mounted (docker-compose) | Copied into image (build) |
| **CMD** | `--reload` flag | No reload flag |

**Key Benefit**: Same Dockerfile ensures what you test locally is what runs in production.

## 🔧 Advanced Configuration

### Custom Python Version

```env
PYTHON_VERSION=3.12
```

### Multi-platform Builds

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg PYTHON_VERSION=3.13-slim \
  -t your-username/your-api-name:1.0.0 \
  -f build-image/Dockerfile \
  --push \
  .
```

### Build Arguments

The Dockerfile supports these build arguments:

- `PYTHON_VERSION`: Python base image version (default: 3.13-slim)
- `IMAGE_TAG`: Tag to bake into the image for traceability

## 🆘 Troubleshooting

### "IMAGE_NAME not set in .env"

**Solution:** Add `IMAGE_NAME=your-username/your-api-name` to `.env`

### "Docker login failed"

**Solution:** Verify credentials and ensure you're logged in:
```bash
docker login
```

### "Permission denied" on Linux

**Solution:** Make script executable:
```bash
chmod +x build-image/build-image.sh
```

### Image Size Too Large

**Solutions:**
- Verify using `-slim` Python base image
- Check that dev dependencies aren't installed
- Use `.dockerignore` to exclude unnecessary files
- Consider multi-stage builds for additional optimization

### Build Fails in CI/CD

**Solutions:**
- Verify CI/CD secrets are set correctly
- Check `.ci.env` configuration
- Ensure Docker registry credentials are valid
- Review CI/CD logs for specific errors

## 📚 Additional Resources

- [Build Image README](../build-image/README.md)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)

## 🎯 Quick Reference

```bash
# Build production image
docker compose -f build-image/docker-compose.build.yml run --rm build-image

# Test production image locally
docker run -p 8000:8000 --env-file .env your-username/your-api-name:0.0.1

# Push to registry manually
docker push your-username/your-api-name:0.0.1
docker push your-username/your-api-name:latest

# Pull and run on production server
docker pull your-username/your-api-name:0.0.1
docker run -p 8000:8000 --env-file .env your-username/your-api-name:0.0.1

# Deploy with Docker Swarm
# See: https://github.com/Sokrates1989/swarm-python-api-template
```
