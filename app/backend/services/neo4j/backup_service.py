"""Database backup and restore service for Neo4j."""
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
import gzip
import json
from neo4j import GraphDatabase
from api.settings import settings


class Neo4jBackupService:
    """Service for creating and restoring Neo4j database backups."""
    
    LOCK_TIMEOUT = 7200  # 2 hours in seconds
    
    def __init__(self):
        """Initialize Neo4j backup service with file-based tracking."""
        # Create data directory for locks and status files
        self.data_dir = Path(tempfile.gettempdir()) / "neo4j_backup"
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
        
    def create_backup_to_temp(self, compress: bool = True) -> Tuple[str, Path]:
        """
        Create a Neo4j database backup to a temporary file.
        
        This exports all nodes and relationships as Cypher CREATE statements
        to a temporary file that should be deleted after download.
        
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_neo4j_{timestamp}.cypher"
        if compress:
            filename += ".gz"
        
        # Create temporary file that won't be auto-deleted
        suffix = '.cypher.gz' if compress else '.cypher'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_filepath = Path(temp_file.name)
        temp_file.close()  # Close it so we can write to it properly
        
        try:
            # Connect to Neo4j
            driver = GraphDatabase.driver(
                settings.get_neo4j_uri(),
                auth=(settings.DB_USER, settings.get_db_password())
            )
            
            cypher_statements = []
            
            with driver.session() as session:
                # Export all nodes
                print("📦 Exporting nodes...")
                result = session.run("MATCH (n) RETURN n")
                for record in result:
                    node = record["n"]
                    labels = ":".join(node.labels)
                    props = dict(node.items())
                    
                    # Create Cypher CREATE statement
                    props_str = ", ".join([f"{k}: {self._format_value(v)}" for k, v in props.items()])
                    cypher = f"CREATE (:{labels} {{{props_str}}});"
                    cypher_statements.append(cypher)
                
                # Export all relationships
                print("📦 Exporting relationships...")
                result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN 
                        labels(a) as start_labels,
                        properties(a) as start_props,
                        type(r) as rel_type,
                        properties(r) as rel_props,
                        labels(b) as end_labels,
                        properties(b) as end_props
                """)
                
                for record in result:
                    start_labels = ":".join(record["start_labels"])
                    start_props = self._format_props(record["start_props"])
                    rel_type = record["rel_type"]
                    rel_props = self._format_props(record["rel_props"])
                    end_labels = ":".join(record["end_labels"])
                    end_props = self._format_props(record["end_props"])
                    
                    # Create Cypher MATCH + CREATE statement for relationship
                    cypher = (
                        f"MATCH (a:{start_labels} {start_props}), "
                        f"(b:{end_labels} {end_props}) "
                        f"CREATE (a)-[:{rel_type} {rel_props}]->(b);"
                    )
                    cypher_statements.append(cypher)
            
            driver.close()
            
            # Write to temporary file
            content = "\n".join(cypher_statements)
            
            if compress:
                with gzip.open(temp_filepath, 'wt', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(temp_filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            print(f"✅ Exported {len(cypher_statements)} statements to temporary file")
            return filename, temp_filepath
            
        except Exception as e:
            # Clean up temp file on error
            if temp_filepath.exists():
                temp_filepath.unlink()
            raise Exception(f"Neo4j backup failed: {str(e)}")
        finally:
            # Always release lock when done
            self._release_lock()
    
    def _format_value(self, value) -> str:
        """Format a value for Cypher.

        Properly escapes strings for Cypher syntax, handling quotes, backslashes,
        and control characters that would otherwise break the generated statements.
        """
        if isinstance(value, str):
            # Manually escape special characters for Cypher string literals
            # Order matters: escape backslashes first, then other characters
            escaped = value.replace('\\', '\\\\')  # Backslash must be first
            escaped = escaped.replace('"', '\\"')   # Escape double quotes
            escaped = escaped.replace('\n', '\\n')  # Escape newlines
            escaped = escaped.replace('\r', '\\r')  # Escape carriage returns
            escaped = escaped.replace('\t', '\\t')  # Escape tabs
            return f'"{escaped}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            formatted_items = [self._format_value(item) for item in value]
            return f"[{', '.join(formatted_items)}]"
        elif value is None:
            return 'null'
        else:
            return f'"{str(value)}"'
    
    def _format_props(self, props: dict) -> str:
        """Format properties dictionary for Cypher."""
        if not props:
            return ""
        
        props_str = ", ".join([f"{k}: {self._format_value(v)}" for k, v in props.items()])
        return f"{{{props_str}}}"
    
    def restore_backup(self, backup_file: Path):
        """
        Restore Neo4j database from backup file.
        
        ⚠️ WARNING: This will delete all existing data first!
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            List of warnings encountered during restore
            
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
        
        # Check if file is compressed
        is_compressed = backup_file.suffix == '.gz'
        
        try:
            # Initialize progress tracking
            self._update_restore_progress(
                status="in_progress",
                current=0,
                total=0,
                message="Reading backup file..."
            )
            
            # Read backup file
            if is_compressed:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    cypher_statements = f.read()
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    cypher_statements = f.read()
            
            # Connect to Neo4j
            driver = GraphDatabase.driver(
                settings.get_neo4j_uri(),
                auth=(settings.DB_USER, settings.get_db_password())
            )
            
            warnings = []
            max_warnings_to_collect = 100
            
            with driver.session() as session:
                # Clear existing data
                print("🗑️  Clearing existing data...")
                self._update_restore_progress(
                    status="in_progress",
                    message="Clearing existing database data..."
                )
                session.run("MATCH (n) DETACH DELETE n")
                
                # Execute each Cypher statement
                print("📥 Restoring data...")
                # Backups generated by create_backup_to_temp contain exactly
                # one Cypher statement per line (ending with ';'). Splitting
                # on lines avoids breaking statements that contain ';' inside
                # string literals (e.g. medication names).
                raw_lines = cypher_statements.splitlines()
                statements = []
                for line in raw_lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Remove the trailing CLI-style ';' terminator while
                    # leaving any semicolons inside string literals intact.
                    if line.endswith(';'):
                        line = line[:-1].strip()
                    if line:
                        statements.append(line)
                total = len(statements)
                
                self._update_restore_progress(
                    status="in_progress",
                    current=0,
                    total=total,
                    message=f"Restoring {total} statements..."
                )
                
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            session.run(statement)
                            if (i + 1) % 100 == 0:
                                print(f"   Executed {i + 1}/{total} statements...")
                                self._update_restore_progress(
                                    status="in_progress",
                                    current=i + 1,
                                    total=total,
                                    message=f"Executing statement {i + 1} of {total}...",
                                    warnings=warnings
                                )
                        except Exception as e:
                            warn_msg = f"Failed to execute statement {i + 1}/{total}: {e}"
                            print(f"   Warning: {warn_msg}")
                            
                            # Collect a limited number of warning details
                            if len(warnings) < max_warnings_to_collect:
                                snippet = statement.replace("\n", " ")
                                if len(snippet) > 200:
                                    snippet = snippet[:200] + "..."
                                warnings.append(f"{warn_msg} | Cypher: {snippet}")
                            # Continue with other statements
                
                print(f"✅ Executed {total} statements")
            
            driver.close()
            
            # Update final status
            self._update_restore_progress(
                status="completed",
                current=total,
                total=total,
                message=f"Restore completed. Executed {total} statements.",
                warnings=warnings
            )
            
            return warnings
            
        except Exception as e:
            # Update failed status
            self._update_restore_progress(
                status="failed",
                message=f"Restore failed: {str(e)}"
            )
            raise Exception(f"Neo4j restore failed: {str(e)}")
        finally:
            # Always release lock and clean up temp file when done
            self._release_lock()
            if backup_file.exists():
                try:
                    backup_file.unlink()
                except Exception as e:
                    print(f"Warning: Failed to clean up temp file: {e}")
    
    def get_database_stats(self) -> dict:
        """
        Get current database statistics.
        
        Returns:
            Dictionary with node and relationship counts
        """
        try:
            driver = GraphDatabase.driver(
                settings.get_neo4j_uri(),
                auth=(settings.DB_USER, settings.get_db_password())
            )
            
            with driver.session() as session:
                # Count nodes
                node_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_result.single()["count"]
                
                # Count relationships
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_result.single()["count"]
                
                # Get node labels
                labels_result = session.run("CALL db.labels()")
                labels = [record["label"] for record in labels_result]
                
                # Get relationship types
                types_result = session.run("CALL db.relationshipTypes()")
                rel_types = [record["relationshipType"] for record in types_result]
            
            driver.close()
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "labels": labels,
                "relationship_types": rel_types
            }
            
        except Exception as e:
            raise Exception(f"Failed to get database stats: {str(e)}")
