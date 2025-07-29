"""
Security utilities for the webapp.

This module provides security validation and rate limiting functionality.
"""

import os
import re
import secrets
import time
from collections import defaultdict, deque
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import logger

class SecurityValidator:
    """Security validation utilities."""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.bmp'
    }
    
    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        'default': 16 * 1024 * 1024,  # 16MB
        'image': 10 * 1024 * 1024,    # 10MB
        'document': 20 * 1024 * 1024,  # 20MB
    }
    
    # Dangerous characters and patterns
    DANGEROUS_CHARS = ['\x00', '..', '/', '\\', '<', '>', '|', ':', '*', '?', '"']
    
    @classmethod
    def validate_filename(cls, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate filename for security.
        
        Args:
            filename: The filename to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"
        
        if len(filename) > 255:
            return False, "Filename too long (max 255 characters)"
        
        for char in cls.DANGEROUS_CHARS:
            if char in filename:
                return False, f"Filename contains invalid character: {char}"
        
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed: {ext}"
        
        return True, None
    
    @classmethod
    def validate_file_path(cls, file_path: str, allowed_base_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file path to prevent directory traversal.
        
        Args:
            file_path: The file path to validate
            allowed_base_path: The base path that files must be within
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Resolve paths to absolute paths
            abs_file_path = Path(file_path).resolve()
            abs_base_path = Path(allowed_base_path).resolve()
            
            if not str(abs_file_path).startswith(str(abs_base_path)):
                return False, "File path outside allowed directory"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid file path: {str(e)}"
    
    @classmethod
    def validate_file_size(cls, size_bytes: int, file_type: str = 'default') -> Tuple[bool, Optional[str]]:
        """
        Validate file size.
        
        Args:
            size_bytes: File size in bytes
            file_type: Type of file (default, image, document)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        max_size = cls.MAX_FILE_SIZES.get(file_type, cls.MAX_FILE_SIZES['default'])
        
        if size_bytes > max_size:
            max_mb = max_size / (1024 * 1024)
            return False, f"File too large. Maximum size for {file_type} files is {max_mb:.1f}MB"
        
        return True, None
    
    @classmethod
    def sanitize_input(cls, input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize user input.
        
        Args:
            input_str: The input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(input_str, str):
            input_str = str(input_str)
        
        # Remove null bytes
        input_str = input_str.replace('\x00', '')
        
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        # HTML escape
        input_str = escape(input_str)
        
        return input_str
    
    @classmethod
    def generate_secure_token(cls, length: int = 32) -> str:
        """
        Generate a secure random token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            Hex-encoded secure token
        """
        return secrets.token_hex(length)

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = {}
    
    def is_allowed(
        self, 
        identifier: str, 
        max_requests: int = 100, 
        window_seconds: int = 3600
    ) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        if len(request_times) >= max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Add current request
        request_times.append(current_time)
        return True
    
    def get_remaining_requests(
        self, 
        identifier: str, 
        max_requests: int = 100, 
        window_seconds: int = 3600
    ) -> int:
        """Get number of remaining requests for identifier."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        return max(0, max_requests - len(request_times))
    
    def reset_limit(self, identifier: str):
        """Reset rate limit for identifier."""
        if identifier in self.requests:
            del self.requests[identifier]
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            'active_identifiers': len(self.requests),
            'total_tracked_requests': sum(len(reqs) for reqs in self.requests.values())
        }

# Global instances
security_validator = SecurityValidator()
rate_limiter = RateLimiter()

def validate_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """Validate filename using global validator."""
    return security_validator.validate_filename(filename)

def validate_file_path(file_path: str, allowed_base_path: str) -> Tuple[bool, Optional[str]]:
    """Validate file path using global validator."""
    return security_validator.validate_file_path(file_path, allowed_base_path)

def validate_file_size(size_bytes: int, file_type: str = 'default') -> Tuple[bool, Optional[str]]:
    """Validate file size using global validator."""
    return security_validator.validate_file_size(size_bytes, file_type)

def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitize input using global validator."""
    return security_validator.sanitize_input(input_str, max_length)

def generate_secure_token(length: int = 32) -> str:
    """Generate secure token using global validator."""
    return security_validator.generate_secure_token(length)

def check_rate_limit(
    identifier: str, 
    max_requests: int = 100, 
    window_seconds: int = 3600
) -> bool:
    """Check rate limit using global rate limiter."""
    return rate_limiter.is_allowed(identifier, max_requests, window_seconds)

def get_remaining_requests(
    identifier: str, 
    max_requests: int = 100, 
    window_seconds: int = 3600
) -> int:
    """Get remaining requests using global rate limiter."""
    return rate_limiter.get_remaining_requests(identifier, max_requests, window_seconds)

def reset_rate_limit(identifier: str):
    """Reset rate limit using global rate limiter."""
    rate_limiter.reset_limit(identifier)
