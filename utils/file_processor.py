"""
File processing utilities for the Exam Grader application.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class FileProcessor:
    """File processing utility class."""
    
    def __init__(self, max_file_size_mb: int = 20):
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
    
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate file size and existence."""
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size_bytes:
                return False, f"File too large. Maximum size is {self.max_file_size_mb}MB"
            
            if file_size == 0:
                return False, "File is empty"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False, f"Error validating file: {str(e)}"
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information."""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File does not exist'}
            
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            return {
                'filename': path_obj.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'extension': path_obj.suffix.lower(),
                'created': stat.st_ctime,
                'modified': stat.st_mtime
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {'error': str(e)}
    
    def safe_remove(self, file_path: str) -> bool:
        """Safely remove a file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Successfully removed file: {file_path}")
                return True
            return True
            
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {str(e)}")
            return False

class MemoryEfficientFileHandler:
    """Memory-efficient file handling for large files."""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self._file_cache = {}  # Simple file content cache
        self._cache_max_size = 10  # Maximum cached files

    def read_text_file_limited(self, file_path: str, max_chars: int = 10000) -> str:
        """Read text file with character limit."""
        try:
            # Check cache first
            cache_key = f"{file_path}:{max_chars}"
            if cache_key in self._file_cache:
                return self._file_cache[cache_key]

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars)

            # Cache the content (with size limit)
            if len(self._file_cache) >= self._cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self._file_cache))
                del self._file_cache[oldest_key]

            self._file_cache[cache_key] = content
            return content

        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {str(e)}")
            return ""

    def read_file_in_chunks(self, file_path: str, chunk_size: Optional[int] = None):
        """Generator to read file in chunks for memory efficiency."""
        chunk_size = chunk_size or self.chunk_size
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Error reading file in chunks {file_path}: {str(e)}")
            return

    def get_file_hash_efficient(self, file_path: str) -> str:
        """Calculate file hash without loading entire file into memory."""
        import hashlib
        hash_obj = hashlib.sha256()

        try:
            for chunk in self.read_file_in_chunks(file_path):
                hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            return ""

    def clear_cache(self):
        """Clear the file content cache."""
        self._file_cache.clear()

def get_file_type(filename: str) -> str:
    """Get file type from filename."""
    if not filename:
        return 'unknown'
    
    ext = Path(filename).suffix.lower()
    
    type_mapping = {
        '.pdf': 'pdf',
        '.docx': 'word',
        '.doc': 'word',
        '.txt': 'text',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image'
    }
    
    return type_mapping.get(ext, 'unknown')

def is_text_file(filename: str) -> bool:
    """Check if file is a text file."""
    text_extensions = {'.txt', '.md', '.csv', '.json', '.xml', '.html'}
    ext = Path(filename).suffix.lower()
    return ext in text_extensions

def is_image_file(filename: str) -> bool:
    """Check if file is an image file."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    ext = Path(filename).suffix.lower()
    return ext in image_extensions

def is_document_file(filename: str) -> bool:
    """Check if file is a document file."""
    doc_extensions = {'.pdf', '.docx', '.doc'}
    ext = Path(filename).suffix.lower()
    return ext in doc_extensions
