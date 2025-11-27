"""Alembic environment configuration for database migrations."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Import your models' Base (from SQL models directory)
from models.sql.example import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

def get_url():
    """Get database URL from environment variables."""
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv()
    
    db_type = os.getenv("DB_TYPE", "postgresql")
    
    if db_type in ["postgresql", "postgres"]:
        # Use asyncpg URL but convert to sync for Alembic
        database_url = os.getenv("DATABASE_URL", "")
        
        # If DATABASE_URL is not set, construct it from components
        if not database_url:
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "")
            db_user = os.getenv("DB_USER", "")
            
            # Get password from file or environment variable
            db_password_file = os.getenv("DB_PASSWORD_FILE", "")
            if db_password_file and Path(db_password_file).exists():
                db_password = Path(db_password_file).read_text().strip()
            else:
                db_password = os.getenv("DB_PASSWORD", "")
            
            if not all([db_host, db_name, db_user, db_password]):
                raise ValueError(
                    f"Missing database configuration. Either set DATABASE_URL or provide "
                    f"DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD/DB_PASSWORD_FILE. "
                    f"Current values: DB_HOST={db_host}, DB_NAME={db_name}, DB_USER={db_user}"
                )
            
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Convert asyncpg to psycopg2 for Alembic (sync driver)
        if "asyncpg" in database_url:
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        return database_url
    else:
        raise ValueError(f"Alembic migrations only supported for PostgreSQL. Current DB_TYPE: {db_type}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
