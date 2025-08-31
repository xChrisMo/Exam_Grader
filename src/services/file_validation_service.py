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
            logger.debug(f"Getting user settings, current_user authenticated: {current_user.is_authenticated if current_user else False}")
            
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                if user_settings:
                    settings_dict = user_settings.to_dict()
                    logger.debug(f"User settings retrieved: max_file_size={settings_dict.get('max_file_size')}")
                    return settings_dict
                else:
                    logger.debug("No user settings found, creating default")
            else:
                logger.debug("No authenticated user, using default settings")
            
            # Fallback to default settings
            default_settings = UserSettings.get_default_settings()
            logger.debug(f"Default settings: max_file_size={default_settings.get('max_file_size')}")
            return default_settings
            
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            import traceback
            logger.error(f"Settings error stack trace: {traceback.format_exc()}")
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
            max_size_mb = settings.get('max_file_size')
            logger.debug(f"File validation: max_file_size from settings = {max_size_mb} (type: {type(max_size_mb)})")
            
            # If max_file_size is None (unlimited), use None; otherwise use default if not set
            if max_size_mb is None:
                # None means unlimited - this is the intended behavior
                logger.debug("File validation: Using unlimited file size")
                pass  # Will be handled in _is_size_valid
            elif max_size_mb == 0:
                # 0 also means unlimited in some contexts
                logger.debug("File validation: Converting 0 to unlimited")
                max_size_mb = None
            # If max_size_mb is still None after settings, it means unlimited
            
            logger.debug(f"File validation: Final max_size_mb = {max_size_mb}")
            if not self._is_size_valid(file, max_size_mb):
                if max_size_mb is None or max_size_mb == float('inf'):
                    size_limit_str = "unlimited"
                else:
                    size_limit_str = f"{max_size_mb} MB"
                return False, f"File size exceeds maximum limit of {size_limit_str}"
            
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
        """Check if file size is within limits with comprehensive None protection."""
        try:
            # Layer 1: Handle None or infinite file size (no limit)
            if max_size_mb is None or max_size_mb == float('inf'):
                logger.debug(f"File size validation: unlimited (max_size_mb={max_size_mb})")
                return True
            
            # Layer 2: Additional safety check for invalid types
            if not isinstance(max_size_mb, (int, float)):
                logger.warning(f"Invalid max_size_mb type: {type(max_size_mb)}, value: {max_size_mb}")
                return True  # Default to allowing the file if we can't validate
            
            # Get file size
            file.seek(0, os.SEEK_END)
            file_size_bytes = file.tell()
            file.seek(0)  # Reset file pointer
            
            file_size_mb = file_size_bytes / (1024 * 1024)
            logger.debug(f"File size validation: {file_size_mb:.2f} MB <= {max_size_mb} MB")
            
            # Layer 3: Final safety check before comparison
            if max_size_mb is None or not isinstance(max_size_mb, (int, float)):
                logger.debug("Layer 3 None check triggered")
                return True
            
            # Layer 4: Triple check to prevent any None comparison
            if max_size_mb is None or max_size_mb == 'None' or str(max_size_mb).lower() == 'none':
                logger.debug("Layer 4 None check triggered")
                return True
            
            # Layer 5: Convert to float if it's a string number
            if isinstance(max_size_mb, str):
                try:
                    max_size_mb = float(max_size_mb)
                except ValueError:
                    logger.warning(f"Could not convert max_size_mb string to float: {max_size_mb}")
                    return True
            
            # Layer 6: Final type check
            if not isinstance(max_size_mb, (int, float)):
                logger.warning(f"Layer 6: max_size_mb is not a number: {max_size_mb} (type: {type(max_size_mb)})")
                return True
            
            # Layer 7: Protected comparison with exception handling
            try:
                result = file_size_mb <= max_size_mb
                return result
            except TypeError as te:
                logger.error(f"Type error in file size comparison: {te}, file_size_mb={file_size_mb}, max_size_mb={max_size_mb}")
                return True  # Default to allowing the file
            
        except Exception as e:
            import traceback
            logger.error(f"Error checking file size: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            logger.error(f"max_size_mb value: {max_size_mb} (type: {type(max_size_mb)})")
            logger.error(f"Function arguments - file: {file}, max_size_mb: {max_size_mb}")
            
            # If it's the specific TypeError we're trying to fix, provide more info
            if "'<=' not supported between instances of 'float' and 'NoneType'" in str(e):
                logger.error("CAUGHT THE SPECIFIC ERROR! This should not happen with our fixes.")
                logger.error(f"File object: {type(file)}, filename: {getattr(file, 'filename', 'unknown')}")
                
            return False
    
    def get_validation_info(self) -> dict:
        """Get current validation settings for display to user."""
        settings = self.get_user_settings()
        allowed_formats = self._parse_allowed_formats(settings.get('allowed_formats', ''))
        max_size_mb = settings.get('max_file_size')
        
        # Handle None (unlimited) and display formatting
        if max_size_mb is None or max_size_mb == float('inf'):
            max_size_display = 'No limit'
            max_size_value = None
        else:
            max_size_display = f"{max_size_mb} MB"
            max_size_value = max_size_mb
        
        return {
            'max_file_size_mb': max_size_value,
            'allowed_formats': allowed_formats,
            'max_file_size_display': max_size_display
        }


# Global instance
file_validation_service = FileValidationService()