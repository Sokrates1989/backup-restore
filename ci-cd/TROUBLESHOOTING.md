# CI/CD Troubleshooting Guide

This guide covers common issues you might encounter when setting up or running your CI/CD pipeline.

## 🔍 Table of Contents

- [Setup Issues](#setup-issues)
- [Build Issues](#build-issues)
- [Deployment Issues](#deployment-issues)
- [GitHub Actions Specific](#github-actions-specific)
- [GitLab CI Specific](#gitlab-ci-specific)
- [Azure Deployment Issues](#azure-deployment-issues)
- [Linux Server Deployment Issues](#linux-server-deployment-issues)

---

## Setup Issues

### ❌ Setup wizard fails to start

**Symptoms:**
```
Error: Cannot find docker-compose.cicd-setup.yml
```

**Solution:**
```bash
# Make sure you're in the project root directory
cd /path/to/your/project

# Verify the file exists
ls ci-cd/docker-compose.cicd-setup.yml

# If missing, the ci-cd directory might not be set up correctly
```

### ❌ .env file not found during setup

**Symptoms:**
```
❌ .env file not found!
```

**Solution:**
```bash
# Create .env from template
cp config/.env.template .env

# Or run the setup wizard first
./quick-start.sh  # Linux/Mac
.\quick-start.ps1  # Windows
```

### ❌ Permission denied when running setup script

**Symptoms:**
```
Permission denied: ./ci-cd/scripts/setup-cicd.sh
```

**Solution:**
```bash
# Make script executable
chmod +x ci-cd/scripts/setup-cicd.sh

# Or run via docker-compose (recommended)
docker compose -f ci-cd/docker-compose.cicd-setup.yml run --rm cicd-setup
```

---

## Build Issues

### ❌ Docker build fails with "PYTHON_VERSION not set"

**Symptoms:**
```
Error: PYTHON_VERSION is not set
```

**Solution:**
1. Check `.ci.env` file exists and contains `PYTHON_VERSION=3.13`
2. Verify `.ci.env` is being loaded in your workflow/pipeline
3. Check for typos in variable names

```bash
# Verify .ci.env content
cat .ci.env | grep PYTHON_VERSION

# Should output: PYTHON_VERSION=3.13
```

### ❌ Docker build fails with "IMAGE_NAME not set"

**Symptoms:**
```
Error: IMAGE_NAME is not set or using default value
```

**Solution:**
1. Update `.ci.env` with your actual image name:
```bash
IMAGE_NAME=yourusername/your-api-name
```

2. Commit and push the change:
```bash
git add .ci.env
git commit -m "Update IMAGE_NAME"
git push
```

### ❌ Docker login fails

**Symptoms:**
```
Error: Error response from daemon: Get https://registry-1.docker.io/v2/: unauthorized
```

**Solution:**
1. Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set correctly
2. Use an access token instead of password:
   - Go to Docker Hub → Account Settings → Security
   - Create new access token
   - Update `DOCKER_PASSWORD` secret with the token

### ❌ Build succeeds but push fails

**Symptoms:**
```
Error: denied: requested access to the resource is denied
```

**Solution:**
1. Verify you have push access to the registry
2. Check if the repository exists on Docker Hub
3. Ensure `IMAGE_NAME` format is correct: `username/repo-name`
4. For private registries, verify registry URL in login step

---

## Deployment Issues

### ❌ Deployment job doesn't run

**Symptoms:**
- Build succeeds but deployment is skipped

**Solution:**

**GitHub Actions:**
```yaml
# Check the condition in your workflow
deploy-to-server:
  if: github.ref == 'refs/heads/main'  # Only runs on main branch
```

**GitLab CI:**
```yaml
# Check the 'only' section
deploy-production:
  only:
    - main  # Only runs on main branch
  when: manual  # Requires manual trigger
```

### ❌ Container fails to start after deployment

**Symptoms:**
```
Error: Container exits immediately after starting
```

**Solution:**
1. Check container logs:
```bash
docker compose -f docker-compose.prod.yml logs api
```

2. Common causes:
   - Missing environment variables
   - Database connection issues
   - Port already in use
   - Health check failing

3. Test locally first:
```bash
docker run -p 8000:8000 --env-file .env your-image:latest
```

### ❌ Environment variables not being passed

**Symptoms:**
- Application can't connect to database
- Missing configuration values

**Solution:**
1. Verify secrets are set in GitHub/GitLab
2. Check `docker-compose.prod.yml` environment section
3. Ensure secret names match exactly (case-sensitive)
4. For Azure: Check App Settings in Azure Portal

---

## GitHub Actions Specific

### ❌ Workflow doesn't trigger

**Symptoms:**
- Push to main but no workflow runs

**Solution:**
1. Check workflow file location: `.github/workflows/ci-cd.yml`
2. Verify YAML syntax:
```bash
# Use a YAML validator
cat .github/workflows/ci-cd.yml | docker run --rm -i cytopia/yamllint
```

3. Check branch name matches trigger:
```yaml
on:
  push:
    branches: [ main, master ]  # Must match your branch name
```

### ❌ "Secret not found" error

**Symptoms:**
```
Error: Secret DOCKER_PASSWORD not found
```

**Solution:**
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Verify secret exists and name matches exactly
3. Secrets are case-sensitive: `DOCKER_PASSWORD` ≠ `docker_password`
4. Re-create the secret if needed

### ❌ Actions runner out of disk space

**Symptoms:**
```
Error: No space left on device
```

**Solution:**
1. Clean up Docker cache in workflow:
```yaml
- name: Clean up Docker
  run: docker system prune -af
```

2. Use smaller base images
3. Remove unnecessary build artifacts

### ❌ Job timeout

**Symptoms:**
```
Error: The job running on runner has exceeded the maximum execution time of 360 minutes
```

**Solution:**
1. Increase timeout (if needed):
```yaml
jobs:
  build:
    timeout-minutes: 60  # Adjust as needed
```

2. Optimize build:
   - Use build cache
   - Reduce image size
   - Parallelize steps

---

## GitLab CI Specific

### ❌ Pipeline doesn't start

**Symptoms:**
- Push to repository but no pipeline runs

**Solution:**
1. Check `.gitlab-ci.yml` exists in repository root
2. Verify YAML syntax in GitLab UI: CI/CD → Editor
3. Check if CI/CD is enabled: Settings → General → Visibility → CI/CD
4. Verify runner is available: Settings → CI/CD → Runners

### ❌ "Variable not found" error

**Symptoms:**
```
Error: DOCKER_PASSWORD: variable not found
```

**Solution:**
1. Go to GitLab project → Settings → CI/CD → Variables
2. Add variable with exact name
3. Check "Mask variable" for sensitive values
4. Uncheck "Protect variable" if running on non-protected branches

### ❌ No runner available

**Symptoms:**
```
This job is stuck because you don't have any active runners
```

**Solution:**
1. Use GitLab.com shared runners (if available)
2. Or register your own runner:
```bash
# Install GitLab Runner
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner

# Register runner
sudo gitlab-runner register
```

### ❌ Docker-in-Docker issues

**Symptoms:**
```
Error: Cannot connect to the Docker daemon
```

**Solution:**
1. Ensure using `docker:dind` service:
```yaml
services:
  - docker:24-dind
```

2. Set required variables:
```yaml
variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
```

---

## Azure Deployment Issues

### ❌ Azure login fails

**Symptoms:**
```
Error: Azure login failed
```

**Solution:**
1. Verify `AZURE_CREDENTIALS` secret is set correctly
2. Check service principal has correct permissions
3. Recreate service principal:
```bash
az ad sp create-for-rbac \
  --name "cicd-deploy" \
  --role contributor \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg} \
  --sdk-auth
```

### ❌ Resource group not found

**Symptoms:**
```
Error: Resource group 'xxx' could not be found
```

**Solution:**
1. Create resource group:
```bash
az group create --name your-rg --location westeurope
```

2. Verify name in `.ci.env` matches exactly

### ❌ Container instance fails to start

**Symptoms:**
```
Error: Container instance failed to start
```

**Solution:**
1. Check Azure Portal logs: Container Instances → Logs
2. Verify environment variables are set correctly
3. Check if ports are configured correctly
4. Ensure image is publicly accessible or credentials are provided

### ❌ App Service deployment fails

**Symptoms:**
```
Error: Failed to deploy to App Service
```

**Solution:**
1. Verify App Service exists:
```bash
az webapp show --name your-app --resource-group your-rg
```

2. Check if App Service plan supports containers
3. Verify `WEBSITES_PORT` is set to your app's port (usually 8000)
4. Check App Service logs in Azure Portal

---

## Linux Server Deployment Issues

### ❌ SSH connection fails

**Symptoms:**
```
Error: Permission denied (publickey)
```

**Solution:**
1. Verify SSH private key is added to secrets correctly
2. Test SSH connection manually:
```bash
ssh -i ~/.ssh/your_key user@server
```

3. Ensure public key is in server's `~/.ssh/authorized_keys`
4. Check SSH key format (should be RSA or Ed25519)
5. Verify server allows key-based authentication

### ❌ SSH host key verification fails

**Symptoms:**
```
Error: Host key verification failed
```

**Solution:**
1. Add `SSH_KNOWN_HOSTS` secret:
```bash
ssh-keyscan your-server.com
```

2. Or disable strict host checking (less secure):
```yaml
- run: |
    mkdir -p ~/.ssh
    echo "StrictHostKeyChecking no" >> ~/.ssh/config
```

### ❌ Docker not found on server

**Symptoms:**
```
Error: docker: command not found
```

**Solution:**
1. Install Docker on server:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

2. Install Docker Compose plugin:
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### ❌ Permission denied when running Docker

**Symptoms:**
```
Error: Got permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
1. Add deployment user to docker group:
```bash
sudo usermod -aG docker $USER
```

2. Or use sudo in deployment script (less secure)

### ❌ Port already in use

**Symptoms:**
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solution:**
1. Stop existing containers:
```bash
docker compose -f docker-compose.prod.yml down
```

2. Check what's using the port:
```bash
sudo lsof -i :8000
```

3. Change port in `docker-compose.prod.yml` if needed

### ❌ Deployment directory doesn't exist

**Symptoms:**
```
Error: No such file or directory: /opt/api
```

**Solution:**
1. Create directory on server:
```bash
ssh user@server "mkdir -p /opt/api"
```

2. Ensure deployment user has write permissions:
```bash
ssh user@server "sudo chown $USER:$USER /opt/api"
```

---

## General Debugging Tips

### Enable Debug Logging

**GitHub Actions:**
```yaml
- name: Debug
  run: |
    echo "IMAGE_NAME=$IMAGE_NAME"
    echo "IMAGE_TAG=$IMAGE_TAG"
    env | sort
```

**GitLab CI:**
```yaml
script:
  - echo "IMAGE_NAME=$IMAGE_NAME"
  - echo "IMAGE_TAG=$IMAGE_TAG"
  - env | sort
```

### Test Components Individually

1. **Test Docker build locally:**
```bash
docker build -t test:latest .
```

2. **Test Docker push:**
```bash
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker push your-image:latest
```

3. **Test SSH connection:**
```bash
ssh -i ~/.ssh/key user@server "docker --version"
```

4. **Test Azure CLI:**
```bash
az login --service-principal -u $CLIENT_ID -p $SECRET --tenant $TENANT
az group list
```

### Check Logs

**Docker container logs:**
```bash
docker logs container-name
docker compose -f docker-compose.prod.yml logs
```

**System logs on Linux server:**
```bash
sudo journalctl -u docker
sudo tail -f /var/log/syslog
```

**Azure logs:**
```bash
az container logs --resource-group rg --name container-name
az webapp log tail --name app-name --resource-group rg
```

---

## Still Having Issues?

If you're still experiencing problems:

1. **Check the main README:** [README.md](./README.md)
2. **Review workflow/pipeline logs** carefully
3. **Test each component individually**
4. **Verify all secrets and variables** are set correctly
5. **Check for typos** in configuration files
6. **Ensure all prerequisites** are installed and configured
7. **Try a minimal configuration** first, then add complexity

## 📚 Additional Resources

- [GitHub Actions Troubleshooting](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)
- [GitLab CI Troubleshooting](https://docs.gitlab.com/ee/ci/troubleshooting.html)
- [Docker Troubleshooting](https://docs.docker.com/config/daemon/troubleshoot/)
- [Azure Troubleshooting](https://docs.microsoft.com/en-us/azure/container-instances/container-instances-troubleshooting)
