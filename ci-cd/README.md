# CI/CD Pipeline Setup Guide

This directory contains everything you need to set up a complete CI/CD pipeline for your Python API project.

## 🚀 Quick Start

The easiest way to set up CI/CD is using the interactive setup wizard:

### Option 1: Via Quick Start Script (Recommended)

```bash
# Linux/Mac
./quick-start.sh
# Then select option 6: Setup CI/CD Pipeline

# Windows
.\quick-start.ps1
# Then select option 6: Setup CI/CD Pipeline
```

### Option 2: Direct Setup

```bash
# Linux/Mac
docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup

# Windows PowerShell
docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup
```

## 📋 What the Setup Wizard Does

The interactive setup wizard will guide you through:

1. **Choose CI/CD Platform**
   - GitHub Actions
   - GitLab CI/CD

2. **Choose Deployment Target**
   - Linux Server / Docker Swarm Cluster
   - Azure Container Instances
   - Azure App Service
   - Build Only (no automatic deployment)

3. **Configure Environment**
   - Docker image name and registry
   - Image version
   - Python version

4. **Configure Deployment Settings**
   - Server details (for Linux/Swarm)
   - Azure resource configuration (for Azure deployments)

5. **Generate Configuration Files**
   - Creates `.ci.env` with your settings
   - Copies appropriate workflow/pipeline files
   - Creates deployment configuration files

6. **Display Required Secrets**
   - Shows exactly what secrets/variables you need to add
   - Provides current local values for reference
   - Explains where to add them in GitHub/GitLab

## 📁 Directory Structure

```
ci-cd/
├── README.md                          # This file
├── TROUBLESHOOTING.md                 # Common issues and solutions
├── .ci.env.template                   # Template for CI/CD environment variables
├── docker-compose.cicd-setup.yml      # Docker Compose file for setup wizard
├── scripts/
│   └── setup-cicd.sh                  # Interactive setup script (runs in Docker)
└── templates/
    ├── github/
    │   ├── build-and-push.yml.example # GitHub: Build only
    │   ├── build-deploy-linux.yml     # GitHub: Build + Deploy to Linux
    │   ├── build-deploy-azure-aci.yml # GitHub: Build + Deploy to Azure ACI
    │   └── build-deploy-azure-app.yml # GitHub: Build + Deploy to Azure App Service
    ├── gitlab/
    │   ├── .gitlab-ci.yml.example     # GitLab: Build only
    │   ├── .gitlab-ci-linux.yml       # GitLab: Build + Deploy to Linux
    │   ├── .gitlab-ci-azure-aci.yml   # GitLab: Build + Deploy to Azure ACI
    │   └── .gitlab-ci-azure-app.yml   # GitLab: Build + Deploy to Azure App Service
    └── deployment/
        └── docker-compose.prod.yml    # Production deployment configuration
```

## 🔐 Required Secrets and Variables

### Common (All Platforms)

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `DOCKER_USERNAME` | Docker registry username | Your Docker Hub username |
| `DOCKER_PASSWORD` | Docker registry password/token | Docker Hub access token (recommended) or password |

### Linux Server / Docker Swarm Deployment

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `SSH_PRIVATE_KEY` | SSH private key for server access | Generate with `ssh-keygen -t ed25519 -C "ci-cd-deploy"` |
| `SSH_KNOWN_HOSTS` | Known hosts entry (optional) | Run `ssh-keyscan your-server.com` |

### Azure Deployments

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `AZURE_CREDENTIALS` | Azure service principal credentials | See [Azure Setup Guide](#azure-service-principal-setup) below |

### Production Environment Variables

| Secret Name | Description | Example |
|------------|-------------|---------|
| `PROD_DATABASE_URL` | Production database connection string | `postgresql://user:pass@host:5432/db` |
| `PROD_REDIS_URL` | Production Redis connection string | `redis://host:6379` |
| `PROD_ADMIN_API_KEY` | Production admin API key | Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

## 📍 Where to Add Secrets

### GitHub Actions

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name shown above

### GitLab CI/CD

1. Go to your project on GitLab
2. Click **Settings** → **CI/CD**
3. Expand **Variables** section
4. Click **Add variable**
5. Add each variable with the exact name shown above
6. Check **Mask variable** for sensitive values
7. Check **Protect variable** if you want it only available on protected branches

## 🔧 Azure Service Principal Setup

To deploy to Azure, you need to create a service principal:

```bash
# Login to Azure
az login

# Create service principal
az ad sp create-for-rbac \
  --name "cicd-deploy" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth

# Copy the entire JSON output and add it as AZURE_CREDENTIALS secret
```

For GitLab CI/CD, you can also use individual variables:
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`

## 🖥️ Linux Server Setup

If deploying to a Linux server or Docker Swarm cluster:

### 1. Install Docker on Server

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
```

### 2. Set Up SSH Access

```bash
# On your local machine, generate SSH key pair
ssh-keygen -t ed25519 -C "ci-cd-deploy" -f ~/.ssh/cicd_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/cicd_deploy.pub user@your-server.com

# Test connection
ssh -i ~/.ssh/cicd_deploy user@your-server.com

# Add the PRIVATE key content to your CI/CD secrets as SSH_PRIVATE_KEY
cat ~/.ssh/cicd_deploy
```

### 3. Create Deployment Directory

```bash
# On your server
mkdir -p /opt/api
cd /opt/api

# Create .env file with production credentials
nano .env
```

### 4. Configure Firewall (if needed)

```bash
# Allow HTTP/HTTPS traffic
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # Or your API port
```

## 🌐 Docker Swarm Setup (Optional)

If you want to use Docker Swarm for high availability:

### Initialize Swarm

```bash
# On manager node
docker swarm init

# On worker nodes (use token from init output)
docker swarm join --token <token> <manager-ip>:2377
```

### Deploy as Stack

```bash
# Deploy your application
docker stack deploy -c docker-compose.prod.yml api

# Check status
docker stack services api
docker stack ps api
```

## 🔄 Workflow Triggers

### GitHub Actions

By default, workflows trigger on:
- Push to `main` or `master` branch
- Push of version tags (e.g., `v1.0.0`)
- Manual trigger via GitHub UI

### GitLab CI/CD

By default, pipelines trigger on:
- Push to `main`, `master`, or `dev` branch
- Push of version tags
- Manual trigger via GitLab UI

Deployment jobs are set to `when: manual` for safety.

## 📝 Customization

### Modify Trigger Branches

**GitHub Actions** (`.github/workflows/ci-cd.yml`):
```yaml
on:
  push:
    branches: [ main, develop, staging ]  # Add your branches
```

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
only:
  - main
  - develop
  - staging  # Add your branches
```

### Change Deployment Conditions

**GitHub Actions**:
```yaml
deploy-to-server:
  if: github.ref == 'refs/heads/main'  # Only deploy from main
```

**GitLab CI**:
```yaml
deploy-production:
  only:
    - main  # Only deploy from main
  when: manual  # Require manual approval
```

### Adjust Resource Limits

Edit `docker-compose.prod.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Adjust CPU limit
      memory: 2G       # Adjust memory limit
```

## 🧪 Testing Your Pipeline

### 1. Test Locally First

```bash
# Build the production image
docker compose -f build-image/docker-compose.build.yml run --rm build-image

# Test the image
docker run -p 8000:8000 --env-file .env your-image:latest
```

### 2. Test CI/CD Without Deployment

1. Set up secrets in GitHub/GitLab
2. Push to a test branch first
3. Verify the build succeeds
4. Check the built image in your registry

### 3. Test Deployment

1. For Linux servers: Test SSH connection manually first
2. For Azure: Test Azure CLI commands manually first
3. Use manual deployment triggers initially
4. Monitor logs during first deployment

## 📊 Monitoring Your Pipeline

### GitHub Actions

- Go to **Actions** tab in your repository
- Click on a workflow run to see details
- Check individual job logs
- View deployment status in **Environments** tab

### GitLab CI/CD

- Go to **CI/CD** → **Pipelines**
- Click on a pipeline to see stages
- View job logs by clicking on job names
- Check deployment status in **Deployments** → **Environments**

## 🔍 Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Docker Documentation](https://docs.docker.com/)
- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)

## 🆘 Getting Help

If you encounter issues:

1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Review pipeline/workflow logs
3. Verify all secrets are set correctly
4. Test components individually (build, SSH, Azure CLI, etc.)
5. Check server logs: `docker compose -f docker-compose.prod.yml logs`

## 🔒 Security Best Practices

1. **Never commit secrets** to version control
2. **Use access tokens** instead of passwords for Docker registry
3. **Rotate secrets regularly** (every 90 days recommended)
4. **Use different credentials** for development and production
5. **Enable 2FA** on GitHub/GitLab accounts
6. **Restrict SSH access** to specific IP addresses if possible
7. **Use Docker secrets** for production deployments
8. **Keep base images updated** to patch security vulnerabilities
9. **Scan images** for vulnerabilities before deployment
10. **Monitor access logs** on your servers

## 📄 License

This CI/CD setup is part of your Python API template project.
