"""
Theme Service

This service handles UI theming based on user settings including:
- Theme selection (light/dark)
- CSS class generation
- Theme-specific configurations
"""

from typing import Dict, Any, List
from flask_login import current_user

from src.database.models import UserSettings
from utils.logger import logger


class ThemeService:
    """Service for handling UI themes based on user settings."""
    
    def __init__(self):
        self.available_themes = {
            'light': {
                'name': 'Light',
                'css_classes': 'theme-light',
                'primary_color': '#3b82f6',
                'background_color': '#ffffff',
                'text_color': '#1f2937'
            },
            'dark': {
                'name': 'Dark',
                'css_classes': 'theme-dark bg-gray-900 text-white',
                'primary_color': '#60a5fa',
                'background_color': '#111827',
                'text_color': '#f9fafb'
            },
            'auto': {
                'name': 'Auto (System)',
                'css_classes': 'theme-auto',
                'primary_color': '#3b82f6',
                'background_color': 'var(--bg-color)',
                'text_color': 'var(--text-color)'
            }
        }
    
    def get_user_theme(self) -> str:
        """Get current user's theme setting."""
        try:
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                return user_settings.theme or 'light'
            else:
                return 'light'
        except Exception as e:
            logger.warning(f"Failed to get user theme: {e}")
            return 'light'
    
    def get_theme_config(self, theme_name: str = None) -> Dict[str, Any]:
        """Get theme configuration."""
        if theme_name is None:
            theme_name = self.get_user_theme()
        
        return self.available_themes.get(theme_name, self.available_themes['light'])
    
    def get_body_classes(self) -> str:
        """Get CSS classes for the body element."""
        theme_config = self.get_theme_config()
        return theme_config.get('css_classes', '')
    
    def get_theme_variables(self) -> Dict[str, str]:
        """Get CSS variables for the current theme."""
        theme_config = self.get_theme_config()
        return {
            '--primary-color': theme_config.get('primary_color', '#3b82f6'),
            '--bg-color': theme_config.get('background_color', '#ffffff'),
            '--text-color': theme_config.get('text_color', '#1f2937')
        }
    
    def get_available_themes(self) -> List[Dict[str, str]]:
        """Get list of available themes for settings dropdown."""
        return [
            {'value': key, 'label': config['name']}
            for key, config in self.available_themes.items()
        ]


# Global instance
theme_service = ThemeService()