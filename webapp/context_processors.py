"""
Flask Context Processors

This module provides context processors that inject user settings and preferences
into all templates automatically.
"""

from flask import g
from flask_login import current_user

from src.services.template_context_service import template_context_service
from utils.logger import logger

def inject_user_settings():
    """Inject user settings into all templates."""
    try:
        if current_user and current_user.is_authenticated:
            # Get comprehensive context with all user settings
            context = template_context_service.get_comprehensive_context()

            # Store in Flask's g object for efficient access
            g.user_settings_context = context

            return context
        else:
            # Return default context for anonymous users
            default_context = {
                'current_theme': 'light',
                'body_classes': '',
                'show_tooltips': True,
                'auto_save': False,
                'language': 'en',
                'max_file_size_display': '100 MB',
                'allowed_formats_display': '.pdf, .jpg, .png, .docx, .doc, .txt',
                'default_per_page': 10,
                'notification_settings': {
                    'email_notifications': True,
                    'processing_notifications': True,
                    'notification_level': 'info'
                }
            }
            g.user_settings_context = default_context
            return default_context

    except Exception as e:
        logger.warning(f"Failed to inject user settings context: {e}")
        # Return minimal safe context
        safe_context = {
            'current_theme': 'light',
            'body_classes': '',
            'show_tooltips': True,
            'auto_save': False,
            'language': 'en'
        }
        g.user_settings_context = safe_context
        return safe_context

def inject_file_validation_info():
    """Inject file validation information for upload forms."""
    try:
        if hasattr(g, 'user_settings_context'):
            # Already loaded in inject_user_settings
            return {}

        from src.services.file_validation_service import file_validation_service
        validation_info = file_validation_service.get_validation_info()

        return {
            'file_validation_info': validation_info,
            'upload_constraints': {
                'max_size': validation_info.get('max_file_size_display', '100 MB'),
                'allowed_formats': ', '.join(validation_info.get('allowed_formats', []))
            }
        }
    except Exception as e:
        logger.warning(f"Failed to inject file validation info: {e}")
        return {
            'file_validation_info': {
                'max_file_size_mb': 100,
                'allowed_formats': ['.pdf', '.jpg', '.png'],
                'max_file_size_display': '100 MB'
            },
            'upload_constraints': {
                'max_size': '100 MB',
                'allowed_formats': '.pdf, .jpg, .png'
            }
        }

def inject_theme_variables():
    """Inject theme variables for CSS customization."""
    try:
        if hasattr(g, 'user_settings_context') and 'theme_variables' in g.user_settings_context:
            return {'theme_vars': g.user_settings_context['theme_variables']}

        from src.services.theme_service import theme_service
        return {'theme_vars': theme_service.get_theme_variables()}
    except Exception as e:
        logger.warning(f"Failed to inject theme variables: {e}")
        return {'theme_vars': {}}

def inject_ui_preferences():
    """Inject UI preferences for JavaScript and template logic."""
    try:
        if hasattr(g, 'user_settings_context'):
            context = g.user_settings_context
            return {
                'ui_prefs': {
                    'show_tooltips': context.get('show_tooltips', True),
                    'auto_save': context.get('auto_save', False),
                    'language': context.get('language', 'en'),
                    'theme': context.get('current_theme', 'light'),
                    'results_per_page': context.get('default_per_page', 10)
                }
            }

        return {
            'ui_prefs': {
                'show_tooltips': True,
                'auto_save': False,
                'language': 'en',
                'theme': 'light',
                'results_per_page': 10
            }
        }
    except Exception as e:
        logger.warning(f"Failed to inject UI preferences: {e}")
        return {'ui_prefs': {'show_tooltips': True, 'auto_save': False}}

def register_context_processors(app):
    """Register all context processors with the Flask app."""
    app.context_processor(inject_user_settings)
    app.context_processor(inject_file_validation_info)
    app.context_processor(inject_theme_variables)
    app.context_processor(inject_ui_preferences)

    logger.info("Registered user settings context processors")