"""Shared SQLAlchemy declarative base for all SQL models.

All SQLAlchemy ORM models in this project must import and use this Base so Alembic
can correctly discover metadata for migrations.
"""

from sqlalchemy.orm import declarative_base


Base = declarative_base()
