# Database Backups Directory

This directory stores database backup files created via the API.

## Automatic Backups

Backups are stored here when created via:
```bash
POST /backup/create
```

## Backup Files

Backup files are named with timestamps:
- PostgreSQL: `backup_postgresql_YYYYMMDD_HHMMSS.sql[.gz]`
- MySQL: `backup_mysql_YYYYMMDD_HHMMSS.sql[.gz]`
- SQLite: `backup_sqlite_YYYYMMDD_HHMMSS.db[.gz]`

## Persistence

To persist backups across container restarts, mount this directory as a volume:

```yaml
# docker-compose.yml
services:
  app:
    volumes:
      - ./backups:/app/backups
```

## Security

⚠️ **Important:** This directory contains sensitive database backups!

- Add to `.gitignore` (already done)
- Restrict file permissions
- Store in secure locations
- Encrypt for sensitive data

## See Also

- [Database Backup Guide](../docs/DATABASE_BACKUP.md)
- [API Documentation](http://localhost:8081/docs#/Database%20Backup)
