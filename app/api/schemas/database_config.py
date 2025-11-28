"""Database connection configuration schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class Neo4jConfig(BaseModel):
    """Neo4j database connection configuration."""
    neo4j_url: str = Field(..., description="Neo4j connection URL (e.g., bolt://localhost:7687)")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    target_api_url: Optional[str] = Field(
        None,
        description="Optional: Target API URL to lock during restore (e.g., http://localhost:8000)"
    )
    target_api_key: Optional[str] = Field(
        None,
        description="Optional: API key for target API lock endpoint"
    )


class Neo4jStatsConfig(BaseModel):
    """Neo4j database stats configuration (no locking fields)."""
    neo4j_url: str = Field(..., description="Neo4j connection URL (e.g., bolt://localhost:7687)")
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
    target_api_url: Optional[str] = Field(
        None,
        description="Optional: Target API URL to lock during restore (e.g., http://localhost:8000)"
    )
    target_api_key: Optional[str] = Field(
        None,
        description="Optional: API key for target API lock endpoint"
    )


class SQLStatsConfig(BaseModel):
    """SQL database stats configuration (no locking fields)."""
    db_type: str = Field(..., description="Database type: postgresql, mysql, or sqlite")
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(..., description="Database port")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
