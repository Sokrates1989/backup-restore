# Configuration using pydantic-settings
from pydantic_settings import BaseSettings
from typing import Literal, Optional
from pathlib import Path


class Settings(BaseSettings):
    # API Settings
    PORT: int = 8000
    IMAGE_TAG: str = "local non docker"
    DEBUG: bool = False
    
    # Security Settings - Tiered API Keys
    ADMIN_API_KEY: str = ""  # Level 1: Read-only admin operations
    ADMIN_API_KEY_FILE: str = ""  # Path to file containing admin API key
    BACKUP_RESTORE_API_KEY: str = ""  # Level 2: Restore operations (destructive)
    BACKUP_RESTORE_API_KEY_FILE: str = ""  # Path to file containing restore API key
    BACKUP_DELETE_API_KEY: str = ""  # Level 3: Delete operations (destructive)
    BACKUP_DELETE_API_KEY_FILE: str = ""  # Path to file containing delete API key

    CONFIG_ENCRYPTION_KEY: str = ""  # Symmetric key for encrypting stored destination/target secrets
    CONFIG_ENCRYPTION_KEY_FILE: str = ""  # Path to file containing config encryption key
    
    # Database Type Configuration
    DB_TYPE: Literal["neo4j", "postgresql", "mysql", "sqlite"] = "neo4j"
    DB_MODE: Literal["local", "standalone"] = "local"

    # Neo4j Configuration
    NEO4J_URL: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_PASSWORD_FILE: str = ""  # Path to file containing DB password
    
    # SQL Database Configuration
    DATABASE_URL: str = ""  # Full connection string (for external databases)
    DB_HOST: str = "localhost"
    DB_NAME: str = ""
    DB_PORT: int = 5432

    class Config:
        env_file = ".env"
    
    def get_admin_api_key(self) -> str:
        """Get admin API key from file or environment variable"""
        if self.ADMIN_API_KEY_FILE and Path(self.ADMIN_API_KEY_FILE).exists():
            return Path(self.ADMIN_API_KEY_FILE).read_text().strip()
        return self.ADMIN_API_KEY
    
    def get_restore_api_key(self) -> str:
        """Get restore API key from file or environment variable"""
        if self.BACKUP_RESTORE_API_KEY_FILE and Path(self.BACKUP_RESTORE_API_KEY_FILE).exists():
            return Path(self.BACKUP_RESTORE_API_KEY_FILE).read_text().strip()
        return self.BACKUP_RESTORE_API_KEY
    
    def get_delete_api_key(self) -> str:
        """Get delete API key from file or environment variable"""
        if self.BACKUP_DELETE_API_KEY_FILE and Path(self.BACKUP_DELETE_API_KEY_FILE).exists():
            return Path(self.BACKUP_DELETE_API_KEY_FILE).read_text().strip()
        return self.BACKUP_DELETE_API_KEY

    def get_config_encryption_key(self) -> str:
        """Get config encryption key from file or environment variable."""
        if self.CONFIG_ENCRYPTION_KEY_FILE and Path(self.CONFIG_ENCRYPTION_KEY_FILE).exists():
            return Path(self.CONFIG_ENCRYPTION_KEY_FILE).read_text().strip()
        return self.CONFIG_ENCRYPTION_KEY
    
    def get_db_password(self) -> str:
        """Get database password from file or environment variable"""
        if self.DB_PASSWORD_FILE and Path(self.DB_PASSWORD_FILE).exists():
            return Path(self.DB_PASSWORD_FILE).read_text().strip()
        return self.DB_PASSWORD
    
    def get_neo4j_uri(self) -> str:
        """Resolve Neo4j Bolt URI, preferring explicit NEO4J_URL when set."""
        if self.NEO4J_URL:
            return self.NEO4J_URL
        return f"bolt://{self.DB_HOST}:{self.DB_PORT}"
    
    def get_database_url(self) -> str:
        """Build database URL for SQL databases"""
        if self.DATABASE_URL:
            # Use provided URL (for external databases)
            return self.DATABASE_URL
        
        # Build URL from components (for local databases)
        password = self.get_db_password()
        if self.DB_TYPE == "postgresql":
            return f"postgresql://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        elif self.DB_TYPE == "mysql":
            return f"mysql://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        elif self.DB_TYPE == "sqlite":
            return f"sqlite:///{self.DB_NAME}"
        return ""


settings = Settings()