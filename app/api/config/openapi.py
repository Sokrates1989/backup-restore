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
            "X-Admin-Key": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Admin-Key",
                "description": "Admin API Key for backup operations (download backups)"
            },
            "X-Restore-Key": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Restore-Key",
                "description": "Restore API Key for restore operations (overwrites database)"
            },
            "X-Delete-Key": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Delete-Key",
                "description": "Delete API Key for destructive delete operations"
            }
        }
        
        # Add security requirements to backup and automation endpoints
        for path, path_item in openapi_schema.get("paths", {}).items():
            if path.startswith("/backup/") or path.startswith("/automation/"):
                for method, operation in path_item.items():
                    if method in ["get", "post", "delete", "put", "patch"]:
                        if method == "delete":
                            operation["security"] = [{"X-Delete-Key": []}]
                        elif "restore" in path:
                            operation["security"] = [{"X-Restore-Key": []}]
                        else:
                            operation["security"] = [{"X-Admin-Key": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
