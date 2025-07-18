"""
Error handling utilities for the Exam Grader application.

This module provides error handling, progress tracking, and
user notification functionality.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional
from flask import session, flash

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling utility."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_log = []
    
    def log_error(self, error: Exception, context: str = "", user_id: str = None):
        """Log error with context information.
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            user_id: User ID if available
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }
        
        self.error_log.append(error_info)
        logger.error(f"Error in {context}: {str(error)}")
        
        # Keep only last 100 errors to prevent memory issues
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error dictionaries
        """
        return self.error_log[-limit:]
    
    def clear_errors(self):
        """Clear error log."""
        self.error_log.clear()
        logger.info("Error log cleared")


class ProgressTracker:
    """Track progress of long-running operations."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.operations = {}
    
    def start_operation(self, operation_id: str, total_steps: int, description: str = ""):
        """Start tracking an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            total_steps: Total number of steps in the operation
            description: Description of the operation
        """
        self.operations[operation_id] = {
            'total_steps': total_steps,
            'current_step': 0,
            'description': description,
            'started_at': datetime.now().isoformat(),
            'status': 'running',
            'errors': []
        }
        logger.info(f"Started operation {operation_id}: {description}")
    
    def update_progress(self, operation_id: str, current_step: int, step_description: str = ""):
        """Update operation progress.
        
        Args:
            operation_id: Operation identifier
            current_step: Current step number
            step_description: Description of current step
        """
        if operation_id in self.operations:
            self.operations[operation_id]['current_step'] = current_step
            self.operations[operation_id]['last_step_description'] = step_description
            self.operations[operation_id]['updated_at'] = datetime.now().isoformat()
    
    def complete_operation(self, operation_id: str, success: bool = True, message: str = ""):
        """Mark operation as complete.
        
        Args:
            operation_id: Operation identifier
            success: Whether operation completed successfully
            message: Completion message
        """
        if operation_id in self.operations:
            self.operations[operation_id]['status'] = 'completed' if success else 'failed'
            self.operations[operation_id]['completed_at'] = datetime.now().isoformat()
            self.operations[operation_id]['completion_message'] = message
            logger.info(f"Operation {operation_id} {'completed' if success else 'failed'}: {message}")
    
    def add_error(self, operation_id: str, error: str):
        """Add error to operation.
        
        Args:
            operation_id: Operation identifier
            error: Error message
        """
        if operation_id in self.operations:
            self.operations[operation_id]['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': error
            })
    
    def get_progress(self, operation_id: str) -> Optional[Dict]:
        """Get operation progress.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Progress dictionary or None if not found
        """
        return self.operations.get(operation_id)
    
    def get_all_operations(self) -> Dict:
        """Get all tracked operations.
        
        Returns:
            Dictionary of all operations
        """
        return self.operations.copy()
    
    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up old completed operations.
        
        Args:
            max_age_hours: Maximum age in hours for keeping operations
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for op_id, op_data in self.operations.items():
            if op_data['status'] in ['completed', 'failed']:
                started_time = datetime.fromisoformat(op_data['started_at']).timestamp()
                if started_time < cutoff_time:
                    to_remove.append(op_id)
        
        for op_id in to_remove:
            del self.operations[op_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old operations")


# Global instances
error_handler = ErrorHandler()
progress_tracker = ProgressTracker()


def handle_error(error: Exception, context: str = "", user_message: str = None, flash_message: bool = True):
    """Handle error with logging and user notification.
    
    Args:
        error: Exception that occurred
        context: Context where error occurred
        user_message: Custom message for user (uses error message if None)
        flash_message: Whether to flash message to user
    """
    # Log the error
    error_handler.log_error(error, context)
    
    # Flash message to user if requested
    if flash_message:
        message = user_message or f"An error occurred: {str(error)}"
        flash(message, 'error')


def create_user_notification(message: str, category: str = 'info', persistent: bool = False):
    """Create user notification.
    
    Args:
        message: Notification message
        category: Message category (info, success, warning, error)
        persistent: Whether notification should persist across requests
    """
    if persistent:
        # Store in session for persistence
        notifications = session.get('persistent_notifications', [])
        notifications.append({
            'message': message,
            'category': category,
            'timestamp': datetime.now().isoformat()
        })
        session['persistent_notifications'] = notifications[-10:]  # Keep last 10
    else:
        # Use flash for temporary notifications
        flash(message, category)


def get_persistent_notifications() -> List[Dict]:
    """Get persistent notifications from session.
    
    Returns:
        List of persistent notifications
    """
    return session.get('persistent_notifications', [])


def clear_persistent_notifications():
    """Clear persistent notifications from session."""
    session.pop('persistent_notifications', None)


def safe_execute(func, *args, context: str = "", default_return=None, **kwargs):
    """Safely execute function with error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        context: Context for error logging
        default_return: Default return value on error
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, context, flash_message=False)
        return default_return


def validate_input(value: Any, validator_func, error_message: str = "Invalid input"):
    """Validate input with custom validator.
    
    Args:
        value: Value to validate
        validator_func: Function that returns True if valid
        error_message: Error message for invalid input
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        ValueError: If validation fails
    """
    try:
        if not validator_func(value):
            raise ValueError(error_message)
        return True
    except Exception as e:
        handle_error(e, "Input validation")
        raise


def format_error_for_user(error: Exception) -> str:
    """Format error message for user display.
    
    Args:
        error: Exception to format
        
    Returns:
        User-friendly error message
    """
    error_type = type(error).__name__
    
    # Map technical errors to user-friendly messages
    user_friendly_messages = {
        'FileNotFoundError': 'The requested file could not be found.',
        'PermissionError': 'Permission denied. Please check file permissions.',
        'ConnectionError': 'Connection error. Please check your internet connection.',
        'TimeoutError': 'Operation timed out. Please try again.',
        'ValueError': 'Invalid input provided. Please check your data.',
        'KeyError': 'Required information is missing.',
        'AttributeError': 'System configuration error. Please contact support.'
    }
    
    return user_friendly_messages.get(error_type, f"An error occurred: {str(error)}")


def add_recent_activity(activity_type: str, message: str, icon: str = 'info'):
    """Add activity to recent activity log.
    
    Args:
        activity_type: Type of activity
        message: Activity message
        icon: Icon for the activity
    """
    try:
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': activity_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'icon': icon
        })
        session['recent_activity'] = activity[:10]  # Keep last 10 activities
        session.modified = True
    except Exception as e:
        logger.error(f"Error adding recent activity: {str(e)}")


def get_recent_activity(limit: int = 10) -> List[Dict]:
    """Get recent activity from session.
    
    Args:
        limit: Maximum number of activities to return
        
    Returns:
        List of recent activities
    """
    try:
        return session.get('recent_activity', [])[:limit]
    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}")
        return []
