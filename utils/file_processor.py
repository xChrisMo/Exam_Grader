"""
Optimized file processing utilities for the Exam Grader application.
"""
import os
import io
import mmap
import hashlib
import tempfile
from typing import Iterator, Optional, Tuple, BinaryIO, Dict, Any
from pathlib import Path
from contextlib import contextmanager
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FileProcessor:
    """Optimized file processor with streaming and memory management."""
    
    # File processing constants
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
    MAX_MEMORY_FILE_SIZE = 10 * 1024 * 1024  # 10MB - keep in memory
    HASH_BUFFER_SIZE = 1024 * 1024  # 1MB buffer for hashing
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
        """
        Calculate file hash efficiently using streaming.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)
        
        try:
            with open(file_path, 'rb') as f:
                # Use memory mapping for large files
                file_size = os.path.getsize(file_path)
                
                if file_size > FileProcessor.MAX_MEMORY_FILE_SIZE:
                    # Use memory mapping for large files
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        for i in range(0, file_size, FileProcessor.HASH_BUFFER_SIZE):
                            chunk = mm[i:i + FileProcessor.HASH_BUFFER_SIZE]
                            hash_obj.update(chunk)
                else:
                    # Read in chunks for smaller files
                    while chunk := f.read(FileProcessor.HASH_BUFFER_SIZE):
                        hash_obj.update(chunk)
                        
            return hash_obj.hexdigest()
            
        except (OSError, IOError) as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def stream_file_chunks(file_path: str, chunk_size: Optional[int] = None) -> Iterator[bytes]:
        """
        Stream file content in chunks to avoid loading entire file into memory.
        
        Args:
            file_path: Path to the file
            chunk_size: Size of each chunk (defaults to CHUNK_SIZE)
            
        Yields:
            File content chunks as bytes
        """
        if chunk_size is None:
            chunk_size = FileProcessor.CHUNK_SIZE
            
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    yield chunk
        except (OSError, IOError) as e:
            logger.error(f"Error streaming file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    @contextmanager
    def temporary_file(suffix: str = '', prefix: str = 'exam_grader_', 
                      directory: Optional[str] = None):
        """
        Context manager for temporary files with automatic cleanup.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            directory: Directory to create temp file in
            
        Yields:
            Temporary file path
        """
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix, 
                prefix=prefix, 
                dir=directory, 
                delete=False
            )
            temp_path = temp_file.name
            temp_file.close()
            
            logger.debug(f"Created temporary file: {temp_path}")
            yield temp_path
            
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    logger.debug(f"Cleaned up temporary file: {temp_file.name}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_file.name}: {str(e)}")
    
    @staticmethod
    def safe_file_copy(source: str, destination: str, buffer_size: Optional[int] = None) -> bool:
        """
        Safely copy file with streaming to handle large files.
        
        Args:
            source: Source file path
            destination: Destination file path
            buffer_size: Buffer size for copying
            
        Returns:
            True if successful, False otherwise
        """
        if buffer_size is None:
            buffer_size = FileProcessor.CHUNK_SIZE
            
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            
            with open(source, 'rb') as src, open(destination, 'wb') as dst:
                while chunk := src.read(buffer_size):
                    dst.write(chunk)
            
            logger.debug(f"Successfully copied {source} to {destination}")
            return True
            
        except (OSError, IOError) as e:
            logger.error(f"Error copying file from {source} to {destination}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive file information efficiently.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            return {
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': stat.st_mtime,
                'created_time': stat.st_ctime,
                'extension': path_obj.suffix.lower(),
                'filename': path_obj.name,
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK),
            }
        except (OSError, IOError) as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {}
    
    @staticmethod
    def validate_file_size(file_path: str, max_size_mb: int = 50) -> bool:
        """
        Validate file size without loading entire file.
        
        Args:
            file_path: Path to the file
            max_size_mb: Maximum allowed size in MB
            
        Returns:
            True if file size is acceptable
        """
        try:
            file_size = os.path.getsize(file_path)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                logger.warning(f"File {file_path} exceeds size limit: {file_size} bytes > {max_size_bytes} bytes")
                return False
                
            return True
            
        except (OSError, IOError) as e:
            logger.error(f"Error checking file size for {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def process_file_in_chunks(file_path: str, processor_func, 
                              chunk_size: Optional[int] = None, 
                              **kwargs) -> Any:
        """
        Process file in chunks using a provided processor function.
        
        Args:
            file_path: Path to the file
            processor_func: Function to process each chunk
            chunk_size: Size of each chunk
            **kwargs: Additional arguments for processor function
            
        Returns:
            Result from processor function
        """
        if chunk_size is None:
            chunk_size = FileProcessor.CHUNK_SIZE
            
        try:
            results = []
            with open(file_path, 'rb') as f:
                chunk_number = 0
                while chunk := f.read(chunk_size):
                    result = processor_func(chunk, chunk_number=chunk_number, **kwargs)
                    if result is not None:
                        results.append(result)
                    chunk_number += 1
            
            return results
            
        except (OSError, IOError) as e:
            logger.error(f"Error processing file {file_path} in chunks: {str(e)}")
            raise
    
    @staticmethod
    def create_file_stream(file_path: str) -> BinaryIO:
        """
        Create a file stream for efficient reading.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File stream object
        """
        try:
            return open(file_path, 'rb')
        except (OSError, IOError) as e:
            logger.error(f"Error creating file stream for {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def batch_process_files(file_paths: list, processor_func, 
                           batch_size: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Process multiple files in batches to manage memory usage.
        
        Args:
            file_paths: List of file paths to process
            processor_func: Function to process each file
            batch_size: Number of files to process in each batch
            **kwargs: Additional arguments for processor function
            
        Returns:
            Dictionary mapping file paths to results
        """
        results = {}
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch)} files")
            
            for file_path in batch:
                try:
                    result = processor_func(file_path, **kwargs)
                    results[file_path] = result
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    results[file_path] = {'error': str(e)}
        
        return results

class MemoryEfficientFileHandler:
    """Memory-efficient file handler for large file operations."""
    
    def __init__(self, max_memory_usage_mb: int = 100):
        """
        Initialize with memory usage limit.
        
        Args:
            max_memory_usage_mb: Maximum memory usage in MB
        """
        self.max_memory_bytes = max_memory_usage_mb * 1024 * 1024
        self.current_memory_usage = 0
        self._file_handles = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def open_file(self, file_path: str, mode: str = 'rb') -> BinaryIO:
        """
        Open file with memory tracking.
        
        Args:
            file_path: Path to the file
            mode: File open mode
            
        Returns:
            File handle
        """
        try:
            file_size = os.path.getsize(file_path)
            
            # Check if opening this file would exceed memory limit
            if self.current_memory_usage + file_size > self.max_memory_bytes:
                self._cleanup_oldest_files()
            
            file_handle = open(file_path, mode)
            self._file_handles[file_path] = {
                'handle': file_handle,
                'size': file_size,
                'access_time': os.time.time()
            }
            self.current_memory_usage += file_size
            
            logger.debug(f"Opened file {file_path}, memory usage: {self.current_memory_usage / (1024*1024):.2f}MB")
            return file_handle
            
        except (OSError, IOError) as e:
            logger.error(f"Error opening file {file_path}: {str(e)}")
            raise
    
    def close_file(self, file_path: str) -> None:
        """Close and remove file from tracking."""
        if file_path in self._file_handles:
            file_info = self._file_handles[file_path]
            file_info['handle'].close()
            self.current_memory_usage -= file_info['size']
            del self._file_handles[file_path]
            logger.debug(f"Closed file {file_path}")
    
    def _cleanup_oldest_files(self) -> None:
        """Close oldest files to free memory."""
        # Sort by access time (oldest first)
        sorted_files = sorted(
            self._file_handles.items(),
            key=lambda x: x[1]['access_time']
        )
        
        # Close oldest files until we have enough memory
        for file_path, file_info in sorted_files:
            self.close_file(file_path)
            if self.current_memory_usage < self.max_memory_bytes * 0.7:  # Leave 30% buffer
                break
    
    def cleanup(self) -> None:
        """Close all open files."""
        for file_path in list(self._file_handles.keys()):
            self.close_file(file_path)
        logger.debug("Cleaned up all file handles")
