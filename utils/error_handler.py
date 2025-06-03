"""
Enhanced error handling and user feedback system for the Exam Grader application.
"""
import traceback
from typing import Dict, Any, Optional, Tuple
from flask import request, session
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ErrorHandler:
    """Centralized error handling with user-friendly messages."""
    
    # Error categories and their user-friendly messages
    ERROR_MESSAGES = {
        # File-related errors
        'file_not_found': {
            'user_message': 'The requested file could not be found. Please check if the file exists and try again.',
            'suggestions': ['Verify the file path', 'Check file permissions', 'Try uploading the file again']
        },
        'file_too_large': {
            'user_message': 'The file you uploaded is too large. Please use a smaller file.',
            'suggestions': ['Compress the file', 'Use a different file format', 'Split large documents into smaller parts']
        },
        'invalid_file_type': {
            'user_message': 'This file type is not supported. Please use a supported file format.',
            'suggestions': ['Convert to PDF or Word document', 'Use JPG or PNG for images', 'Check the list of supported formats']
        },
        'file_corrupted': {
            'user_message': 'The uploaded file appears to be corrupted or damaged.',
            'suggestions': ['Try uploading the file again', 'Check if the original file opens correctly', 'Use a different file']
        },
        'file_processing_failed': {
            'user_message': 'We encountered an error while processing your file.',
            'suggestions': ['Try uploading the file again', 'Ensure the file is not password-protected', 'Contact support if the problem persists']
        },
        
        # Service-related errors
        'service_unavailable': {
            'user_message': 'A required service is currently unavailable. Please try again later.',
            'suggestions': ['Wait a few minutes and try again', 'Check your internet connection', 'Contact support if the issue persists']
        },
        'ocr_failed': {
            'user_message': 'We could not extract text from your document. The image quality might be too low.',
            'suggestions': ['Use a higher quality scan', 'Ensure text is clearly visible', 'Try a different file format']
        },
        'llm_processing_failed': {
            'user_message': 'The AI processing service encountered an error while analyzing your content.',
            'suggestions': ['Try again in a few moments', 'Check if your content is in a supported language', 'Simplify complex formatting']
        },
        
        # Data-related errors
        'invalid_data': {
            'user_message': 'The provided data is invalid or incomplete.',
            'suggestions': ['Check all required fields are filled', 'Verify data format is correct', 'Remove any special characters']
        },
        'missing_guide': {
            'user_message': 'No marking guide has been uploaded. Please upload a marking guide first.',
            'suggestions': ['Go to the Upload Guide page', 'Ensure your guide contains clear questions and marking criteria']
        },
        'missing_submissions': {
            'user_message': 'No student submissions have been uploaded for grading.',
            'suggestions': ['Upload student submissions first', 'Ensure submissions are in a supported format']
        },
        'mapping_failed': {
            'user_message': 'We could not match the student answers with the marking guide questions.',
            'suggestions': ['Check if the marking guide is clear', 'Ensure student submissions contain recognizable answers', 'Try manual mapping']
        },
        'grading_failed': {
            'user_message': 'The automatic grading process encountered an error.',
            'suggestions': ['Check if the mapping was successful', 'Verify the marking guide has clear criteria', 'Try processing fewer submissions at once']
        },
        
        # Authentication and authorization errors
        'access_denied': {
            'user_message': 'You do not have permission to access this resource.',
            'suggestions': ['Log in with appropriate credentials', 'Contact an administrator for access']
        },
        'session_expired': {
            'user_message': 'Your session has expired. Please refresh the page and try again.',
            'suggestions': ['Refresh the page', 'Log in again if required', 'Save your work frequently']
        },
        
        # Network and connectivity errors
        'network_error': {
            'user_message': 'A network error occurred. Please check your connection and try again.',
            'suggestions': ['Check your internet connection', 'Try refreshing the page', 'Wait a moment and try again']
        },
        'timeout_error': {
            'user_message': 'The operation took too long to complete and was cancelled.',
            'suggestions': ['Try with smaller files', 'Check your internet connection', 'Try again during off-peak hours']
        },
        
        # Rate limiting errors
        'rate_limit_exceeded': {
            'user_message': 'You have made too many requests. Please wait before trying again.',
            'suggestions': ['Wait a few minutes before trying again', 'Avoid rapid successive requests']
        },
        
        # Generic errors
        'unknown_error': {
            'user_message': 'An unexpected error occurred. Please try again or contact support.',
            'suggestions': ['Try refreshing the page', 'Clear your browser cache', 'Contact support with error details']
        }
    }
    
    @staticmethod
    def get_user_friendly_error(error_type: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get user-friendly error message and suggestions.
        
        Args:
            error_type: Type of error from ERROR_MESSAGES keys
            context: Additional context for the error
            
        Returns:
            Dictionary with user message, suggestions, and context
        """
        error_info = ErrorHandler.ERROR_MESSAGES.get(error_type, ErrorHandler.ERROR_MESSAGES['unknown_error'])
        
        result = {
            'type': error_type,
            'message': error_info['user_message'],
            'suggestions': error_info['suggestions'].copy(),
            'timestamp': None,
            'context': context or {}
        }
        
        # Add context-specific information
        if context:
            if 'filename' in context:
                result['message'] = f"{result['message']} (File: {context['filename']})"
            
            if 'max_size' in context:
                result['suggestions'].insert(0, f"Maximum file size is {context['max_size']}MB")
            
            if 'supported_formats' in context:
                formats = ', '.join(context['supported_formats'])
                result['suggestions'].insert(0, f"Supported formats: {formats}")
        
        return result
    
    @staticmethod
    def log_error(error: Exception, error_type: str, context: Optional[Dict] = None) -> str:
        """
        Log error with context and return error ID for tracking.
        
        Args:
            error: The exception that occurred
            error_type: Type of error for categorization
            context: Additional context information
            
        Returns:
            Error ID for tracking
        """
        import uuid
        error_id = str(uuid.uuid4())[:8]
        
        # Gather context information
        error_context = {
            'error_id': error_id,
            'error_type': error_type,
            'error_message': str(error),
            'user_agent': request.headers.get('User-Agent', 'Unknown') if request else 'Unknown',
            'ip_address': request.remote_addr if request else 'Unknown',
            'url': request.url if request else 'Unknown',
            'method': request.method if request else 'Unknown',
            'session_id': session.get('session_id', 'Unknown') if session else 'Unknown'
        }
        
        if context:
            error_context.update(context)
        
        # Log the error with full context
        logger.error(f"Error {error_id}: {error_type} - {str(error)}")
        logger.error(f"Context: {error_context}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return error_id
    
    @staticmethod
    def handle_file_error(error: Exception, filename: str = None) -> Tuple[str, Dict]:
        """
        Handle file-related errors and return appropriate error type and context.
        
        Args:
            error: The exception that occurred
            filename: Name of the file being processed
            
        Returns:
            Tuple of (error_type, context)
        """
        error_str = str(error).lower()
        context = {'filename': filename} if filename else {}
        
        if 'no such file' in error_str or 'file not found' in error_str:
            return 'file_not_found', context
        elif 'file too large' in error_str or 'exceeds size limit' in error_str:
            return 'file_too_large', context
        elif 'not supported' in error_str or 'invalid format' in error_str:
            return 'invalid_file_type', context
        elif 'corrupted' in error_str or 'damaged' in error_str:
            return 'file_corrupted', context
        elif 'permission denied' in error_str:
            return 'access_denied', context
        else:
            return 'file_processing_failed', context
    
    @staticmethod
    def handle_service_error(error: Exception, service_name: str = None) -> Tuple[str, Dict]:
        """
        Handle service-related errors.
        
        Args:
            error: The exception that occurred
            service_name: Name of the service that failed
            
        Returns:
            Tuple of (error_type, context)
        """
        error_str = str(error).lower()
        context = {'service': service_name} if service_name else {}
        
        if 'timeout' in error_str:
            return 'timeout_error', context
        elif 'connection' in error_str or 'network' in error_str:
            return 'network_error', context
        elif 'unavailable' in error_str or 'not available' in error_str:
            return 'service_unavailable', context
        elif service_name == 'ocr' or 'ocr' in error_str:
            return 'ocr_failed', context
        elif service_name == 'llm' or 'llm' in error_str:
            return 'llm_processing_failed', context
        else:
            return 'service_unavailable', context
    
    @staticmethod
    def create_error_response(error_type: str, context: Optional[Dict] = None, 
                            status_code: int = 500) -> Dict[str, Any]:
        """
        Create a standardized error response for API endpoints.
        
        Args:
            error_type: Type of error
            context: Additional context
            status_code: HTTP status code
            
        Returns:
            Error response dictionary
        """
        error_info = ErrorHandler.get_user_friendly_error(error_type, context)
        
        return {
            'success': False,
            'error': {
                'type': error_type,
                'message': error_info['message'],
                'suggestions': error_info['suggestions'],
                'context': error_info['context']
            },
            'status_code': status_code
        }

class ProgressTracker:
    """Track and report progress for long-running operations."""
    
    def __init__(self, total_steps: int, operation_name: str):
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.start_time = None
        self.step_messages = []
    
    def start(self):
        """Start the progress tracking."""
        import time
        self.start_time = time.time()
        logger.info(f"Starting {self.operation_name} with {self.total_steps} steps")
    
    def update(self, step_message: str = None):
        """Update progress to next step."""
        self.current_step += 1
        if step_message:
            self.step_messages.append(step_message)
            logger.info(f"{self.operation_name} - Step {self.current_step}/{self.total_steps}: {step_message}")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        import time
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        progress_percent = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
        
        return {
            'operation': self.operation_name,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percent': round(progress_percent, 1),
            'elapsed_time': round(elapsed_time, 1),
            'recent_messages': self.step_messages[-3:],  # Last 3 messages
            'is_complete': self.current_step >= self.total_steps
        }
    
    def complete(self, final_message: str = None):
        """Mark operation as complete."""
        import time
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        if final_message:
            self.step_messages.append(final_message)
        
        logger.info(f"{self.operation_name} completed in {elapsed_time:.1f} seconds")

def create_user_notification(message: str, notification_type: str = 'info', 
                           auto_dismiss: bool = True, duration: int = 5000) -> Dict[str, Any]:
    """
    Create a user notification for the frontend.
    
    Args:
        message: Notification message
        notification_type: Type of notification (success, error, warning, info)
        auto_dismiss: Whether to auto-dismiss the notification
        duration: Duration in milliseconds before auto-dismiss
        
    Returns:
        Notification dictionary
    """
    import uuid
    
    return {
        'id': str(uuid.uuid4()),
        'message': message,
        'type': notification_type,
        'auto_dismiss': auto_dismiss,
        'duration': duration,
        'timestamp': None
    }
