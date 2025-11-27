"""
Package information endpoint.
Lists all installed Python packages and their versions.

SECURITY: These endpoints require API key authentication via X-API-Key header.
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
import importlib.metadata
import sys
from api.security import verify_admin_key

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("/list")
def list_packages(_: str = Depends(verify_admin_key)) -> Dict[str, Any]:
    """
    List all installed Python packages and their versions.
    
    Requires authentication via X-API-Key header.
    
    Returns a list similar to 'pdm list' output with package name and version.
    """
    packages = []
    
    # Get all installed distributions
    distributions = sorted(importlib.metadata.distributions(), key=lambda d: d.name.lower())
    
    for dist in distributions:
        packages.append({
            "name": dist.name,
            "version": dist.version,
        })
    
    return {
        "total_packages": len(packages),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "packages": packages
    }


@router.get("/info/{package_name}")
def get_package_info(package_name: str, _: str = Depends(verify_admin_key)) -> Dict[str, Any]:
    """
    Get detailed information about a specific package.
    
    Requires authentication via X-API-Key header.
    
    Args:
        package_name: Name of the package to get information about
        
    Returns:
        Detailed package information including metadata
    """
    try:
        dist = importlib.metadata.distribution(package_name)
        
        # Get package metadata
        metadata = {
            "name": dist.name,
            "version": dist.version,
            "summary": dist.metadata.get("Summary", ""),
            "home_page": dist.metadata.get("Home-page", ""),
            "author": dist.metadata.get("Author", ""),
            "license": dist.metadata.get("License", ""),
            "requires_python": dist.metadata.get("Requires-Python", ""),
        }
        
        # Get dependencies
        requires = dist.metadata.get_all("Requires-Dist")
        if requires:
            metadata["dependencies"] = [req.split(";")[0].strip() for req in requires]
        else:
            metadata["dependencies"] = []
        
        return metadata
        
    except importlib.metadata.PackageNotFoundError:
        return {
            "error": f"Package '{package_name}' not found",
            "available_packages": [d.name for d in sorted(importlib.metadata.distributions(), key=lambda d: d.name.lower())]
        }
