"""OpenAPI configuration for Swagger UI."""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def setup_openapi(app: FastAPI) -> None:
    """
    Configure OpenAPI schema for the FastAPI application with security schemes.
    
    Args:
        app: The FastAPI application instance
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Define security schemes that will appear in Swagger UI "Authorize" button
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Keycloak Bearer token for Backup Restore API"
            }
        }
        
        # Add security requirements to backup and automation endpoints
        for path, path_item in openapi_schema.get("paths", {}).items():
            if path.startswith("/backup/") or path.startswith("/automation/"):
                for method, operation in path_item.items():
                    if method in ["get", "post", "delete", "put", "patch"]:
                        operation["security"] = [{"BearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
