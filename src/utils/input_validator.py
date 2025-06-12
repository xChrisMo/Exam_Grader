"""
Enhanced Input Validation System for Exam Grader Application.

This module provides comprehensive input validation for file uploads,
user inputs, and API requests to prevent security vulnerabilities.
"""

import os
import re
import magic
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    message: str
    details: Dict[str, any] = None
    risk_level: str = "low"  # low, medium, high, critical


class InputValidator:
    """
    Comprehensive input validator for security and data integrity.
    
    Features:
    - File type validation with MIME type checking
    - Content scanning for malicious patterns
    - Size and format validation
    - Path traversal prevention
    - XSS and injection prevention
    """

    def __init__(self):
        """Initialize input validator."""
        self.allowed_file_types = {
            'pdf': ['application/pdf'],
            'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'doc': ['application/msword'],
            'txt': ['text/plain'],
            'jpg': ['image/jpeg'],
            'jpeg': ['image/jpeg'],
            'png': ['image/png'],
            'tiff': ['image/tiff'],
            'bmp': ['image/bmp'],
            'gif': ['image/gif']
        }
        
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_filename_length = 255
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # JavaScript
            r'javascript:',               # JavaScript URLs
            r'vbscript:',                # VBScript URLs
            r'on\w+\s*=',               # Event handlers
            r'<iframe[^>]*>',           # Iframes
            r'<object[^>]*>',           # Objects
            r'<embed[^>]*>',            # Embeds
            r'<link[^>]*>',             # Links
            r'<meta[^>]*>',             # Meta tags
            r'eval\s*\(',               # Eval functions
            r'exec\s*\(',               # Exec functions
            r'system\s*\(',             # System calls
            r'\.\./',                   # Path traversal
            r'\.\.\\',                  # Path traversal (Windows)
        ]

    def validate_file_upload(self, file_path: Union[str, Path], 
                           original_filename: str = None) -> ValidationResult:
        """
        Comprehensive file upload validation.
        
        Args:
            file_path: Path to uploaded file
            original_filename: Original filename from upload
            
        Returns:
            ValidationResult with validation status
        """
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                return ValidationResult(
                    is_valid=False,
                    message="File does not exist",
                    risk_level="medium"
                )
            
            # Validate filename
            filename_result = self.validate_filename(original_filename or file_path.name)
            if not filename_result.is_valid:
                return filename_result
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return ValidationResult(
                    is_valid=False,
                    message=f"File too large: {file_size / (1024*1024):.1f}MB (max: {self.max_file_size / (1024*1024):.1f}MB)",
                    details={"file_size": file_size, "max_size": self.max_file_size},
                    risk_level="medium"
                )
            
            # Check file type by extension and MIME type
            mime_result = self.validate_mime_type(file_path)
            if not mime_result.is_valid:
                return mime_result
            
            # Scan file content for dangerous patterns
            content_result = self.scan_file_content(file_path)
            if not content_result.is_valid:
                return content_result
            
            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(file_path)
            
            return ValidationResult(
                is_valid=True,
                message="File validation passed",
                details={
                    "file_size": file_size,
                    "mime_type": mime_result.details.get("mime_type"),
                    "file_hash": file_hash,
                    "extension": file_path.suffix.lower()
                },
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Validation error: {str(e)}",
                risk_level="high"
            )

    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate filename for security and format compliance.
        
        Args:
            filename: Filename to validate
            
        Returns:
            ValidationResult with validation status
        """
        try:
            if not filename:
                return ValidationResult(
                    is_valid=False,
                    message="Filename cannot be empty",
                    risk_level="medium"
                )
            
            # Check length
            if len(filename) > self.max_filename_length:
                return ValidationResult(
                    is_valid=False,
                    message=f"Filename too long: {len(filename)} chars (max: {self.max_filename_length})",
                    risk_level="medium"
                )
            
            # Check for dangerous characters
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
            for char in dangerous_chars:
                if char in filename:
                    return ValidationResult(
                        is_valid=False,
                        message=f"Filename contains dangerous character: {char}",
                        risk_level="high"
                    )
            
            # Check for path traversal attempts
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                return ValidationResult(
                    is_valid=False,
                    message="Filename contains path traversal attempt",
                    risk_level="critical"
                )
            
            # Check for reserved names (Windows)
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
            
            name_without_ext = Path(filename).stem.upper()
            if name_without_ext in reserved_names:
                return ValidationResult(
                    is_valid=False,
                    message=f"Filename uses reserved name: {name_without_ext}",
                    risk_level="medium"
                )
            
            return ValidationResult(
                is_valid=True,
                message="Filename validation passed",
                details={"filename": filename, "length": len(filename)},
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"Filename validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Filename validation error: {str(e)}",
                risk_level="high"
            )

    def validate_mime_type(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate file MIME type against allowed types.
        
        Args:
            file_path: Path to file
            
        Returns:
            ValidationResult with validation status
        """
        try:
            file_path = Path(file_path)
            
            # Get file extension
            extension = file_path.suffix.lower().lstrip('.')
            
            # Check if extension is allowed
            if extension not in self.allowed_file_types:
                return ValidationResult(
                    is_valid=False,
                    message=f"File type not allowed: .{extension}",
                    details={"extension": extension, "allowed_types": list(self.allowed_file_types.keys())},
                    risk_level="medium"
                )
            
            # Check MIME type using python-magic
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
            except Exception:
                # Fallback if python-magic is not available
                logger.warning("python-magic not available, skipping MIME type validation")
                return ValidationResult(
                    is_valid=True,
                    message="MIME type validation skipped (python-magic not available)",
                    details={"extension": extension},
                    risk_level="low"
                )
            
            # Check if MIME type matches allowed types for extension
            allowed_mimes = self.allowed_file_types[extension]
            if mime_type not in allowed_mimes:
                return ValidationResult(
                    is_valid=False,
                    message=f"MIME type mismatch: {mime_type} not allowed for .{extension}",
                    details={"mime_type": mime_type, "extension": extension, "allowed_mimes": allowed_mimes},
                    risk_level="high"
                )
            
            return ValidationResult(
                is_valid=True,
                message="MIME type validation passed",
                details={"mime_type": mime_type, "extension": extension},
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"MIME type validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"MIME type validation error: {str(e)}",
                risk_level="high"
            )

    def scan_file_content(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Scan file content for dangerous patterns.
        
        Args:
            file_path: Path to file
            
        Returns:
            ValidationResult with scan results
        """
        try:
            file_path = Path(file_path)
            
            # Only scan text-based files
            extension = file_path.suffix.lower().lstrip('.')
            if extension not in ['txt', 'html', 'htm', 'xml', 'json', 'csv']:
                return ValidationResult(
                    is_valid=True,
                    message="Content scan skipped for binary file",
                    details={"extension": extension},
                    risk_level="low"
                )
            
            # Read file content (limit to first 1MB for performance)
            max_scan_size = 1024 * 1024  # 1MB
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_scan_size)
            except UnicodeDecodeError:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read(max_scan_size)
            
            # Scan for dangerous patterns
            detected_patterns = []
            for pattern in self.dangerous_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                if matches:
                    detected_patterns.append({
                        "pattern": pattern,
                        "matches": len(matches),
                        "examples": matches[:3]  # First 3 matches
                    })
            
            if detected_patterns:
                return ValidationResult(
                    is_valid=False,
                    message=f"Dangerous content detected: {len(detected_patterns)} pattern(s) found",
                    details={"detected_patterns": detected_patterns},
                    risk_level="critical"
                )
            
            return ValidationResult(
                is_valid=True,
                message="Content scan passed",
                details={"scanned_size": len(content), "patterns_checked": len(self.dangerous_patterns)},
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"Content scan error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Content scan error: {str(e)}",
                risk_level="medium"
            )

    def validate_text_input(self, text: str, max_length: int = 10000) -> ValidationResult:
        """
        Validate text input for XSS and injection attacks.
        
        Args:
            text: Text to validate
            max_length: Maximum allowed length
            
        Returns:
            ValidationResult with validation status
        """
        try:
            if not text:
                return ValidationResult(
                    is_valid=True,
                    message="Empty text input",
                    risk_level="low"
                )
            
            # Check length
            if len(text) > max_length:
                return ValidationResult(
                    is_valid=False,
                    message=f"Text too long: {len(text)} chars (max: {max_length})",
                    risk_level="medium"
                )
            
            # Scan for dangerous patterns
            detected_patterns = []
            for pattern in self.dangerous_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                if matches:
                    detected_patterns.append({
                        "pattern": pattern,
                        "matches": len(matches)
                    })
            
            if detected_patterns:
                return ValidationResult(
                    is_valid=False,
                    message=f"Dangerous content in text: {len(detected_patterns)} pattern(s) found",
                    details={"detected_patterns": detected_patterns},
                    risk_level="high"
                )
            
            return ValidationResult(
                is_valid=True,
                message="Text validation passed",
                details={"length": len(text)},
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"Text validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Text validation error: {str(e)}",
                risk_level="medium"
            )

    def _calculate_file_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate SHA-256 hash of file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation error: {str(e)}")
            return "unknown"


# Global validator instance
input_validator = InputValidator()
