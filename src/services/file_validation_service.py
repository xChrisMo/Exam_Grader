"""
File Validation Service

This service validates uploaded files against user settings including:
- Maximum file size limits
- Allowed file formats
- File type validation
"""

import os
from typing import List, Tuple, Optional
from werkzeug.datastructures import FileStorage
from flask_login import current_user

from src.database.models import UserSettings
from utils.logger import logger


class FileValidationError(Exception):
    """Exception raised for file validation errors."""
    pass


class FileValidationService:
    """Service for validating uploaded files against user settings."""
    
    def __init__(self):
        self.default_max_size_mb = 100
        self.default_allowed_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc', '.txt']
    
    def get_user_settings(self) -> dict:
        """Get current user's file validation settings."""
        try:
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                return user_settings.to_dict()
            else:
                return UserSettings.get_default_settings()
        except Exception as e:
            logger.warning(f"Failed to get user settings for file validation: {e}")
            return UserSettings.get_default_settings()
    
    def validate_file(self, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        Validate a single file against user settings.
        
        Args:
            file: The uploaded file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            settings = self.get_user_settings()
            
            # Check if file exists and has a filename
            if not file or not file.filename:
                return False, "No file selected"
            
            filename = file.filename.lower()
            
            # Check file extension
            allowed_formats = self._parse_allowed_formats(settings.get('allowed_formats', ''))
            if not self._is_format_allowed(filename, allowed_formats):
                allowed_str = ', '.join(allowed_formats)
                return False, f"File format not allowed. Allowed formats: {allowed_str}"
            
            # Check file size
            max_size_mb = settings.get('max_file_size', self.default_max_size_mb)
            if not self._is_size_valid(file, max_size_mb):
                return False, f"File size exceeds maximum limit of {max_size_mb} MB"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file: {e}")
            return False, f"File validation error: {str(e)}"
    
    def validate_files(self, files: List[FileStorage]) -> Tuple[List[FileStorage], List[str]]:
        """
        Validate multiple files against user settings.
        
        Args:
            files: List of uploaded files to validate
            
        Returns:
            Tuple of (valid_files, error_messages)
        """
        valid_files = []
        errors = []
        
        for file in files:
            is_valid, error_msg = self.validate_file(file)
            if is_valid:
                valid_files.append(file)
            else:
                errors.append(f"{file.filename}: {error_msg}")
        
        return valid_files, errors
    
    def _parse_allowed_formats(self, formats_string: str) -> List[str]:
        """Parse allowed formats string into a list."""
        if not formats_string:
            return self.default_allowed_formats
        
        formats = [fmt.strip().lower() for fmt in formats_string.split(',') if fmt.strip()]
        
        # Ensure formats start with a dot
        normalized_formats = []
        for fmt in formats:
            if not fmt.startswith('.'):
                fmt = '.' + fmt
            normalized_formats.append(fmt)
        
        return normalized_formats if normalized_formats else self.default_allowed_formats
    
    def _is_format_allowed(self, filename: str, allowed_formats: List[str]) -> bool:
        """Check if file format is allowed."""
        if not filename or '.' not in filename:
            return False
        
        file_ext = '.' + filename.split('.')[-1].lower()
        return file_ext in allowed_formats
    
    def _is_size_valid(self, file: FileStorage, max_size_mb: float) -> bool:
        """Check if file size is within limits."""
        try:
            # Handle infinite file size (no limit)
            if max_size_mb == float('inf'):
                return True
            
            # Get file size
            file.seek(0, os.SEEK_END)
            file_size_bytes = file.tell()
            file.seek(0)  # Reset file pointer
            
            file_size_mb = file_size_bytes / (1024 * 1024)
            return file_size_mb <= max_size_mb
            
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return False
    
    def get_validation_info(self) -> dict:
        """Get current validation settings for display to user."""
        settings = self.get_user_settings()
        allowed_formats = self._parse_allowed_formats(settings.get('allowed_formats', ''))
        max_size_mb = settings.get('max_file_size', self.default_max_size_mb)
        
        return {
            'max_file_size_mb': max_size_mb,
            'allowed_formats': allowed_formats,
            'max_file_size_display': 'No limit' if max_size_mb == float('inf') else f"{max_size_mb} MB"
        }


# Global instance
file_validation_service = FileValidationService()