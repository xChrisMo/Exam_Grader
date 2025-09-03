"""Application Configuration Service - Centralized configuration management."""

from typing import Dict, List, Union

from src.config.unified_config import UnifiedConfig
from utils.logger import logger


class AppConfigService:
    """Service for managing application configuration and removing hardcoded values."""
    
    def __init__(self):
        """Initialize the configuration service."""
        try:
            self.config = UnifiedConfig()
        except Exception as e:
            logger.error(f"Failed to load unified config: {e}")
            self.config = None
    
    def get_allowed_file_types(self) -> List[str]:
        """Get allowed file types from configuration."""
        try:
            if self.config and hasattr(self.config, 'file_processing'):
                return self.config.file_processing.allowed_extensions
        except Exception as e:
            logger.debug(f"Could not get allowed file types from config: {e}")
        
        # Fallback to reasonable defaults
        return [
            ".pdf", ".docx", ".doc", ".txt", 
            ".jpg", ".jpeg", ".png", ".bmp", 
            ".tiff", ".gif"
        ]
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes from configuration."""
        try:
            if self.config and hasattr(self.config, 'file_processing'):
                return self.config.file_processing.max_file_size_mb * 1024 * 1024
        except Exception as e:
            logger.debug(f"Could not get max file size from config: {e}")
        
        # Fallback to 100MB
        return 100 * 1024 * 1024
    
    def get_max_file_size_mb(self) -> int:
        """Get maximum file size in MB from configuration."""
        return self.get_max_file_size() // (1024 * 1024)
    
    def get_default_theme(self) -> str:
        """Get default theme from configuration."""
        try:
            if self.config and hasattr(self.config, 'ui'):
                return self.config.ui.default_theme
        except Exception as e:
            logger.debug(f"Could not get default theme from config: {e}")
        
        return "light"
    
    def get_default_language(self) -> str:
        """Get default language from configuration."""
        try:
            if self.config and hasattr(self.config, 'ui'):
                return self.config.ui.default_language
        except Exception as e:
            logger.debug(f"Could not get default language from config: {e}")
        
        return "en"
    
    def get_available_themes(self) -> List[Dict[str, str]]:
        """Get available themes."""
        return [
            {"value": "light", "label": "Light"},
            {"value": "dark", "label": "Dark"},
            {"value": "auto", "label": "Auto"},
        ]
    
    def get_available_languages(self) -> List[Dict[str, str]]:
        """Get available languages."""
        return [
            {"value": "en", "label": "English"},
            {"value": "es", "label": "Spanish"},
            {"value": "fr", "label": "French"},
            {"value": "de", "label": "German"},
        ]
    
    def get_notification_levels(self) -> List[Dict[str, str]]:
        """Get available notification levels."""
        return [
            {"value": "error", "label": "Errors Only"},
            {"value": "warning", "label": "Warnings and Errors"},
            {"value": "info", "label": "All Notifications"},
        ]
    
    def get_default_results_per_page(self) -> int:
        """Get default results per page."""
        try:
            if self.config and hasattr(self.config, 'ui'):
                return getattr(self.config.ui, 'results_per_page', 10)
        except Exception as e:
            logger.debug(f"Could not get results per page from config: {e}")
        
        return 10
    
    def get_text_preview_length(self) -> int:
        """Get text preview length for truncation."""
        try:
            if self.config and hasattr(self.config, 'ui'):
                return getattr(self.config.ui, 'text_preview_length', 500)
        except Exception as e:
            logger.debug(f"Could not get text preview length from config: {e}")
        
        return 500


# Global instance
app_config = AppConfigService()


def get_template_context() -> Dict[str, Union[List, int, str]]:
    """Get common template context variables."""
    return {
        "allowed_types": app_config.get_allowed_file_types(),
        "max_file_size": app_config.get_max_file_size(),
        "max_file_size_mb": app_config.get_max_file_size_mb(),
    }