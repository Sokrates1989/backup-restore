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
import sqlite3

import psycopg2
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

    def _looks_like_gzip(self, path: Path) -> bool:
        """Return True when the file appears to be gzip-compressed.

        Args:
            path: File path.

        Returns:
            bool: True if the file starts with the gzip magic bytes.
        """

        try:
            with open(path, "rb") as f:
                return f.read(2) == b"\x1f\x8b"
        except Exception:
            return False
        
    def create_backup_to_temp(
        self,
        db_type: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        compress: bool = True
    ) -> tuple[str, Path]:
        """
        Create a database backup to a temporary file.
        
        Args:
            db_type: Database type (postgresql, mysql, sqlite)
            db_host: Database host
            db_port: Database port
            db_name: Database name
            db_user: Database username
            db_password: Database password
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
            db_type_lower = db_type.lower()
            
            if db_type_lower in ["postgresql", "postgres"]:
                return self._backup_postgresql(timestamp, compress, db_host, db_port, db_name, db_user, db_password)
            elif db_type_lower == "mysql":
                return self._backup_mysql(timestamp, compress, db_host, db_port, db_name, db_user, db_password)
            elif db_type_lower == "sqlite":
                return self._backup_sqlite(timestamp, compress, db_name)
            else:
                raise ValueError(f"Backup not supported for database type: {db_type}")
        finally:
            # Always release lock when done
            self._release_lock()
    
    def _backup_postgresql(self, timestamp: str, compress: bool, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> tuple[str, Path]:
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
        env['PGPASSWORD'] = db_password
        
        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
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
    
    def _backup_mysql(self, timestamp: str, compress: bool, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> tuple[str, Path]:
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
            '-h', db_host,
            '-P', str(db_port),
            '-u', db_user,
            db_name,
            '--single-transaction',  # Consistent backup
            '--skip-lock-tables',    # Don't lock tables
        ]

        env = os.environ.copy()
        env["MYSQL_PWD"] = db_password

        def _ssl_disabled_args() -> list[str]:
            if dump_cmd.startswith("mariadb"):
                return ["--skip-ssl"]
            return ["--ssl-mode=DISABLED"]

        def _should_allow_insecure_ssl() -> bool:
            try:
                from api.settings import settings

                return bool(getattr(settings, "DEBUG", False) or getattr(settings, "ALLOW_INSECURE_MYSQL_SSL", False))
            except Exception:
                return False

        def _looks_like_tls_error(stderr: str) -> bool:
            low = str(stderr or "").lower()
            return "tls/ssl error" in low or "self-signed" in low or "certificate" in low
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, check=True, text=True)
            
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(result.stdout)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
            
            return filename, filepath
            
        except subprocess.CalledProcessError as e:
            if _should_allow_insecure_ssl() and _looks_like_tls_error(e.stderr):
                try:
                    retry_cmd = cmd + _ssl_disabled_args()
                    result = subprocess.run(retry_cmd, env=env, capture_output=True, check=True, text=True)

                    if compress:
                        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                            f.write(result.stdout)
                    else:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(result.stdout)

                    return filename, filepath
                except subprocess.CalledProcessError:
                    pass

            raise Exception(f"MySQL backup failed: {e.stderr}")
    
    def _backup_sqlite(self, timestamp: str, compress: bool, db_name: str) -> tuple[str, Path]:
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
        db_file = Path(db_name)
        
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
    
    def get_database_stats(
        self,
        db_type: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str
    ) -> Dict:
        """Collect high-level statistics for the specified database."""
        db_type_lower = db_type.lower()

        if db_type_lower in ["postgresql", "postgres"]:
            return self._get_postgresql_stats(db_host, db_port, db_name, db_user, db_password)
        if db_type_lower == "mysql":
            return self._get_mysql_stats(db_host, db_port, db_name, db_user, db_password)
        if db_type_lower == "sqlite":
            return self._get_sqlite_stats(db_name)

        raise ValueError(f"Database stats not supported for database type: {db_type}")

    def _get_postgresql_stats(self, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> Dict:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        relname AS table_name,
                        COALESCE(n_live_tup, 0)::bigint AS row_estimate,
                        pg_total_relation_size(relid) AS total_bytes
                    FROM pg_stat_user_tables
                    ORDER BY relname;
                    """
                )
                table_rows = cur.fetchall()

                tables = []
                total_rows = 0
                total_table_bytes = 0
                for table_name, row_estimate, total_bytes in table_rows:
                    row_count = int(row_estimate)
                    tables.append({
                        "name": table_name,
                        "row_count": row_count,
                        "size_mb": round(total_bytes / (1024 * 1024), 2)
                    })
                    total_rows += row_count
                    total_table_bytes += total_bytes

                cur.execute("SELECT pg_database_size(%s)", (db_name,))
                database_size_bytes = cur.fetchone()[0]

            return {
                "table_count": len(tables),
                "total_rows": total_rows,
                "database_size_mb": round(database_size_bytes / (1024 * 1024), 2),
                "tables": tables,
            }
        finally:
            conn.close()

    def _get_mysql_stats(self, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> Dict:
        mysql_cmd = None
        for candidate in ["mysql", "mariadb"]:
            if shutil.which(candidate):
                mysql_cmd = candidate
                break

        if not mysql_cmd:
            raise Exception("MySQL client (mysql or mariadb) not found on system")

        escaped_db = db_name.replace("'", "''")
        query = (
            "SELECT table_name, IFNULL(table_rows, 0) AS rows, "
            "IFNULL(data_length + index_length, 0) AS total_bytes "
            "FROM information_schema.tables "
            f"WHERE table_schema = '{escaped_db}';"
        )

        cmd = [
            mysql_cmd,
            '-h', db_host,
            '-P', str(db_port),
            '-u', db_user,
            f'-p{db_password}',
            '--batch',
            '--raw',
            '--silent',
            '-N',
            '-e', query,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"MySQL stats query failed: {result.stderr.strip()}")

        tables = []
        total_rows = 0
        total_bytes = 0
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            name, rows_str, bytes_str = parts[:3]
            try:
                row_count = int(float(rows_str))
            except ValueError:
                row_count = 0
            try:
                size_bytes = int(float(bytes_str))
            except ValueError:
                size_bytes = 0

            tables.append({
                "name": name,
                "row_count": row_count,
                "size_mb": round(size_bytes / (1024 * 1024), 2)
            })
            total_rows += row_count
            total_bytes += size_bytes

        return {
            "table_count": len(tables),
            "total_rows": total_rows,
            "database_size_mb": round(total_bytes / (1024 * 1024), 2),
            "tables": tables,
        }

    def _get_sqlite_stats(self, db_name: str) -> Dict:
        db_path = Path(db_name)
        if not db_path.exists():
            raise Exception(f"SQLite database file not found: {db_path}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            table_names = [row[0] for row in cursor.fetchall()]

            tables = []
            total_rows = 0
            for table_name in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                row_count = cursor.fetchone()[0]
                total_rows += row_count
                tables.append({
                    "name": table_name,
                    "row_count": row_count,
                })
        finally:
            conn.close()

        size_bytes = db_path.stat().st_size if db_path.exists() else 0
        return {
            "table_count": len(tables),
            "total_rows": total_rows,
            "database_size_mb": round(size_bytes / (1024 * 1024), 2),
            "tables": tables,
        }

    
    def restore_backup(
        self,
        backup_file: Path,
        db_type: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        target_api_url: str = None,
        target_api_key: str = None
    ) -> dict:
        """
        Restore database from backup file.
        
        Args:
            backup_file: Path to backup file
            db_type: Database type (postgresql, mysql, sqlite)
            db_host: Database host
            db_port: Database port
            db_name: Database name
            db_user: Database username
            db_password: Database password
            target_api_url: Optional URL of target API to unlock after restore
            target_api_key: Optional API key for target API unlock endpoint
            
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
        
        db_type_lower = db_type.lower()
        warnings = []
        
        try:
            # Initialize progress tracking
            self._update_restore_progress(
                status="in_progress",
                message="Starting restore operation...",
                warnings=warnings
            )
            
            # Check if file is compressed.
            # Some providers (e.g. Google Drive) restore by file-id and the temp file
            # may not preserve the original .gz suffix.
            is_compressed = backup_file.suffix == '.gz' or self._looks_like_gzip(backup_file)
            
            # Drop existing database data before restore
            try:
                self._update_restore_progress(
                    status="in_progress",
                    message="Dropping existing database data...",
                    warnings=warnings
                )
                self._drop_database(db_type_lower, db_host, db_port, db_name, db_user, db_password)
            except Exception as e:
                raise Exception(f"Failed to drop existing database: {str(e)}")
            
            # Restore from backup
            self._update_restore_progress(
                status="in_progress",
                message=f"Restoring {db_type_lower} database from backup...",
                warnings=warnings
            )
            
            if db_type_lower in ["postgresql", "postgres"]:
                self._restore_postgresql(backup_file, is_compressed, db_host, db_port, db_name, db_user, db_password)
            elif db_type_lower == "mysql":
                self._restore_mysql(backup_file, is_compressed, db_host, db_port, db_name, db_user, db_password)
            elif db_type_lower == "sqlite":
                self._restore_sqlite(backup_file, is_compressed, db_name)
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
            
            # Unlock target API if it was provided
            if target_api_url and target_api_key:
                try:
                    import httpx
                    with httpx.Client(timeout=10.0) as client:
                        client.post(
                            f"{target_api_url}/database/unlock",
                            headers={"X-Admin-Key": target_api_key},
                        )
                    print(f"✅ Unlocked target API: {target_api_url}")
                except Exception as e:
                    print(f"Warning: Failed to unlock target API: {e}")
    
    def _restore_postgresql(self, backup_file: Path, is_compressed: bool, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> None:
        """Restore PostgreSQL database using psql."""
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        cmd = [
            'psql',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
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
    
    def _restore_mysql(self, backup_file: Path, is_compressed: bool, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> None:
        """Restore MySQL database using mariadb (MySQL-compatible)."""
        # Try mariadb first (newer), fall back to mysql
        mysql_cmd = 'mariadb' if shutil.which('mariadb') else 'mysql'
        
        cmd = [
            mysql_cmd,
            '-h', db_host,
            '-P', str(db_port),
            '-u', db_user,
            db_name,
        ]

        env = os.environ.copy()
        env["MYSQL_PWD"] = db_password

        def _ssl_disabled_args() -> list[str]:
            if mysql_cmd.startswith("mariadb"):
                return ["--skip-ssl"]
            return ["--ssl-mode=DISABLED"]

        def _should_allow_insecure_ssl() -> bool:
            try:
                from api.settings import settings

                return bool(getattr(settings, "DEBUG", False) or getattr(settings, "ALLOW_INSECURE_MYSQL_SSL", False))
            except Exception:
                return False

        def _looks_like_tls_error(stderr: str) -> bool:
            low = str(stderr or "").lower()
            return "tls/ssl error" in low or "self-signed" in low or "certificate" in low
        
        try:
            if is_compressed:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    sql_content = f.read()
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            
            subprocess.run(cmd, env=env, input=sql_content, capture_output=True, check=True, text=True)
            
        except subprocess.CalledProcessError as e:
            if _should_allow_insecure_ssl() and _looks_like_tls_error(e.stderr):
                try:
                    retry_cmd = cmd + _ssl_disabled_args()
                    subprocess.run(retry_cmd, env=env, input=sql_content, capture_output=True, check=True, text=True)
                    return
                except subprocess.CalledProcessError:
                    pass

            raise Exception(f"MySQL restore failed: {e.stderr}")
    
    def _restore_sqlite(self, backup_file: Path, is_compressed: bool, db_name: str) -> None:
        """Restore SQLite database by replacing the database file."""
        db_file = Path(db_name)
        
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
    
    def _drop_database(self, db_type: str, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> None:
        """
        Drop all tables/data from the database before restore.
        
        This ensures a clean restore without conflicts from existing data.
        """
        db_type_lower = db_type.lower()
        
        if db_type_lower in ["postgresql", "postgres"]:
            self._drop_postgresql_tables(db_host, db_port, db_name, db_user, db_password)
        elif db_type_lower == "mysql":
            self._drop_mysql_tables(db_host, db_port, db_name, db_user, db_password)
        elif db_type_lower == "sqlite":
            self._drop_sqlite_tables(db_name)
    
    def _drop_postgresql_tables(self, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> None:
        """Drop all tables in PostgreSQL database."""
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
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
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
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
    
    def _drop_mysql_tables(self, db_host: str, db_port: int, db_name: str, db_user: str, db_password: str) -> None:
        """Drop all tables in MySQL database."""
        env = os.environ.copy()
        env['MYSQL_PWD'] = db_password
        
        # Get list of tables and drop them
        drop_sql = f"""
        SET FOREIGN_KEY_CHECKS = 0;
        SET @tables = NULL;
        SELECT GROUP_CONCAT(CONCAT('`', REPLACE(table_name, '`', '``'), '`')) INTO @tables
        FROM information_schema.tables
        WHERE table_schema = '{db_name}'
          AND table_type = 'BASE TABLE';

        SET @tables = IF(
            @tables IS NULL OR @tables = '',
            'SELECT 1',
            CONCAT('DROP TABLE IF EXISTS ', @tables)
        );
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
                    '-h', db_host,
                    '-P', str(db_port),
                    '-u', db_user,
                    db_name,
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
    
    def _drop_sqlite_tables(self, db_name: str) -> None:
        """Drop all tables in SQLite database."""
        import sqlite3
        
        db_file = Path(db_name)
        if not db_file.exists():
            return  # Nothing to drop
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            def _quote_identifier(identifier: str) -> str:
                """Quote a SQLite identifier.

                Args:
                    identifier: Table/view/trigger name.

                Returns:
                    str: Safely quoted identifier.
                """

                return '"' + str(identifier).replace('"', '""') + '"'

            cursor.execute("PRAGMA foreign_keys=OFF;")

            # Drop objects in a safe order. Also skip internal SQLite tables.
            for obj_type in ("view", "trigger", "table"):
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%';",
                    (obj_type,),
                )
                objects = cursor.fetchall()
                for (name,) in objects:
                    cursor.execute(f"DROP {obj_type.upper()} IF EXISTS {_quote_identifier(name)};")

            # Reset autoincrement counters when the sqlite_sequence table exists.
            try:
                cursor.execute("DELETE FROM sqlite_sequence;")
            except sqlite3.OperationalError:
                pass

            conn.commit()
            conn.close()
        except Exception as e:
            raise Exception(f"Failed to drop SQLite tables: {str(e)}")
    
