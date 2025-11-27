# CI/CD Secrets and Variables Quick Reference

This guide provides a quick reference for all secrets and variables needed for your CI/CD pipeline.

## 🔐 Required Secrets by Deployment Type

### ✅ All Deployments (Required)

| Secret Name | Description | Where to Get | GitHub Location | GitLab Location |
|------------|-------------|--------------|-----------------|-----------------|
| `DOCKER_USERNAME` | Docker Hub username | Your Docker Hub account | Settings → Secrets → Actions | Settings → CI/CD → Variables |
| `DOCKER_PASSWORD` | Docker Hub access token | Docker Hub → Account Settings → Security → New Access Token | Settings → Secrets → Actions | Settings → CI/CD → Variables |

**How to create Docker Hub access token:**
1. Go to [Docker Hub](https://hub.docker.com/)
2. Click your profile → Account Settings
3. Go to Security → Access Tokens
4. Click "New Access Token"
5. Give it a name (e.g., "CI/CD Pipeline")
6. Copy the token and save it as `DOCKER_PASSWORD` secret

---

### 🖥️ Linux Server / Docker Swarm Deployment

| Secret Name | Description | How to Generate | Example |
|------------|-------------|-----------------|---------|
| `SSH_PRIVATE_KEY` | SSH private key for server access | `ssh-keygen -t ed25519 -C "ci-cd-deploy"` | Contents of `~/.ssh/id_ed25519` |
| `SSH_KNOWN_HOSTS` | Server's SSH fingerprint (optional) | `ssh-keyscan your-server.com` | `your-server.com ssh-ed25519 AAAA...` |

**Step-by-step SSH setup:**

```bash
# 1. Generate SSH key pair
ssh-keygen -t ed25519 -C "ci-cd-deploy" -f ~/.ssh/cicd_deploy

# 2. Copy public key to server
ssh-copy-id -i ~/.ssh/cicd_deploy.pub user@your-server.com

# 3. Test connection
ssh -i ~/.ssh/cicd_deploy user@your-server.com

# 4. Get private key content (add this to SSH_PRIVATE_KEY secret)
cat ~/.ssh/cicd_deploy

# 5. Get known hosts entry (add this to SSH_KNOWN_HOSTS secret)
ssh-keyscan your-server.com
```

**Additional variables in `.ci.env`:**
```bash
DEPLOY_SERVER=your-server.com
DEPLOY_USER=deploy
DEPLOY_PATH=/opt/api
```

---

### ☁️ Azure Container Instances Deployment

| Secret Name | Description | How to Generate |
|------------|-------------|-----------------|
| `AZURE_CREDENTIALS` | Service principal JSON | See command below |

**For GitHub Actions:**
```bash
# Login to Azure
az login

# Create service principal (copy entire JSON output)
az ad sp create-for-rbac \
  --name "cicd-deploy" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth
```

**For GitLab CI (alternative - use individual variables):**

| Variable Name | Description | How to Get |
|--------------|-------------|------------|
| `AZURE_CLIENT_ID` | Service principal app ID | From service principal output: `clientId` |
| `AZURE_CLIENT_SECRET` | Service principal password | From service principal output: `clientSecret` |
| `AZURE_TENANT_ID` | Azure tenant ID | From service principal output: `tenantId` |

**Additional variables in `.ci.env`:**
```bash
AZURE_RESOURCE_GROUP=my-resource-group
AZURE_CONTAINER_NAME=my-api-container
AZURE_LOCATION=westeurope
```

---

### ☁️ Azure App Service Deployment

Same as Azure Container Instances above, plus:

**Additional variables in `.ci.env`:**
```bash
AZURE_RESOURCE_GROUP=my-resource-group
AZURE_APP_NAME=my-api-app
AZURE_LOCATION=westeurope
```

---

## 🔒 Production Environment Secrets

These should be **different** from your local development values!

| Secret Name | Description | How to Generate | Example |
|------------|-------------|-----------------|---------|
| `PROD_DATABASE_URL` | Production database connection | Your database provider | `postgresql://user:pass@prod-db.com:5432/apidb` |
| `PROD_REDIS_URL` | Production Redis connection | Your Redis provider | `redis://prod-redis.com:6379` |
| `PROD_ADMIN_API_KEY` | Production admin API key | Generate random token | See command below |

**Generate secure API key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📍 Where to Add Secrets

### GitHub Actions

1. Go to your repository on GitHub
2. Click **Settings** (repository settings, not your account)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter the secret name (exactly as shown above)
6. Paste the secret value
7. Click **Add secret**

**Screenshot locations:**
- Repository → Settings → Secrets and variables → Actions → New repository secret

### GitLab CI/CD

1. Go to your project on GitLab
2. In the left sidebar, click **Settings** → **CI/CD**
3. Find the **Variables** section and click **Expand**
4. Click **Add variable**
5. Enter the variable key (exactly as shown above)
6. Paste the variable value
7. Check **Mask variable** for sensitive values
8. Optionally check **Protect variable** (only available on protected branches)
9. Click **Add variable**

**Screenshot locations:**
- Project → Settings → CI/CD → Variables → Add variable

---

## 📋 Checklist: Before First Deployment

### Common Setup (All Platforms)

- [ ] `DOCKER_USERNAME` secret added
- [ ] `DOCKER_PASSWORD` secret added (use access token, not password)
- [ ] `.ci.env` file created and committed
- [ ] `IMAGE_NAME` in `.ci.env` matches your Docker Hub username/repo
- [ ] Workflow/pipeline file copied to correct location
- [ ] Changes committed and pushed to repository

### Linux Server Deployment

- [ ] `SSH_PRIVATE_KEY` secret added
- [ ] `SSH_KNOWN_HOSTS` secret added (optional but recommended)
- [ ] Docker installed on server
- [ ] Docker Compose installed on server
- [ ] SSH public key added to server's `~/.ssh/authorized_keys`
- [ ] Deployment directory created on server (`/opt/api`)
- [ ] Firewall configured to allow traffic on required ports
- [ ] `DEPLOY_SERVER`, `DEPLOY_USER`, `DEPLOY_PATH` set in `.ci.env`

### Azure Deployment

- [ ] `AZURE_CREDENTIALS` secret added (GitHub) OR
- [ ] `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` added (GitLab)
- [ ] Azure resource group created
- [ ] Service principal has contributor role on resource group
- [ ] `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_NAME`/`AZURE_APP_NAME`, `AZURE_LOCATION` set in `.ci.env`

### Production Environment

- [ ] `PROD_DATABASE_URL` secret added
- [ ] `PROD_REDIS_URL` secret added
- [ ] `PROD_ADMIN_API_KEY` secret added (newly generated, not from .env)
- [ ] Production database is accessible from deployment target
- [ ] Production Redis is accessible from deployment target

---

## 🧪 Testing Secrets

### Test Docker Hub Login

```bash
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
```

### Test SSH Connection

```bash
ssh -i ~/.ssh/cicd_deploy user@your-server.com "echo 'Connection successful!'"
```

### Test Azure Login

```bash
# Using service principal
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID

# List resources to verify access
az group list
```

### Test Database Connection

```bash
# PostgreSQL
psql "$PROD_DATABASE_URL" -c "SELECT 1;"

# Or using Docker
docker run --rm postgres:16-alpine psql "$PROD_DATABASE_URL" -c "SELECT 1;"
```

---

## 🔄 Rotating Secrets

For security, rotate secrets regularly (recommended: every 90 days).

### Rotate Docker Hub Token

1. Create new access token in Docker Hub
2. Update `DOCKER_PASSWORD` secret in GitHub/GitLab
3. Delete old token from Docker Hub

### Rotate SSH Key

1. Generate new SSH key pair
2. Add new public key to server
3. Update `SSH_PRIVATE_KEY` secret
4. Test deployment
5. Remove old public key from server

### Rotate Azure Service Principal

1. Create new service principal
2. Update `AZURE_CREDENTIALS` or individual variables
3. Test deployment
4. Delete old service principal

### Rotate Production API Key

1. Generate new API key
2. Update `PROD_ADMIN_API_KEY` secret
3. Deploy application
4. Update any clients using the old key

---

## 🚨 Security Warnings

### ⚠️ Never Do This:

- ❌ Commit secrets to Git repository
- ❌ Share secrets in chat/email
- ❌ Use production secrets in development
- ❌ Use weak passwords or default values
- ❌ Store secrets in plain text files
- ❌ Use the same secret across multiple environments

### ✅ Always Do This:

- ✅ Use access tokens instead of passwords
- ✅ Generate unique secrets for production
- ✅ Rotate secrets regularly
- ✅ Use different secrets for dev/staging/prod
- ✅ Enable 2FA on GitHub/GitLab accounts
- ✅ Mask sensitive variables in CI/CD logs
- ✅ Use Docker secrets for production deployments
- ✅ Monitor access logs for suspicious activity

---

## 📞 Quick Reference Commands

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "ci-cd-deploy" -f ~/.ssh/cicd_deploy

# Get SSH known hosts
ssh-keyscan your-server.com

# Generate API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Create Azure service principal
az ad sp create-for-rbac --name "cicd-deploy" --role contributor --scopes /subscriptions/{sub-id}/resourceGroups/{rg} --sdk-auth

# Test Docker login
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Test SSH connection
ssh -i ~/.ssh/cicd_deploy user@server "docker --version"

# Test Azure login
az login --service-principal -u $CLIENT_ID -p $SECRET --tenant $TENANT
```

---

## 📚 Related Documentation

- [Main CI/CD README](./README.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitLab CI Variables Documentation](https://docs.gitlab.com/ee/ci/variables/)
