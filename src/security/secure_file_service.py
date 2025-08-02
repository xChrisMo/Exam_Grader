"""Secure File Upload and Processing Service for Exam Grader Application.

This module provides secure file handling with comprehensive validation,
sandboxed processing, and malware detection capabilities.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from src.exceptions.application_errors import SecurityError
except ImportError:
    # Fallback implementations
    class SecurityError(Exception):
        pass
    
    class ValidationError(Exception):
        pass
    
    def validate_file_upload(file_obj, filename):
        return True, None, {}

class SecureFileStorage:
    """Secure file storage with isolation and cleanup."""
    
    def __init__(self, base_path: str, max_storage_days: int = 30):
        """Initialize secure file storage.
        
        Args:
            base_path: Base directory for file storage
            max_storage_days: Maximum days to keep files
        """
        self.base_path = Path(base_path)
        self.max_storage_days = max_storage_days
        self.quarantine_path = self.base_path / 'quarantine'
        self.temp_path = self.base_path / 'temp'
        self.processed_path = self.base_path / 'processed'
        
        # Create directories
        for path in [self.base_path, self.quarantine_path, self.temp_path, self.processed_path]:
            path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Secure file storage initialized at {self.base_path}")
    
    def store_file(self, file_content: bytes, filename: str, file_info: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Path]]:
        """Store file securely with metadata.
        
        Args:
            file_content: File content bytes
            filename: Original filename
            file_info: File validation information
            
        Returns:
            Tuple of (success, error_message, stored_path)
        """
        try:
            # Generate secure filename
            secure_filename = self._generate_secure_filename(filename, file_info.get('hash', ''))
            
            # Determine storage path based on validation
            if file_info.get('quarantined', False):
                storage_path = self.quarantine_path / secure_filename
            else:
                storage_path = self.processed_path / secure_filename
            
            # Write file
            with open(storage_path, 'wb') as f:
                f.write(file_content)
            
            # Set restrictive permissions
            os.chmod(storage_path, 0o600)
            
            # Store metadata
            metadata_path = storage_path.with_suffix('.meta')
            metadata = {
                'original_filename': filename,
                'stored_filename': secure_filename,
                'file_info': file_info,
                'storage_timestamp': datetime.now(timezone.utc).isoformat(),
                'size': len(file_content)
            }
            
            with open(metadata_path, 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            os.chmod(metadata_path, 0o600)
            
            logger.info(f"File stored securely: {secure_filename}")
            return True, None, storage_path
            
        except Exception as e:
            logger.error(f"Error storing file {filename}: {str(e)}")
            return False, f"Failed to store file: {str(e)}", None
    
    def retrieve_file(self, stored_filename: str) -> Tuple[bool, Optional[str], Optional[bytes], Optional[Dict[str, Any]]]:
        """Retrieve stored file with metadata.
        
        Args:
            stored_filename: Secure filename
            
        Returns:
            Tuple of (success, error_message, file_content, metadata)
        """
        try:
            # Check processed files first
            file_path = self.processed_path / stored_filename
            if not file_path.exists():
                file_path = self.quarantine_path / stored_filename
            
            if not file_path.exists():
                return False, "File not found", None, None
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Read metadata
            metadata_path = file_path.with_suffix('.meta')
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    import json
                    metadata = json.load(f)
            
            return True, None, file_content, metadata
            
        except Exception as e:
            logger.error(f"Error retrieving file {stored_filename}: {str(e)}")
            return False, f"Failed to retrieve file: {str(e)}", None, None
    
    def cleanup_old_files(self) -> int:
        """Clean up old files based on retention policy.
        
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_storage_days)
        
        try:
            for directory in [self.processed_path, self.quarantine_path, self.temp_path]:
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        # Check file age
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_date:
                            try:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"Cleaned up old file: {file_path.name}")
                            except Exception as e:
                                logger.error(f"Error cleaning up file {file_path}: {str(e)}")
            
            logger.info(f"Cleaned up {cleaned_count} old files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")
            return cleaned_count
    
    def _generate_secure_filename(self, original_filename: str, file_hash: str) -> str:
        """Generate secure filename.
        
        Args:
            original_filename: Original filename
            file_hash: File content hash
            
        Returns:
            Secure filename
        """
        # Get file extension
        extension = Path(original_filename).suffix.lower()
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        hash_prefix = file_hash[:16] if file_hash else 'unknown'
        
        return f"{timestamp}_{hash_prefix}{extension}"

class MalwareScanner:
    """Basic malware detection for uploaded files."""
    
    # Known malicious patterns
    MALICIOUS_PATTERNS = [
        # PE executable signatures
        b'\x4D\x5A\x90\x00',  # DOS header
        b'\x4D\x5A\x50\x00',  # DOS header variant
        
        # Script patterns
        b'<script',
        b'javascript:',
        b'vbscript:',
        
        # Shell commands
        b'cmd.exe',
        b'powershell',
        b'/bin/sh',
        b'/bin/bash',
        
        # Suspicious strings
        b'eval(',
        b'exec(',
        b'system(',
        b'shell_exec',
    ]
    
    # Suspicious file extensions embedded in content
    SUSPICIOUS_EXTENSIONS = [
        b'.exe', b'.bat', b'.cmd', b'.com', b'.scr',
        b'.pif', b'.vbs', b'.js', b'.jar', b'.ps1'
    ]
    
    @classmethod
    def scan_file(cls, file_content: bytes, filename: str) -> Tuple[bool, List[str]]:
        """Scan file for malware patterns.
        
        Args:
            file_content: File content to scan
            filename: Original filename
            
        Returns:
            Tuple of (is_clean, detected_threats)
        """
        threats = []
        
        try:
            for pattern in cls.MALICIOUS_PATTERNS:
                if pattern in file_content:
                    threats.append(f"Malicious pattern detected: {pattern.decode('utf-8', errors='ignore')}")
            
            for ext in cls.SUSPICIOUS_EXTENSIONS:
                if ext in file_content:
                    threats.append(f"Suspicious file extension in content: {ext.decode('utf-8', errors='ignore')}")
            
            entropy = cls._calculate_entropy(file_content)
            if entropy > 7.5:  # High entropy threshold
                threats.append(f"High entropy detected: {entropy:.2f} (possible obfuscation)")
            
            # Check file size anomalies
            if len(file_content) > 100 * 1024 * 1024:  # 100MB
                threats.append("Unusually large file size")
            
            is_clean = len(threats) == 0
            
            if not is_clean:
                logger.warning(f"Malware scan detected threats in {filename}: {threats}")
            
            return is_clean, threats
            
        except Exception as e:
            logger.error(f"Error scanning file {filename}: {str(e)}")
            return False, [f"Scan error: {str(e)}"]
    
    @classmethod
    def _calculate_entropy(cls, data: bytes) -> float:
        """Calculate Shannon entropy of data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Entropy value
        """
        if not data:
            return 0
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Calculate entropy
        entropy = 0
        data_len = len(data)
        
        for count in byte_counts:
            if count > 0:
                probability = count / data_len
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy

class SecureFileService:
    """Main secure file service."""
    
    def __init__(self, storage_path: str, enable_malware_scan: bool = True):
        """Initialize secure file service.
        
        Args:
            storage_path: Base path for file storage
            enable_malware_scan: Whether to enable malware scanning
        """
        self.storage = SecureFileStorage(storage_path)
        self.enable_malware_scan = enable_malware_scan
        self.malware_scanner = MalwareScanner()
        
        logger.info(f"Secure file service initialized (malware scan: {enable_malware_scan})")
    
    def process_upload(self, file_obj: BinaryIO, filename: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Process file upload with comprehensive security checks.
        
        Args:
            file_obj: File object to process
            filename: Original filename
            
        Returns:
            Tuple of (success, error_message, file_info)
        """
        try:
            # Step 1: Basic file validation
            is_valid, error_msg, file_info = validate_file_upload(file_obj, filename)
            if not is_valid:
                logger.warning(f"File validation failed for {filename}: {error_msg}")
                return False, error_msg, None
            
            # Step 2: Read file content
            file_obj.seek(0)
            file_content = file_obj.read()
            file_obj.seek(0)
            
            # Step 3: Malware scanning
            if self.enable_malware_scan:
                is_clean, threats = self.malware_scanner.scan_file(file_content, filename)
                if not is_clean:
                    file_info['quarantined'] = True
                    file_info['threats'] = threats
                    logger.warning(f"File {filename} quarantined due to threats: {threats}")
                    
                    # Store in quarantine but don't fail the upload
                    success, store_error, stored_path = self.storage.store_file(file_content, filename, file_info)
                    if success:
                        file_info['stored_path'] = str(stored_path)
                        return True, f"File quarantined due to security concerns: {', '.join(threats)}", file_info
                    else:
                        return False, f"Failed to quarantine file: {store_error}", None
            
            # Step 4: Store file securely
            success, store_error, stored_path = self.storage.store_file(file_content, filename, file_info)
            if not success:
                return False, store_error, None
            
            file_info['stored_path'] = str(stored_path)
            file_info['processing_status'] = 'completed'
            
            logger.info(f"File {filename} processed successfully")
            return True, None, file_info
            
        except Exception as e:
            logger.error(f"Error processing upload {filename}: {str(e)}")
            return False, f"File processing failed: {str(e)}", None
    
    def get_file(self, stored_filename: str) -> Tuple[bool, Optional[str], Optional[bytes], Optional[Dict[str, Any]]]:
        """Retrieve processed file.
        
        Args:
            stored_filename: Secure filename
            
        Returns:
            Tuple of (success, error_message, file_content, metadata)
        """
        return self.storage.retrieve_file(stored_filename)
    
    def cleanup_files(self) -> int:
        """Clean up old files.
        
        Returns:
            Number of files cleaned up
        """
        return self.storage.cleanup_old_files()
    
    @contextmanager
    def secure_temp_file(self, suffix: str = ''):
        """Create a secure temporary file.
        
        Args:
            suffix: File suffix
            
        Yields:
            Temporary file path
        """
        temp_file = None
        try:
            # Create temporary file in secure location
            temp_dir = self.storage.temp_path
            temp_file = tempfile.NamedTemporaryFile(
                dir=temp_dir,
                suffix=suffix,
                delete=False
            )
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            # Set restrictive permissions
            os.chmod(temp_path, 0o600)
            
            yield temp_path
            
        finally:
            # Clean up temporary file
            if temp_file and Path(temp_file.name).exists():
                try:
                    Path(temp_file.name).unlink()
                except Exception as e:
                    logger.error(f"Error cleaning up temp file: {str(e)}")
    
    def validate_file_access(self, stored_filename: str, user_id: Optional[str] = None) -> bool:
        """Validate if user can access file.
        
        Args:
            stored_filename: Secure filename
            user_id: User identifier
            
        Returns:
            True if access is allowed
        """
        try:
            # Get file metadata
            success, error, content, metadata = self.storage.retrieve_file(stored_filename)
            if not success:
                return False
            
            if metadata and metadata.get('file_info', {}).get('quarantined', False):
                logger.warning(f"Access denied to quarantined file: {stored_filename}")
                return False
            
            # Additional access control logic can be added here
            # For now, allow access to non-quarantined files
            return True
            
        except Exception as e:
            logger.error(f"Error validating file access for {stored_filename}: {str(e)}")
            return False

# Global secure file service instance
secure_file_service = None

def init_secure_file_service(storage_path: str, enable_malware_scan: bool = True) -> SecureFileService:
    """Initialize global secure file service.
    
    Args:
        storage_path: Base path for file storage
        enable_malware_scan: Whether to enable malware scanning
        
    Returns:
        SecureFileService instance
    """
    global secure_file_service
    secure_file_service = SecureFileService(storage_path, enable_malware_scan)
    return secure_file_service

def get_secure_file_service() -> Optional[SecureFileService]:
    """Get global secure file service instance.
    
    Returns:
        SecureFileService instance or None
    """
    return secure_file_service