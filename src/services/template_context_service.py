"""
Template Context Service

This service provides template context with user settings integration including:
- Theme settings
- Notification settings
- File validation info
- Pagination settings
- All user preferences
"""

from typing import Dict, Any
from flask_login import current_user

from src.database.models import UserSettings
from src.services.theme_service import theme_service
from src.services.notification_service import notification_service
from src.services.file_validation_service import file_validation_service
from src.services.pagination_service import pagination_service
from utils.logger import logger

class TemplateContextService:
    """Service for providing comprehensive template context with user settings."""

    def __init__(self):
        self.base_context = {
            'app_name': 'Exam Grader',
            'app_version': '1.0.0'
        }

    def get_user_settings_context(self) -> Dict[str, Any]:
        """Get user settings for template context."""
        try:
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                return user_settings.to_dict()
            else:
                return UserSettings.get_default_settings()
        except Exception as e:
            logger.warning(f"Failed to get user settings for template context: {e}")
            return UserSettings.get_default_settings()

    def get_theme_context(self) -> Dict[str, Any]:
        """Get theme-related context."""
        try:
            theme_config = theme_service.get_theme_config()
            return {
                'current_theme': theme_service.get_user_theme(),
                'theme_config': theme_config,
                'body_classes': theme_service.get_body_classes(),
                'theme_variables': theme_service.get_theme_variables(),
                'available_themes': theme_service.get_available_themes()
            }
        except Exception as e:
            logger.warning(f"Failed to get theme context: {e}")
            return {
                'current_theme': 'light',
                'theme_config': {'name': 'Light', 'css_classes': ''},
                'body_classes': '',
                'theme_variables': {},
                'available_themes': [{'value': 'light', 'label': 'Light'}]
            }

    def get_notification_context(self) -> Dict[str, Any]:
        """Get notification-related context."""
        try:
            settings = notification_service.get_user_notification_settings()
            return {
                'notification_settings': settings,
                'notification_levels': notification_service.get_available_levels()
            }
        except Exception as e:
            logger.warning(f"Failed to get notification context: {e}")
            return {
                'notification_settings': {
                    'email_notifications': True,
                    'processing_notifications': True,
                    'notification_level': 'info'
                },
                'notification_levels': [{'value': 'info', 'label': 'Info'}]
            }

    def get_file_validation_context(self) -> Dict[str, Any]:
        """Get file validation context."""
        try:
            validation_info = file_validation_service.get_validation_info()
            return {
                'file_validation': validation_info,
                'max_file_size_display': validation_info.get('max_file_size_display', '100 MB'),
                'allowed_formats_display': ', '.join(validation_info.get('allowed_formats', ['.pdf', '.jpg', '.png']))
            }
        except Exception as e:
            logger.warning(f"Failed to get file validation context: {e}")
            return {
                'file_validation': {
                    'max_file_size_mb': 100,
                    'allowed_formats': ['.pdf', '.jpg', '.png'],
                    'max_file_size_display': '100 MB'
                },
                'max_file_size_display': '100 MB',
                'allowed_formats_display': '.pdf, .jpg, .png'
            }

    def get_pagination_context(self) -> Dict[str, Any]:
        """Get pagination context."""
        try:
            per_page = pagination_service.get_user_per_page()
            return {
                'default_per_page': per_page,
                'pagination_options': [
                    {'value': 5, 'label': '5 per page'},
                    {'value': 10, 'label': '10 per page'},
                    {'value': 25, 'label': '25 per page'},
                    {'value': 50, 'label': '50 per page'},
                    {'value': 100, 'label': '100 per page'}
                ]
            }
        except Exception as e:
            logger.warning(f"Failed to get pagination context: {e}")
            return {
                'default_per_page': 10,
                'pagination_options': [{'value': 10, 'label': '10 per page'}]
            }

    def get_ui_preferences_context(self) -> Dict[str, Any]:
        """Get UI preferences context."""
        try:
            settings = self.get_user_settings_context()
            return {
                'show_tooltips': settings.get('show_tooltips', True),
                'auto_save': settings.get('auto_save', False),
                'language': settings.get('language', 'en'),
                'available_languages': [
                    {'value': 'en', 'label': 'English'},
                    {'value': 'es', 'label': 'Español'},
                    {'value': 'fr', 'label': 'Français'},
                    {'value': 'de', 'label': 'Deutsch'}
                ]
            }
        except Exception as e:
            logger.warning(f"Failed to get UI preferences context: {e}")
            return {
                'show_tooltips': True,
                'auto_save': False,
                'language': 'en',
                'available_languages': [{'value': 'en', 'label': 'English'}]
            }

    def get_comprehensive_context(self) -> Dict[str, Any]:
        """Get comprehensive template context with all user settings integrated."""
        context = self.base_context.copy()

        # Add all context sections
        context.update(self.get_theme_context())
        context.update(self.get_notification_context())
        context.update(self.get_file_validation_context())
        context.update(self.get_pagination_context())
        context.update(self.get_ui_preferences_context())

        # Add user settings
        context['user_settings'] = self.get_user_settings_context()

        # Add service availability
        try:
            from webapp.routes.main_routes import get_actual_service_status
            context['service_status'] = get_actual_service_status()
        except Exception as e:
            logger.warning(f"Failed to get service status: {e}")
            context['service_status'] = {
                'ocr_status': False,
                'llm_status': False,
                'ai_status': False
            }

        return context

# Global instance
template_context_service = TemplateContextService()