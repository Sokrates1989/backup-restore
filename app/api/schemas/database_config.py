"""Database connection configuration schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class Neo4jConfig(BaseModel):
    """Neo4j database connection configuration."""
    neo4j_url: str = Field(
        ...,
        description=(
            "Neo4j connection URL. For example: "
            "bolt://neo4j:7687 when the backup service and Neo4j run in the same "
            "Docker Compose project, or bolt://host.docker.internal:7687 when "
            "connecting to a Neo4j instance exposed on the host."
        ),
    )
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    lock_target_db: bool = Field(
        False,
        description=(
            "When true, attempt to lock the target API during backup/restore "
            "(requires target_api_url and target_api_token)."
        ),
    )
    target_api_url: Optional[str] = Field(
        None,
        description=(
            "Optional: Target API URL to lock during backup/restore. "
            "For example, if the target API is exposed on the host at port 8081, "
            "use http://host.docker.internal:8081."
        ),
    )
    target_api_token: Optional[str] = Field(
        None,
        description="Optional: Bearer token for target API lock endpoint"
    )


class Neo4jStatsConfig(BaseModel):
    """Neo4j database stats configuration (no locking fields)."""
    neo4j_url: str = Field(
        ...,
        description=(
            "Neo4j connection URL. For example: "
            "bolt://neo4j:7687 when the backup service and Neo4j run in the same "
            "Docker Compose project, or bolt://host.docker.internal:7687 when "
            "connecting to a Neo4j instance exposed on the host."
        ),
    )
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")


class SQLConfig(BaseModel):
    """SQL database connection configuration."""
    db_type: str = Field(..., description="Database type: postgresql, mysql, or sqlite")
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(..., description="Database port")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    lock_target_db: bool = Field(
        False,
        description=(
            "When true, attempt to lock the target API during backup/restore "
            "(requires target_api_url and target_api_token)."
        ),
    )
    target_api_url: Optional[str] = Field(
        None,
        description=(
            "Optional: Target API URL to lock during backup/restore. "
            "For example, if the target API is exposed on the host at port 8081, "
            "use http://host.docker.internal:8081."
        ),
    )
    target_api_token: Optional[str] = Field(
        None,
        description="Optional: Bearer token for target API lock endpoint"
    )


class SQLStatsConfig(BaseModel):
    """SQL database stats configuration (no locking fields)."""
    db_type: str = Field(..., description="Database type: postgresql, mysql, or sqlite")
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(..., description="Database port")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
