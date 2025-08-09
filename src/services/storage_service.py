"""Storage Service - Real storage usage tracking and management."""

import os
from pathlib import Path
from typing import Dict, Union

from utils.logger import logger


def get_storage_stats() -> Dict[str, Union[int, float]]:
    """Get actual storage statistics for the application."""
    try:
        # Define storage directories to check
        storage_dirs = [
            "uploads",
            "temp", 
            "output",
            "cache",
            "logs",
            "instance"
        ]
        
        total_size_bytes = 0
        
        # Calculate total size of all storage directories
        for dir_name in storage_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                total_size_bytes += get_directory_size(dir_path)
        
        # Convert to MB
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        
        # Get available disk space
        try:
            import shutil
            _, _, free_bytes = shutil.disk_usage(".")
            max_size_mb = round(free_bytes / (1024 * 1024), 2)
        except Exception:
            # Fallback to a reasonable default if disk usage check fails
            max_size_mb = 10000  # 10GB default
        
        return {
            "total_size_mb": total_size_mb,
            "max_size_mb": max_size_mb,
            "usage_percentage": round((total_size_mb / max_size_mb) * 100, 1) if max_size_mb > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return {
            "total_size_mb": 0,
            "max_size_mb": 1000,
            "usage_percentage": 0
        }


def get_directory_size(directory: Path) -> int:
    """Calculate the total size of a directory in bytes."""
    total_size = 0
    try:
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    # Skip files that can't be accessed
                    continue
    except Exception as e:
        logger.debug(f"Error calculating directory size for {directory}: {e}")
    
    return total_size


def cleanup_temp_files(max_age_hours: int = 24) -> int:
    """Clean up temporary files older than specified hours."""
    import time
    
    cleaned_count = 0
    temp_dir = Path("temp")
    
    if not temp_dir.exists():
        return 0
    
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                try:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                except (OSError, FileNotFoundError):
                    continue
                    
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")
    
    return cleaned_count


def get_file_type_stats() -> Dict[str, int]:
    """Get statistics about file types in storage."""
    file_types = {}
    
    try:
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            for file_path in uploads_dir.rglob("*"):
                if file_path.is_file():
                    extension = file_path.suffix.lower()
                    if extension:
                        file_types[extension] = file_types.get(extension, 0) + 1
                    else:
                        file_types["no_extension"] = file_types.get("no_extension", 0) + 1
                        
    except Exception as e:
        logger.error(f"Error getting file type stats: {e}")
    
    return file_types