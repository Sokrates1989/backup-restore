## Database Backup and Restore

This template includes a complete backup and restore system with API endpoints for SQL databases (PostgreSQL, MySQL, SQLite).

## Features

✅ **Create backups** via API endpoint  
✅ **Download backups** as files  
✅ **Restore from existing backups**  
✅ **Upload and restore** from external backup files  
✅ **List all backups** with metadata (including safety backups)  
✅ **Delete old backups**  
✅ **Automatic compression** with gzip  
✅ **Tiered security** with separate API keys for admin, restore, and delete operations  
✅ **Safety backups** - Automatically creates backup before restore  
✅ **Clean restore** - Drops existing data before restoring  
✅ **Volume mounted** - Backups accessible on host system  
✅ **Supports all databases** - PostgreSQL, MySQL, SQLite, Neo4j  

---

## Quick Start

### 1. Create a Backup

```bash
curl -X POST "http://localhost:8081/backup/create?compress=true" \
  -H "X-Admin-Key: your-admin-key"
```

**Response:**
```json
{
  "success": true,
  "message": "Backup created successfully: backup_postgresql_20241110_120000.sql.gz",
  "filename": "backup_postgresql_20241110_120000.sql.gz",
  "size_mb": 2.45
}
```

### 2. Download the Backup

```bash
curl -X GET "http://localhost:8081/backup/download/backup_postgresql_20241110_120000.sql.gz" \
  -H "X-Admin-Key: your-admin-key" \
  -O
```

### 3. Restore from Backup

```bash
curl -X POST "http://localhost:8081/backup/restore/backup_postgresql_20241110_120000.sql.gz?create_safety_backup=true" \
  -H "X-Restore-Key: your-restore-key"
```

---

## Security - Tiered API Keys

The backup system uses **three levels of API keys** for different operations:

### Level 1: Admin Key (`X-Admin-Key`)
**Read-only operations** - Low risk
- Create backups
- Download backups
- List backups

### Level 2: Restore Key (`X-Restore-Key`)
**Destructive operations** - Medium risk
- Restore from backup (overwrites database)
- Upload and restore

⚠️ **WARNING:** Restore operations will:
1. Create a safety backup of current data (unless disabled)
2. Drop all existing tables and data
3. Restore from the backup file

### Level 3: Delete Key (`X-Delete-Key`)
**Permanent deletion** - High risk
- Delete backup files

⚠️ **WARNING:** Deletion is permanent and cannot be undone!

### Configuration

Set these in your `.env` file:

```env
# Level 1: Admin read operations
ADMIN_API_KEY=change-this-to-a-secure-random-key

# Level 2: Restore operations (overwrites database!)
BACKUP_RESTORE_API_KEY=change-this-restore-key-to-something-secure

# Level 3: Delete operations (permanent deletion!)
BACKUP_DELETE_API_KEY=change-this-delete-key-to-something-secure
```

**Best Practice:** Use different keys for each level to limit damage from key compromise.

---

## API Endpoints

### POST `/backup/create`

Create a new database backup.

**Parameters:**
- `compress` (query, optional): Whether to compress with gzip (default: true)

**Response:**
```json
{
  "success": true,
  "message": "Backup created successfully: backup_postgresql_20241110_120000.sql.gz",
  "filename": "backup_postgresql_20241110_120000.sql.gz",
  "size_mb": 2.45
}
```

**Example:**
```bash
# Compressed backup (default)
curl -X POST "http://localhost:8081/backup/create?compress=true" \
  -H "X-Admin-Key: your-admin-key"

# Uncompressed backup
curl -X POST "http://localhost:8081/backup/create?compress=false" \
  -H "X-Admin-Key: your-admin-key"
```

---

### GET `/backup/download/{filename}`

Download a backup file.

**Parameters:**
- `filename` (path): Name of the backup file

**Response:** Binary file download

**Example:**
```bash
curl -X GET "http://localhost:8081/backup/download/backup_postgresql_20241110_120000.sql.gz" \
  -H "X-Admin-Key: your-admin-key" \
  -O
```

---

### POST `/backup/restore/{filename}`

Restore database from an existing backup file.

**⚠️ WARNING: This will overwrite the current database!**

**Authentication:** Requires `X-Restore-Key` header

**What happens during restore:**
1. **Safety backup** - Creates a backup of current data (unless `create_safety_backup=false`)
2. **Drop tables** - Removes all existing tables and data
3. **Restore** - Loads data from the backup file

**Parameters:**
- `filename` (path): Name of the backup file to restore from
- `create_safety_backup` (query, optional): Create safety backup before restore (default: true)

**Response:**
```json
{
  "success": true,
  "message": "Database restored successfully from: backup_postgresql_20241110_120000.sql.gz",
  "safety_backup_created": true,
  "safety_backup_filename": "safety_backup_postgresql_20251111_143022.sql.gz"
}
```

**Examples:**
```bash
# Restore with safety backup (recommended)
curl -X POST "http://localhost:8081/backup/restore/backup_postgresql_20241110_120000.sql.gz?create_safety_backup=true" \
  -H "X-Restore-Key: your-restore-key"

# Restore without safety backup (not recommended)
curl -X POST "http://localhost:8081/backup/restore/backup_postgresql_20241110_120000.sql.gz?create_safety_backup=false" \
  -H "X-Restore-Key: your-restore-key"
```

---

### POST `/backup/restore-upload`

Upload and restore from a backup file.

**⚠️ WARNING: This will overwrite the current database!**

**Authentication:** Requires `X-Restore-Key` header

**What happens during restore:**
1. **Safety backup** - Creates a backup of current data (unless `create_safety_backup=false`)
2. **Drop tables** - Removes all existing tables and data
3. **Restore** - Loads data from the uploaded backup file

**Parameters:**
- `file` (form-data): Backup file to upload
- `create_safety_backup` (query, optional): Create safety backup before restore (default: true)

**Response:**
```json
{
  "success": true,
  "message": "Database restored successfully from uploaded file: my_backup.sql.gz",
  "safety_backup_created": true,
  "safety_backup_filename": "safety_backup_postgresql_20251111_143022.sql.gz"
}
```

**Examples:**
```bash
# Upload and restore with safety backup (recommended)
curl -X POST "http://localhost:8081/backup/restore-upload?create_safety_backup=true" \
  -H "X-Restore-Key: your-restore-key" \
  -F "file=@/path/to/backup.sql.gz"

# Upload and restore without safety backup (not recommended)
curl -X POST "http://localhost:8081/backup/restore-upload?create_safety_backup=false" \
  -H "X-Restore-Key: your-restore-key" \
  -F "file=@/path/to/backup.sql.gz"
```

---

### GET `/backup/list`

List all available backup files.

**Response:**
```json
{
  "backups": [
    {
      "filename": "backup_postgresql_20241110_120000.sql.gz",
      "size_bytes": 2567890,
      "size_mb": 2.45,
      "created_at": "2024-11-10T12:00:00",
      "compressed": true
    },
    {
      "filename": "backup_postgresql_20241109_180000.sql.gz",
      "size_bytes": 2345678,
      "size_mb": 2.24,
      "created_at": "2024-11-09T18:00:00",
      "compressed": true
    }
  ],
  "total_count": 2
}
```

**Example:**
```bash
curl -X GET "http://localhost:8081/backup/list" \
  -H "X-Admin-Key: your-admin-key"
```

---

### DELETE `/backup/delete/{filename}`

Delete a backup file.

**⚠️ WARNING: This permanently deletes the backup file!**

**Authentication:** Requires `X-Delete-Key` header

**Parameters:**
- `filename` (path): Name of the backup file to delete

**Response:**
```json
{
  "success": true,
  "message": "Backup deleted successfully: backup_postgresql_20241110_120000.sql.gz"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8081/backup/delete/backup_postgresql_20241110_120000.sql.gz" \
  -H "X-Delete-Key: your-delete-key"
```

---

## Backup Storage

### Location

Backups are stored in the `backups/` directory at the project root.

**Volume Mount:** The backups directory is mounted as a Docker volume, making backups accessible on the host system at:
```
d:\Development\Code\python\python-api-template\backups\
```

### File Types

- **Regular backups:** `backup_<db_type>_<timestamp>.sql[.gz]`
- **Safety backups:** `safety_backup_<db_type>_<timestamp>.sql.gz`

Safety backups are automatically created before restore operations to protect against data loss.

### Persistence

✅ **Backups persist** across container restarts  
✅ **Accessible on host** for external backup solutions  
✅ **Can be copied** to external storage  
✅ **Version controlled** (excluded via `.gitignore`)  

### Best Practices

1. **Regular backups** - Schedule automated backups via cron or CI/CD
2. **External storage** - Copy important backups to cloud storage (S3, Azure Blob, etc.)
3. **Test restores** - Periodically test restore process to ensure backups are valid
4. **Retention policy** - Delete old backups to save space
5. **Monitor size** - Large databases may require significant storage

---

## Supported Databases

### PostgreSQL

Uses `pg_dump` and `psql` for backup/restore.

**Backup format:** Plain SQL text  
**Compression:** gzip (optional)  
**Filename:** `backup_postgresql_YYYYMMDD_HHMMSS.sql[.gz]`

**Features:**
- Consistent backups with transactions
- No ownership/ACL commands (portable)
- Works with any PostgreSQL version

### MySQL

Uses `mysqldump` and `mysql` for backup/restore.

**Backup format:** Plain SQL text  
**Compression:** gzip (optional)  
**Filename:** `backup_mysql_YYYYMMDD_HHMMSS.sql[.gz]`

**Features:**
- Single-transaction backups
- No table locking
- Works with MySQL and MariaDB

### SQLite

Direct file copy for backup/restore.

**Backup format:** SQLite database file  
**Compression:** gzip (optional)  
**Filename:** `backup_sqlite_YYYYMMDD_HHMMSS.db[.gz]`

**Features:**
- Fast file-based backup
- Automatic current database backup before restore
- No external tools needed

### Neo4j

Exports all nodes and relationships as Cypher CREATE statements.

**Backup format:** Cypher script  
**Compression:** gzip (optional)  
**Filename:** `backup_neo4j_YYYYMMDD_HHMMSS.cypher[.gz]`

**Features:**
- Exports all nodes with labels and properties
- Exports all relationships with types and properties
- Portable Cypher scripts
- Optional APOC plugin support for efficient export
- Database statistics endpoint

**Two backup methods:**

1. **Standard Cypher Export** (default):
   - Uses Neo4j driver to query all nodes and relationships
   - Generates CREATE statements
   - Works without any plugins
   - Suitable for small to medium databases

2. **APOC Export** (optional):
   - Uses APOC plugin's `apoc.export.cypher.all()`
   - More efficient for large databases
   - Requires APOC plugin installed
   - Use with `?use_apoc=true` parameter

**Additional endpoint:**
- `GET /backup/stats` - Get database statistics (node count, relationship count, labels, types)

---

## Security

### Admin Authentication Required

All backup endpoints require the `X-Admin-Key` header:

```bash
-H "X-Admin-Key: your-admin-key"
```

Set your admin key in `.env`:
```env
ADMIN_API_KEY=your-secure-random-key-here
```

**Generate a secure key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Best Practices

1. ✅ **Use strong admin keys** - Generate random, long keys
2. ✅ **Never commit keys** - Keep `.env` out of version control
3. ✅ **Rotate keys regularly** - Change admin keys periodically
4. ✅ **Use HTTPS in production** - Encrypt API traffic
5. ✅ **Limit backup access** - Only trusted admins should have keys
6. ✅ **Store backups securely** - Keep backups in secure locations
7. ✅ **Test restores regularly** - Verify backups actually work

---

## Backup Storage

### Default Location

Backups are stored in `/app/backups/` inside the container.

### Persistent Storage

To persist backups across container restarts, mount a volume:

```yaml
# docker-compose.yml
services:
  app:
    volumes:
      - ./backups:/app/backups  # Persist backups locally
```

### External Storage

For production, consider:
- **AWS S3** - Store backups in S3 buckets
- **Azure Blob Storage** - Use Azure for backup storage
- **Google Cloud Storage** - GCS for backup storage
- **Network drives** - Mount network storage
- **Backup services** - Use dedicated backup solutions

---

## Automation

### Scheduled Backups

Create a cron job or scheduled task to automate backups:

**Linux/Mac (crontab):**
```bash
# Daily backup at 2 AM
0 2 * * * curl -X POST "http://localhost:8081/backup/create?compress=true" -H "X-Admin-Key: your-admin-key"
```

**Windows (Task Scheduler):**
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute 'curl' -Argument '-X POST "http://localhost:8081/backup/create?compress=true" -H "X-Admin-Key: your-admin-key"'
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "DatabaseBackup" -Description "Daily database backup"
```

**Docker Compose with cron:**
```yaml
services:
  backup-cron:
    image: alpine:latest
    command: sh -c "echo '0 2 * * * curl -X POST http://app:8000/backup/create?compress=true -H \"X-Admin-Key: $$ADMIN_API_KEY\"' | crontab - && crond -f"
    environment:
      - ADMIN_API_KEY=${ADMIN_API_KEY}
    depends_on:
      - app
```

### Backup Rotation

Automatically delete old backups to save space:

```bash
#!/bin/bash
# Keep only last 7 days of backups

# Get list of backups
BACKUPS=$(curl -s -X GET "http://localhost:8081/backup/list" -H "X-Admin-Key: your-admin-key" | jq -r '.backups[].filename')

# Delete backups older than 7 days
for backup in $BACKUPS; do
  AGE=$(date -d "$(echo $backup | grep -oP '\d{8}_\d{6}')" +%s)
  NOW=$(date +%s)
  DIFF=$(( (NOW - AGE) / 86400 ))
  
  if [ $DIFF -gt 7 ]; then
    curl -X DELETE "http://localhost:8081/backup/delete/$backup" -H "X-Admin-Key: your-admin-key"
    echo "Deleted old backup: $backup"
  fi
done
```

---

## Usage Examples

### Complete Backup Workflow

```bash
# 1. Create backup
BACKUP=$(curl -s -X POST "http://localhost:8081/backup/create?compress=true" \
  -H "X-Admin-Key: your-admin-key" | jq -r '.filename')

echo "Created backup: $BACKUP"

# 2. Download backup
curl -X GET "http://localhost:8081/backup/download/$BACKUP" \
  -H "X-Admin-Key: your-admin-key" \
  -o "$BACKUP"

echo "Downloaded backup to: $BACKUP"

# 3. Upload to S3 (optional)
aws s3 cp "$BACKUP" "s3://my-backups/$BACKUP"

echo "Uploaded to S3"
```

### Restore Workflow

```bash
# 1. List available backups
curl -X GET "http://localhost:8081/backup/list" \
  -H "X-Admin-Key: your-admin-key" | jq

# 2. Choose a backup and restore
BACKUP="backup_postgresql_20241110_120000.sql.gz"

curl -X POST "http://localhost:8081/backup/restore/$BACKUP" \
  -H "X-Admin-Key: your-admin-key"

echo "Database restored from: $BACKUP"
```

### Restore from External Backup

```bash
# Download backup from S3
aws s3 cp "s3://my-backups/backup_postgresql_20241110_120000.sql.gz" ./backup.sql.gz

# Upload and restore
curl -X POST "http://localhost:8081/backup/restore-upload" \
  -H "X-Admin-Key: your-admin-key" \
  -F "file=@./backup.sql.gz"

echo "Database restored from external backup"
```

---

## Troubleshooting

### "Backup creation failed: pg_dump: command not found"

**Cause:** Database client tools not installed in container

**Fix:** Ensure your Dockerfile includes database client tools:

```dockerfile
# For PostgreSQL
RUN apt-get update && apt-get install -y postgresql-client

# For MySQL
RUN apt-get update && apt-get install -y mysql-client

# For both
RUN apt-get update && apt-get install -y postgresql-client mysql-client
```

### "Restore failed: Access denied"

**Cause:** Database user lacks necessary permissions

**Fix:** Ensure database user has CREATE, DROP, and INSERT permissions.

### "Backup file not found"

**Cause:** Backup directory not persistent or file deleted

**Fix:** Mount a volume for `/app/backups/` in docker-compose.yml

### "Unauthorized"

**Cause:** Missing or incorrect admin key

**Fix:** Include correct `X-Admin-Key` header in requests

---

## Production Recommendations

### 1. **Multiple Backup Locations**

Store backups in multiple locations:
- Local server (fast recovery)
- Cloud storage (disaster recovery)
- Off-site location (geographic redundancy)

### 2. **Backup Testing**

Regularly test restore procedures:
```bash
# Test restore in a separate database
docker compose -f docker-compose.test.yml up -d
curl -X POST "http://localhost:8082/backup/restore/$BACKUP" -H "X-Admin-Key: $KEY"
# Verify data integrity
```

### 3. **Monitoring**

Monitor backup success/failure:
- Log backup operations
- Alert on backup failures
- Track backup sizes and durations
- Verify backup integrity

### 4. **Encryption**

Encrypt backups for sensitive data:
```bash
# Encrypt backup
gpg --encrypt --recipient your@email.com backup.sql.gz

# Decrypt for restore
gpg --decrypt backup.sql.gz.gpg > backup.sql.gz
```

### 5. **Retention Policy**

Implement a backup retention policy:
- **Daily backups:** Keep 7 days
- **Weekly backups:** Keep 4 weeks
- **Monthly backups:** Keep 12 months
- **Yearly backups:** Keep indefinitely

---

## Comparison: API vs Manual Backups

| Aspect | API Backup | Manual Backup |
|--------|-----------|---------------|
| **Ease of use** | ✅ Simple HTTP requests | ❌ Requires shell access |
| **Automation** | ✅ Easy to automate | ⚠️ Requires cron/scripts |
| **Remote access** | ✅ Works from anywhere | ❌ Needs server access |
| **Security** | ✅ Admin key required | ⚠️ Depends on SSH setup |
| **Integration** | ✅ Easy to integrate | ❌ Harder to integrate |
| **Flexibility** | ⚠️ Predefined options | ✅ Full control |

---

## Summary

✅ **Complete backup solution** via API  
✅ **Create, download, restore** with simple HTTP requests  
✅ **Supports PostgreSQL, MySQL, SQLite**  
✅ **Automatic compression** with gzip  
✅ **Admin authentication** for security  
✅ **Easy automation** with cron or schedulers  
✅ **Production-ready** with best practices  

**Next steps:**
1. Set up admin key in `.env`
2. Test backup creation
3. Test restore procedure
4. Set up automated backups
5. Configure backup retention
6. Store backups in multiple locations

For more information:
- [Security Configuration](DATABASE_CREDENTIALS.md)
- [Database Guide](DATABASE.md)
- [API Documentation](http://localhost:8081/docs)
