"""
File service - handles file operations business logic.

This service contains all the business logic for file operations.
Routes should call these functions instead of implementing logic directly.
"""
from pathlib import Path
from typing import Dict, List


class FileService:
    """Service for file operations."""
    
    def __init__(self, mount_path: Path):
        """
        Initialize file service.
        
        Args:
            mount_path: Path to the mounted data directory
        """
        self.mount_path = mount_path
    
    def list_txt_files(self) -> Dict[str, any]:
        """
        List all .txt files in the mounted directory.
        
        Returns:
            Dictionary with list of txt files or error message
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        txt_files = [
            f.name for f in self.mount_path.glob("*.txt") if f.is_file()
        ]
        return {"txt_files": txt_files}
    
    def list_extensions(self) -> Dict[str, any]:
        """
        List all unique file extensions in the mounted directory.
        
        Returns:
            Dictionary with sorted list of extensions or error message
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        extensions = {
            f.suffix for f in self.mount_path.iterdir() 
            if f.is_file() and f.suffix
        }
        return {"extensions": sorted(extensions)}
    
    def get_file_count(self) -> Dict[str, any]:
        """
        Get total count of files in the mounted directory.
        
        Returns:
            Dictionary with file count or error message
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        file_count = sum(1 for f in self.mount_path.iterdir() if f.is_file())
        return {"file_count": file_count}
    
    def print_txt_files(self) -> Dict[str, any]:
        """
        Read and return contents of all .txt files.
        
        Returns:
            Dictionary mapping filenames to their content
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        result = {}
        for f in self.mount_path.glob("*.txt"):
            if f.is_file():
                try:
                    result[f.name] = f.read_text(encoding="utf-8")
                except Exception as e:
                    result[f.name] = f"<error reading file: {e}>"
        
        return result
    
    def list_files_by_extension(self, ext: str) -> Dict[str, any]:
        """
        List all files with specified extension.
        
        Args:
            ext: File extension without dot (e.g., 'txt', 'json')
            
        Returns:
            Dictionary with extension and list of matching files
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        ext = ext.lower().strip().lstrip(".")
        files = [
            f.name for f in self.mount_path.glob(f"*.{ext}") if f.is_file()
        ]
        return {"extension": ext, "files": files}
    
    def print_files_by_extension(self, ext: str) -> Dict[str, any]:
        """
        Read and return contents of all files with specified extension.
        
        Args:
            ext: File extension without dot (e.g., 'txt', 'json')
            
        Returns:
            Dictionary with extension and file contents
        """
        if not self.mount_path.exists():
            return {"error": f"Mount path {self.mount_path} does not exist"}
        
        ext = ext.lower().strip().lstrip(".")
        result = {}
        
        for f in self.mount_path.glob(f"*.{ext}"):
            if f.is_file():
                try:
                    result[f.name] = f.read_text(encoding="utf-8")
                except Exception as e:
                    result[f.name] = f"<error reading file: {e}>"
        
        return {"extension": ext, "files": result}
