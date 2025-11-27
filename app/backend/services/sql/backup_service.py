"""Database backup and restore service for SQL databases."""
import subprocess
import os
import tempfile
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import gzip
import shutil
from api.settings import settings


class BackupService:
    """Service for creating and restoring database backups."""
    
    LOCK_TIMEOUT = 7200  # 2 hours in seconds
    
    def __init__(self):
        """Initialize backup service with file-based tracking."""
        # Create data directory for locks and status files
        self.data_dir = Path(tempfile.gettempdir()) / "sql_backup"
        self.data_dir.mkdir(exist_ok=True)
        
        self.lock_file = self.data_dir / "operation.lock"
        self.status_file = self.data_dir / "restore_status.json"
        self.warnings_file = self.data_dir / "restore_warnings.json"

    def _acquire_lock(self, operation: str) -> bool:
        """Acquire operation lock to prevent concurrent operations."""
        try:
            if self.lock_file.exists():
                lock_data = json.loads(self.lock_file.read_text())
                lock_time = lock_data.get("timestamp", 0)
                if time.time() - lock_time < self.LOCK_TIMEOUT:
                    return False
            lock_data = {"operation": operation, "timestamp": time.time()}
            self.lock_file.write_text(json.dumps(lock_data))
            return True
        except Exception as e:
            print(f"Warning: Failed to acquire lock: {e}")
            return True

    def _release_lock(self):
        """Release the operation lock."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to release lock: {e}")

    def _update_restore_progress(
        self, status: str, current: int = 0, total: int = 0,
        message: str = "", warnings: list = None
    ):
        """Update restore operation progress to file."""
        try:
            progress_data = {
                "status": status, "current": current, "total": total,
                "message": message,
                "warnings_count": len(warnings) if warnings else 0,
                "timestamp": datetime.now().isoformat()
            }
            self.status_file.write_text(json.dumps(progress_data, indent=2))
            if warnings:
                self.warnings_file.write_text(json.dumps(warnings, indent=2))
        except Exception as e:
            print(f"Warning: Failed to update progress: {e}")

    def get_restore_status(self) -> Optional[Dict]:
        """Get current restore operation status."""
        try:
            if not self.status_file.exists():
                return None
            status_data = json.loads(self.status_file.read_text())
            if self.warnings_file.exists():
                status_data["warnings"] = json.loads(self.warnings_file.read_text())
            lock_operation = self.check_operation_lock()
            status_data["is_locked"] = bool(lock_operation)
            status_data["lock_operation"] = lock_operation
            return status_data
        except Exception as e:
            print(f"Warning: Failed to get restore status: {e}")
            return None

    def check_operation_lock(self) -> Optional[str]:
        """Check if there's an active operation lock."""
        try:
            if not self.lock_file.exists():
                return None
            lock_data = json.loads(self.lock_file.read_text())
            lock_time = lock_data.get("timestamp", 0)
            if time.time() - lock_time >= self.LOCK_TIMEOUT:
                self.lock_file.unlink()
                return None
            return lock_data.get("operation")
        except Exception as e:
            print(f"Warning: Failed to check lock: {e}")
            return None
        
    def create_backup_to_temp(self, compress: bool = True) -> tuple[str, Path]:
        """
        Create a database backup to a temporary file.
        
        Args:
            compress: Whether to compress the backup with gzip
            
        Returns:
            Tuple of (filename, temp_filepath)
            
        Raises:
            Exception: If backup creation fails or operation is locked
        """
        # Check if another operation is in progress
        lock_operation = self.check_operation_lock()
        if lock_operation:
            raise Exception(f"Cannot create backup: {lock_operation} operation is in progress")
        
        # Acquire lock for backup operation
        if not self._acquire_lock("backup"):
            raise Exception("Failed to acquire lock for backup operation")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_type = settings.DB_TYPE.lower()
            
            if db_type in ["postgresql", "postgres"]:
                return self._backup_postgresql(timestamp, compress)
            elif db_type == "mysql":
                return self._backup_mysql(timestamp, compress)
            elif db_type == "sqlite":
                return self._backup_sqlite(timestamp, compress)
            else:
                raise ValueError(f"Backup not supported for database type: {db_type}")
        finally:
            # Always release lock when done
            self._release_lock()
    
    def _backup_postgresql(self, timestamp: str, compress: bool) -> tuple[str, Path]:
        """Create PostgreSQL backup using pg_dump."""
        filename = f"backup_postgresql_{timestamp}.sql"
        if compress:
            filename += ".gz"
        
        # Create temporary file
        suffix = '.sql.gz' if compress else '.sql'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        filepath = Path(temp_file.name)
        temp_file.close()
        
        # Build pg_dump command
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.get_db_password()
        
        cmd = [
            'pg_dump',
            '-h', settings.DB_HOST,
            '-p', str(settings.DB_PORT),
            '-U', settings.DB_USER,
            '-d', settings.DB_NAME,
            '--no-owner',  # Don't include ownership commands
            '--no-acl',    # Don't include access privileges
            '-F', 'p',     # Plain text format
        ]
        
        try:
            # Run pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                check=True,
                text=True
            )
            
            # Write output
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(result.stdout)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
            
            return filename, filepath
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"PostgreSQL backup failed: {e.stderr}")
    
    def _backup_mysql(self, timestamp: str, compress: bool) -> tuple[str, Path]:
        """Create MySQL backup using mariadb-dump (MySQL-compatible)."""
        filename = f"backup_mysql_{timestamp}.sql"
        if compress:
            filename += ".gz"
        
        # Create temporary file
        suffix = '.sql.gz' if compress else '.sql'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        filepath = Path(temp_file.name)
        temp_file.close()
        
        # Try mariadb-dump first (newer), fall back to mysqldump
        dump_cmd = 'mariadb-dump' if shutil.which('mariadb-dump') else 'mysqldump'
        
        cmd = [
            dump_cmd,
            '-h', settings.DB_HOST,
            '-P', str(settings.DB_PORT),
            '-u', settings.DB_USER,
            f'-p{settings.get_db_password()}',
            settings.DB_NAME,
            '--single-transaction',  # Consistent backup
            '--skip-lock-tables',    # Don't lock tables
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True
            )
            
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(result.stdout)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
            
            return filename, filepath
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"MySQL backup failed: {e.stderr}")
    
    def _backup_sqlite(self, timestamp: str, compress: bool) -> tuple[str, Path]:
        """Create SQLite backup by copying the database file."""
        filename = f"backup_sqlite_{timestamp}.db"
        if compress:
            filename += ".gz"
        
        # Create temporary file
        suffix = '.db.gz' if compress else '.db'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        filepath = Path(temp_file.name)
        temp_file.close()
        
        # SQLite database is a file, just copy it
        db_file = Path(settings.DB_NAME)
        
        if not db_file.exists():
            raise Exception(f"SQLite database file not found: {db_file}")
        
        try:
            if compress:
                with open(db_file, 'rb') as f_in:
                    with gzip.open(filepath, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(db_file, filepath)
            
            return filename, filepath
            
        except Exception as e:
            raise Exception(f"SQLite backup failed: {str(e)}")
    
    def restore_backup(self, backup_file: Path) -> dict:
        """
        Restore database from backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            dict: Information about the restore operation including warnings
            
        Raises:
            Exception: If restore fails or operation is locked
        """
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        # Check if another operation is in progress
        lock_operation = self.check_operation_lock()
        if lock_operation:
            raise Exception(f"Cannot restore: {lock_operation} operation is in progress")
        
        # Acquire lock for restore operation
        if not self._acquire_lock("restore"):
            raise Exception("Failed to acquire lock for restore operation")
        
        db_type = settings.DB_TYPE.lower()
        warnings = []
        
        try:
            # Initialize progress tracking
            self._update_restore_progress(
                status="in_progress",
                message="Starting restore operation...",
                warnings=warnings
            )
            
            # Check if file is compressed
            is_compressed = backup_file.suffix == '.gz'
            
            # Drop existing database data before restore
            try:
                self._update_restore_progress(
                    status="in_progress",
                    message="Dropping existing database data...",
                    warnings=warnings
                )
                self._drop_database()
            except Exception as e:
                raise Exception(f"Failed to drop existing database: {str(e)}")
            
            # Restore from backup
            self._update_restore_progress(
                status="in_progress",
                message=f"Restoring {db_type} database from backup...",
                warnings=warnings
            )
            
            if db_type in ["postgresql", "postgres"]:
                self._restore_postgresql(backup_file, is_compressed)
            elif db_type == "mysql":
                self._restore_mysql(backup_file, is_compressed)
            elif db_type == "sqlite":
                self._restore_sqlite(backup_file, is_compressed)
            else:
                raise ValueError(f"Restore not supported for database type: {db_type}")
            
            # Update final status
            self._update_restore_progress(
                status="completed",
                message="Restore completed successfully",
                warnings=warnings
            )
            
            return {
                "warnings": warnings,
                "warning_count": len(warnings)
            }
            
        except Exception as e:
            # Update failed status
            self._update_restore_progress(
                status="failed",
                message=f"Restore failed: {str(e)}",
                warnings=warnings
            )
            raise
        finally:
            # Always release lock and clean up temp file when done
            self._release_lock()
            if backup_file.exists():
                try:
                    backup_file.unlink()
                except Exception as e:
                    print(f"Warning: Failed to clean up temp file: {e}")
    
    def _restore_postgresql(self, backup_file: Path, is_compressed: bool) -> None:
        """Restore PostgreSQL database using psql."""
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.get_db_password()
        
        cmd = [
            'psql',
            '-h', settings.DB_HOST,
            '-p', str(settings.DB_PORT),
            '-U', settings.DB_USER,
            '-d', settings.DB_NAME,
        ]
        
        try:
            # Read backup file
            if is_compressed:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    sql_content = f.read()
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            
            # Execute SQL
            result = subprocess.run(
                cmd,
                env=env,
                input=sql_content,
                capture_output=True,
                check=True,
                text=True
            )
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"PostgreSQL restore failed: {e.stderr}")
    
    def _restore_mysql(self, backup_file: Path, is_compressed: bool) -> None:
        """Restore MySQL database using mariadb (MySQL-compatible)."""
        # Try mariadb first (newer), fall back to mysql
        mysql_cmd = 'mariadb' if shutil.which('mariadb') else 'mysql'
        
        cmd = [
            mysql_cmd,
            '-h', settings.DB_HOST,
            '-P', str(settings.DB_PORT),
            '-u', settings.DB_USER,
            f'-p{settings.get_db_password()}',
            settings.DB_NAME,
        ]
        
        try:
            if is_compressed:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    sql_content = f.read()
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            
            result = subprocess.run(
                cmd,
                input=sql_content,
                capture_output=True,
                check=True,
                text=True
            )
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"MySQL restore failed: {e.stderr}")
    
    def _restore_sqlite(self, backup_file: Path, is_compressed: bool) -> None:
        """Restore SQLite database by replacing the database file."""
        db_file = Path(settings.DB_NAME)
        
        # Backup current database before replacing
        if db_file.exists():
            backup_current = db_file.with_suffix('.db.backup')
            shutil.copy2(db_file, backup_current)
        
        try:
            if is_compressed:
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(db_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_file, db_file)
                
        except Exception as e:
            # Restore original if restore failed
            if db_file.exists():
                backup_current = db_file.with_suffix('.db.backup')
                if backup_current.exists():
                    shutil.copy2(backup_current, db_file)
            raise Exception(f"SQLite restore failed: {str(e)}")
    
    def _drop_database(self) -> None:
        """
        Drop all tables/data from the database before restore.
        
        This ensures a clean restore without conflicts from existing data.
        """
        db_type = settings.DB_TYPE.lower()
        
        if db_type in ["postgresql", "postgres"]:
            self._drop_postgresql_tables()
        elif db_type == "mysql":
            self._drop_mysql_tables()
        elif db_type == "sqlite":
            self._drop_sqlite_tables()
    
    def _drop_postgresql_tables(self) -> None:
        """Drop all tables in PostgreSQL database."""
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.get_db_password()
        
        # Drop all tables using CASCADE
        drop_sql = """
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
        """
        
        cmd = [
            'psql',
            '-h', settings.DB_HOST,
            '-p', str(settings.DB_PORT),
            '-U', settings.DB_USER,
            '-d', settings.DB_NAME,
        ]
        
        try:
            subprocess.run(
                cmd,
                env=env,
                input=drop_sql,
                capture_output=True,
                check=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to drop PostgreSQL tables: {e.stderr}")
    
    def _drop_mysql_tables(self) -> None:
        """Drop all tables in MySQL database."""
        env = os.environ.copy()
        env['MYSQL_PWD'] = settings.get_db_password()
        
        # Get list of tables and drop them
        drop_sql = f"""
        SET FOREIGN_KEY_CHECKS = 0;
        SET @tables = NULL;
        SELECT GROUP_CONCAT(table_name) INTO @tables
        FROM information_schema.tables
        WHERE table_schema = '{settings.DB_NAME}';
        SET @tables = CONCAT('DROP TABLE IF EXISTS ', @tables);
        PREPARE stmt FROM @tables;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SET FOREIGN_KEY_CHECKS = 1;
        """
        
        # Try mariadb first, fallback to mysql
        cmd = None
        for mysql_cmd in ['mariadb', 'mysql']:
            if shutil.which(mysql_cmd):
                cmd = [
                    mysql_cmd,
                    '-h', settings.DB_HOST,
                    '-P', str(settings.DB_PORT),
                    '-u', settings.DB_USER,
                    settings.DB_NAME,
                ]
                break
        
        if not cmd:
            raise Exception("Neither mariadb nor mysql command found")
        
        try:
            subprocess.run(
                cmd,
                env=env,
                input=drop_sql,
                capture_output=True,
                check=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to drop MySQL tables: {e.stderr}")
    
    def _drop_sqlite_tables(self) -> None:
        """Drop all tables in SQLite database."""
        import sqlite3
        
        db_file = Path(settings.DB_NAME)
        if not db_file.exists():
            return  # Nothing to drop
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Drop each table
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]};")
            
            conn.commit()
            conn.close()
        except Exception as e:
            raise Exception(f"Failed to drop SQLite tables: {str(e)}")
    
