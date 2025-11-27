# Database Credentials Guide

## Overview

This guide explains how database credentials work in this project, which credentials to use for each database type, and how to secure them for production.

## ⚠️ Security Warning

**NEVER commit production credentials to version control!**

The example `.env` files contain default credentials for **local development only**. These must be changed for production environments.

---

## Credential Usage by Database Type

### PostgreSQL

**Local Docker (DB_MODE=local)**
- **Default credentials:**
  - Username: `postgres`
  - Password: `postgres`
  - Database: `apidb`
- **Where used:**
  - `DB_USER` and `DB_PASSWORD` → Used by `docker-compose.postgres.yml` to create the PostgreSQL container
  - `DATABASE_URL` → Used by the application to connect
  - **IMPORTANT:** Credentials in `DATABASE_URL` must match `DB_USER`/`DB_PASSWORD`

**External Database (DB_MODE=external)**
- Credentials are embedded in `DATABASE_URL`
- `DB_USER` and `DB_PASSWORD` are optional (for reference only)
- Example: `postgresql://myuser:mypassword@db.example.com:5432/mydb`

### Neo4j

**Local Docker (DB_MODE=local)**
- **Default credentials:**
  - Username: `neo4j`
  - Password: `password`
- **Where used:**
  - `DB_USER` and `DB_PASSWORD` → Used by `docker-compose.neo4j.yml` to create the Neo4j container
  - Application reads these variables to connect

**External Database (DB_MODE=external)**
- `DB_USER` and `DB_PASSWORD` are required
- `NEO4J_URL` points to your external server
- Example: `bolt://neo4j.example.com:7687`

### MySQL

**Local Docker (DB_MODE=local)**
- **Default credentials:**
  - Username: `root`
  - Password: `password`
  - Database: `apidb`
- Similar pattern to PostgreSQL

### SQLite

- **No credentials needed** (file-based database)
- Example: `sqlite:///./database.db`

---

## Why Docker Compose Uses DB_USER and DB_PASSWORD

Looking at `docker-compose.postgres.yml`:

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: ${DB_NAME:-apidb}
    POSTGRES_USER: ${DB_USER:-postgres}      # ← Creates PostgreSQL user
    POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}  # ← Sets password
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]  # ← Checks with this user
```

**Why this matters:**
1. When PostgreSQL container starts, it creates a user with `POSTGRES_USER` and `POSTGRES_PASSWORD`
2. The healthcheck verifies the database is ready using this username
3. Your application connects using `DATABASE_URL` which must have matching credentials

---

## How to Change Default Credentials

### For Local Docker Development

#### PostgreSQL:
1. Edit your `.env` file:
   ```env
   DB_USER=myuser
   DB_PASSWORD=mystrongpassword
   DATABASE_URL=postgresql://myuser:mystrongpassword@postgres:5432/apidb
   ```
2. Delete existing data: `rm -rf .docker/postgres-data/`
3. Restart: `docker compose -f docker-compose.postgres.yml up --build`

#### Neo4j:
1. Edit your `.env` file:
   ```env
   DB_USER=neo4j
   DB_PASSWORD=mystrongpassword
   ```
2. Delete existing data: `rm -rf .docker/neo4j-data/`
3. Restart: `docker compose -f docker-compose.neo4j.yml up --build`

### For Production

**DO NOT use plain text credentials in `.env` files!**

---

## Production Security Best Practices

### 1. Use Docker Secrets (Recommended for Docker Swarm)

```yaml
services:
  app:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    external: true
```

Create secret:
```bash
echo "my_secure_password" | docker secret create db_password -
```

### 2. Use Environment Variables from Secure Vaults

**AWS Secrets Manager:**
```bash
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id prod/db/password \
  --query SecretString \
  --output text)
```

**Azure Key Vault:**
```bash
export DB_PASSWORD=$(az keyvault secret show \
  --vault-name mykeyvault \
  --name db-password \
  --query value -o tsv)
```

**HashiCorp Vault:**
```bash
export DB_PASSWORD=$(vault kv get -field=password secret/database)
```

### 3. Use Managed Database Services with IAM

**AWS RDS with IAM Authentication:**
- No password needed
- Uses temporary tokens
- Example: `postgresql://user@rds-instance:5432/db?sslmode=require`

**Azure Database with Managed Identity:**
- Uses Azure AD authentication
- No password in connection string

### 4. Password Requirements

For any passwords you do use:
- **Minimum 20 characters**
- Mix of uppercase, lowercase, numbers, symbols
- Use a password generator
- Rotate regularly (every 90 days)
- Never reuse passwords across environments

### 5. Connection Security

**PostgreSQL:**
```env
# Force SSL/TLS
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Verify certificate
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=verify-full&sslrootcert=/path/to/ca.crt
```

**Neo4j:**
```env
# Use encrypted connection
NEO4J_URL=neo4j+s://host:7687

# Or with bolt+s
NEO4J_URL=bolt+s://host:7687
```

### 6. Principle of Least Privilege

- Use read-only credentials for read-only operations
- Create separate users for different services
- Limit database permissions to only what's needed

**PostgreSQL example:**
```sql
-- Create read-only user
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE mydb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

---

## Credential Checklist

### Development
- [ ] Using default credentials from example files
- [ ] `.env` file is in `.gitignore`
- [ ] Credentials match between `DATABASE_URL` and `DB_USER`/`DB_PASSWORD`

### Staging
- [ ] Changed all default passwords
- [ ] Using environment variables or secrets
- [ ] SSL/TLS enabled for database connections
- [ ] Credentials not committed to version control

### Production
- [ ] Using secure vault (AWS Secrets Manager, Azure Key Vault, etc.)
- [ ] Strong passwords (20+ characters)
- [ ] SSL/TLS enforced
- [ ] IAM authentication (if available)
- [ ] Read-only credentials for read operations
- [ ] Regular password rotation schedule
- [ ] Audit logging enabled
- [ ] Network security groups/firewalls configured

---

## Common Issues

### Issue: "role 'neo4j' does not exist" in PostgreSQL

**Cause:** `DB_USER` has Neo4j credentials but you're using PostgreSQL

**Fix:** Update `.env`:
```env
DB_USER=postgres
DB_PASSWORD=postgres
```

### Issue: Database credentials don't work after changing them

**Cause:** Database container was created with old credentials

**Fix:** Delete data directory and recreate:
```bash
# PostgreSQL
rm -rf .docker/postgres-data/
docker compose -f docker-compose.postgres.yml up --build

# Neo4j
rm -rf .docker/neo4j-data/
docker compose -f docker-compose.neo4j.yml up --build
```

### Issue: Application can't connect to database

**Cause:** Credentials in `DATABASE_URL` don't match `DB_USER`/`DB_PASSWORD`

**Fix:** Ensure they match:
```env
DB_USER=myuser
DB_PASSWORD=mypass
DATABASE_URL=postgresql://myuser:mypass@postgres:5432/apidb
                        # ^^^^^^  ^^^^^^ must match
```

---

## Additional Resources

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Azure Key Vault](https://azure.microsoft.com/en-us/services/key-vault/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [PostgreSQL SSL Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [Neo4j Security Guide](https://neo4j.com/docs/operations-manual/current/security/)
