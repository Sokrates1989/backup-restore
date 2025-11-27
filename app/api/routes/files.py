"""
Files route - handles file-related HTTP endpoints.

STRUCTURE:
- This file: HTTP request/response handling only
- Business logic: backend/services/file_service.py
"""
from fastapi import APIRouter, Query
from pathlib import Path
from backend.services.file_service import FileService

router = APIRouter(tags=["files"], prefix="/files")

# Initialize service with mount path
MOUNT_PATH = Path("/mnt/data")
file_service = FileService(MOUNT_PATH)


@router.get("/list-txt-files")
def list_txt_files():
    """List all .txt files in the mounted directory."""
    return file_service.list_txt_files()


@router.get("/list-extensions")
def list_extensions():
    """List all unique file extensions in the mounted directory."""
    return file_service.list_extensions()


@router.get("/file-count")
def get_file_count():
    """Get total count of files in the mounted directory."""
    return file_service.get_file_count()


@router.get("/print-txt")
def print_txt_files():
    """Read and return contents of all .txt files."""
    return file_service.print_txt_files()


@router.get("/list-files")
def list_files(ext: str = Query(..., description="File extension without dot, e.g., 'txt'")):
    """List all files with specified extension."""
    return file_service.list_files_by_extension(ext)


@router.get("/print")
def print_files(ext: str = Query(..., description="File extension without dot, e.g., 'txt'")):
    """Read and return contents of all files with specified extension."""
    return file_service.print_files_by_extension(ext)