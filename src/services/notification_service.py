"""
Notification Service

This service handles notifications based on user settings including:
- Email notifications
- Processing notifications
- Notification levels
- Flash message filtering
"""

import logging
from typing import Dict, Any, Optional, List
from flask import flash
from flask_login import current_user

from src.database.models import UserSettings
from utils.logger import logger

class NotificationService:
    """Service for handling notifications based on user settings."""

    def __init__(self):
        self.notification_levels = {
            'debug': 10,
            'info': 20,
            'warning': 30,
            'error': 40,
            'critical': 50
        }

        self.level_colors = {
            'debug': 'info',
            'info': 'info',
            'warning': 'warning',
            'error': 'error',
            'critical': 'error'
        }

    def get_user_notification_settings(self) -> Dict[str, Any]:
        """Get current user's notification settings."""
        try:
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                return {
                    'email_notifications': user_settings.email_notifications,
                    'processing_notifications': user_settings.processing_notifications,
                    'notification_level': user_settings.notification_level or 'info'
                }
            else:
                return {
                    'email_notifications': True,
                    'processing_notifications': True,
                    'notification_level': 'info'
                }
        except Exception as e:
            logger.warning(f"Failed to get user notification settings: {e}")
            return {
                'email_notifications': True,
                'processing_notifications': True,
                'notification_level': 'info'
            }

    def should_show_notification(self, level: str) -> bool:
        """Check if notification should be shown based on user's level setting."""
        settings = self.get_user_notification_settings()
        user_level = settings.get('notification_level', 'info')

        user_level_value = self.notification_levels.get(user_level, 20)
        notification_level_value = self.notification_levels.get(level, 20)

        return notification_level_value >= user_level_value

    def flash_message(self, message: str, level: str = 'info', force: bool = False):
        """
        Show flash message if user's notification level allows it.

        Args:
            message: Message to display
            level: Notification level (debug, info, warning, error, critical)
            force: Show message regardless of user settings
        """
        if force or self.should_show_notification(level):
            flask_category = self.level_colors.get(level, 'info')
            flash(message, flask_category)

    def notify_processing_start(self, process_name: str, details: str = ""):
        """Notify user that processing has started."""
        settings = self.get_user_notification_settings()

        if settings.get('processing_notifications', True):
            message = f"Started {process_name}"
            if details:
                message += f": {details}"
            self.flash_message(message, 'info')

    def notify_processing_complete(self, process_name: str, success: bool = True, details: str = ""):
        """Notify user that processing has completed."""
        settings = self.get_user_notification_settings()

        if settings.get('processing_notifications', True):
            if success:
                message = f"Completed {process_name}"
                level = 'info'
            else:
                message = f"Failed {process_name}"
                level = 'error'

            if details:
                message += f": {details}"

            self.flash_message(message, level)

    def notify_processing_error(self, process_name: str, error_message: str):
        """Notify user of processing error."""
        settings = self.get_user_notification_settings()

        if settings.get('processing_notifications', True):
            message = f"Error in {process_name}: {error_message}"
            self.flash_message(message, 'error')

    def send_email_notification(self, subject: str, message: str, level: str = 'info'):
        """
        Send email notification if user has email notifications enabled.

        Note: This is a placeholder for actual email implementation.
        """
        settings = self.get_user_notification_settings()

        if settings.get('email_notifications', False) and self.should_show_notification(level):
            # TODO: Implement actual email sending
            logger.info(f"Email notification would be sent: {subject} - {message}")

    def get_available_levels(self) -> List[Dict[str, str]]:
        """Get list of available notification levels for settings dropdown."""
        return [
            {'value': 'debug', 'label': 'Debug (All messages)'},
            {'value': 'info', 'label': 'Info (Normal messages)'},
            {'value': 'warning', 'label': 'Warning (Important messages only)'},
            {'value': 'error', 'label': 'Error (Errors and critical only)'},
            {'value': 'critical', 'label': 'Critical (Critical messages only)'}
        ]

# Global instance
notification_service = NotificationService()