"""
Secure File Handler Service

Provides secure file handling capabilities for training file uploads.
"""

import os
import hashlib
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.services.base_service import BaseService
from utils.logger import logger


class FileValidationResult(Enum):
    """File validation result status"""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    QUARANTINED = "quarantined"


@dataclass
class FileSecurityInfo:
    """File security information"""
    file_hash: str
    mime_type: str
    file_size: int
    validation_result: FileValidationResult
    scan_timestamp: float
    quarantine_reason: Optional[str] = None
    integrity_verified: bool = False


class SecureFileHandler(BaseService):
    """Secure file handling service with comprehensive security features"""
    
    # Allowed MIME types for training files
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'image/jpeg',
        'image/png',
        'image/tiff',
        'image/bmp',
        'image/gif'
    }
    
    # Dangerous file extensions to block
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js',
        '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi'
    }
    
    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    def __init__(self):
        super().__init__()
        self.quarantine_dir = Path('quarantine')
        self.temp_dir = Path('temp/secure_uploads')
        self.secure_storage_dir = Path('uploads/secure')
        
        # Create necessary directories
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist with proper permissions"""
        directories = [self.quarantine_dir, self.temp_dir, self.secure_storage_dir]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(directory, 0o700)
            except OSError as e:
                logger.warning(f"Could not set directory permissions for {directory}: {e}")
    
    def validate_file(self, file_path: Path, original_filename: str) -> FileSecurityInfo:
        """Comprehensive file validation including security checks"""
        try:
            logger.info(f"Starting security validation for file: {original_filename}")
            
            # Basic file existence and size checks
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                return FileSecurityInfo(
                    file_hash="",
                    mime_type="",
                    file_size=0,
                    validation_result=FileValidationResult.INVALID,
                    scan_timestamp=time.time(),
                    quarantine_reason="Empty file"
                )
            
            if file_size > self.MAX_FILE_SIZE:
                return FileSecurityInfo(
                    file_hash="",
                    mime_type="",
                    file_size=file_size,
                    validation_result=FileValidationResult.INVALID,
                    scan_timestamp=time.time(),
                    quarantine_reason=f"File too large: {file_size} bytes"
                )
            
            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(file_path)
            
            # Detect MIME type
            import mimetypes
            mime_type, _ = mimetypes.guess_type(original_filename)
            mime_type = mime_type or 'application/octet-stream'
            
            # Validate file extension
            file_extension = Path(original_filename).suffix.lower()
            if file_extension in self.BLOCKED_EXTENSIONS:
                return FileSecurityInfo(
                    file_hash=file_hash,
                    mime_type=mime_type,
                    file_size=file_size,
                    validation_result=FileValidationResult.INVALID,
                    scan_timestamp=time.time(),
                    quarantine_reason="Blocked file extension"
                )
            
            # Validate MIME type
            if mime_type not in self.ALLOWED_MIME_TYPES:
                return FileSecurityInfo(
                    file_hash=file_hash,
                    mime_type=mime_type,
                    file_size=file_size,
                    validation_result=FileValidationResult.INVALID,
                    scan_timestamp=time.time(),
                    quarantine_reason="Invalid MIME type"
                )
            
            # Perform basic virus scan
            if not self._perform_basic_scan(file_path):
                return FileSecurityInfo(
                    file_hash=file_hash,
                    mime_type=mime_type,
                    file_size=file_size,
                    validation_result=FileValidationResult.QUARANTINED,
                    scan_timestamp=time.time(),
                    quarantine_reason="Failed security scan"
                )
            
            # All checks passed
            logger.info(f"File validation successful: {original_filename}")
            return FileSecurityInfo(
                file_hash=file_hash,
                mime_type=mime_type,
                file_size=file_size,
                validation_result=FileValidationResult.VALID,
                scan_timestamp=time.time(),
                integrity_verified=True
            )
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            return FileSecurityInfo(
                file_hash="",
                mime_type="",
                file_size=0,
                validation_result=FileValidationResult.INVALID,
                scan_timestamp=time.time(),
                quarantine_reason=f"Validation error: {str(e)}"
            )
    
    def secure_store_file(self, file_path: Path, user_id: int, session_id: str) -> Tuple[Path, str]:
        """Securely store a validated file with proper naming and permissions"""
        try:
            # Create user-specific secure directory
            user_secure_dir = self.secure_storage_dir / str(user_id) / session_id
            user_secure_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate secure filename
            file_hash = self._calculate_file_hash(file_path)
            file_extension = file_path.suffix.lower()
            secure_filename = f"{file_hash[:16]}_{int(time.time())}{file_extension}"
            
            # Copy file to secure location
            secure_path = user_secure_dir / secure_filename
            shutil.copy2(file_path, secure_path)
            
            # Set restrictive permissions
            try:
                os.chmod(secure_path, 0o600)  # Owner read/write only
            except OSError as e:
                logger.warning(f"Could not set file permissions: {e}")
            
            logger.info(f"File securely stored: {secure_filename} for user {user_id}")
            return secure_path, secure_filename
            
        except Exception as e:
            logger.error(f"Error securely storing file: {e}")
            raise
    
    def quarantine_file(self, file_path: Path, reason: str, user_id: int) -> Path:
        """Move a suspicious or dangerous file to quarantine"""
        try:
            # Create quarantine subdirectory
            quarantine_subdir = self.quarantine_dir / str(user_id)
            quarantine_subdir.mkdir(parents=True, exist_ok=True)
            
            # Generate quarantine filename with timestamp
            timestamp = int(time.time())
            quarantine_filename = f"quarantine_{timestamp}_{file_path.name}"
            quarantine_path = quarantine_subdir / quarantine_filename
            
            # Move file to quarantine
            shutil.move(str(file_path), str(quarantine_path))
            
            # Set restrictive permissions
            try:
                os.chmod(quarantine_path, 0o000)  # No permissions
            except OSError as e:
                logger.warning(f"Could not set quarantine permissions: {e}")
            
            logger.warning(f"File quarantined: {file_path.name} -> {quarantine_filename}, Reason: {reason}")
            return quarantine_path
            
        except Exception as e:
            logger.error(f"Error quarantining file: {e}")
            raise
    
    def cleanup_temporary_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age"""
        try:
            cleanup_count = 0
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            # Clean up temp directory
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            cleanup_count += 1
                            logger.debug(f"Cleaned up temporary file: {file_path}")
                        except OSError as e:
                            logger.warning(f"Could not delete temporary file {file_path}: {e}")
            
            logger.info(f"Cleanup completed: {cleanup_count} files removed")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def verify_file_integrity(self, file_path: Path, expected_hash: str) -> bool:
        """Verify file integrity using hash comparison"""
        try:
            current_hash = self._calculate_file_hash(file_path)
            return current_hash == expected_hash
        except Exception as e:
            logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""
    
    def _perform_basic_scan(self, file_path: Path) -> bool:
        """Perform basic security scan on file"""
        try:
            # Check file size (extremely large files might be suspicious)
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB
                logger.warning(f"Large file detected: {file_size} bytes")
                return False
            
            # Check for suspicious patterns in filename
            suspicious_patterns = ['virus', 'malware', 'trojan', 'backdoor']
            filename_lower = file_path.name.lower()
            if any(pattern in filename_lower for pattern in suspicious_patterns):
                logger.warning(f"Suspicious filename pattern: {file_path.name}")
                return False
            
            # Basic content scan for executable signatures
            try:
                with open(file_path, 'rb') as f:
                    content = f.read(1024)  # Read first 1KB
                
                # Check for executable signatures
                executable_signatures = [b'MZ', b'\\x7fELF', b'\\xca\\xfe\\xba\\xbe']
                if any(content.startswith(sig) for sig in executable_signatures):
                    logger.warning(f"Executable signature detected in: {file_path.name}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error reading file for scan: {e}")
                return False
            
            return True  # Passed basic checks
            
        except Exception as e:
            logger.error(f"Error during security scan: {e}")
            return False

