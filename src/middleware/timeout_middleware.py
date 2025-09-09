"""
Timeout Middleware for Long-Running AI Operations

This middleware handles extended timeouts for AI processing operations
and provides proper error handling for timeout scenarios.
"""

import os
import time
import signal
from functools import wraps
from typing import Callable, Optional

from flask import current_app, jsonify, request
from werkzeug.exceptions import RequestTimeout

from utils.logger import logger

class TimeoutMiddleware:
    """Middleware to handle request timeouts for AI operations."""

    def __init__(self, app=None, default_timeout: int = 600):
        """Initialize timeout middleware.

        Args:
            app: Flask application instance
            default_timeout: Default timeout in seconds (10 minutes)
        """
        self.default_timeout = default_timeout
        self.ai_endpoints = {
            '/processing/api/process',
            '/api/process',
            '/processing/process',
            '/api/grade',
            '/api/ocr',
            '/api/mapping'
        }

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the middleware with Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

        # Store timeout settings in app config
        app.config.setdefault('AI_REQUEST_TIMEOUT', self.default_timeout)
        app.config.setdefault('STANDARD_REQUEST_TIMEOUT', 30)

    def before_request(self):
        """Set up timeout handling before request processing."""
        # Check if this is an AI processing endpoint
        if self.is_ai_endpoint(request.endpoint, request.path):
            timeout = current_app.config.get('AI_REQUEST_TIMEOUT', self.default_timeout)
            logger.info(f"Setting extended timeout ({timeout}s) for AI endpoint: {request.path}")

            # Store start time for monitoring
            request.start_time = time.time()
            request.timeout_duration = timeout
        else:
            # Standard timeout for regular endpoints
            timeout = current_app.config.get('STANDARD_REQUEST_TIMEOUT', 30)
            request.start_time = time.time()
            request.timeout_duration = timeout

    def after_request(self, response):
        """Clean up after request processing."""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time

            if duration > 60:  # Log slow requests (over 1 minute)
                logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
            elif self.is_ai_endpoint(request.endpoint, request.path):
                logger.info(f"AI request completed: {request.path} took {duration:.2f}s")

        return response

    def is_ai_endpoint(self, endpoint: Optional[str], path: str) -> bool:
        """Check if the current request is for an AI processing endpoint."""
        if not endpoint and not path:
            return False

        # Check by path
        for ai_path in self.ai_endpoints:
            if path.startswith(ai_path):
                return True

        # Check by endpoint name
        if endpoint:
            ai_endpoint_names = {
                'processing.api_process_single',
                'processing.process',
                'api.grade_submission',
                'api.ocr_process',
                'api.map_answers'
            }
            if endpoint in ai_endpoint_names:
                return True

        return False

def with_timeout(timeout_seconds: int = None):
    """Decorator to add timeout handling to specific functions.

    Args:
        timeout_seconds: Timeout in seconds (uses default if None)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get timeout from decorator, environment, or default
            timeout = (
                timeout_seconds or
                int(os.getenv('REQUEST_TIMEOUT', 600))
            )

            def timeout_handler(signum, frame):
                logger.error(f"Function {func.__name__} timed out after {timeout} seconds")
                raise RequestTimeout(f"Operation timed out after {timeout} seconds")

            # Set up timeout (Unix-like systems only)
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    signal.alarm(0)  # Cancel the alarm
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # Windows fallback - no signal-based timeout
                logger.warning("Signal-based timeout not available on Windows")
                return func(*args, **kwargs)

        return wrapper
    return decorator

def create_timeout_response(message: str = "Request timed out", status_code: int = 408):
    """Create a standardized timeout response."""
    return jsonify({
        'success': False,
        'error': message,
        'error_type': 'timeout',
        'message': 'The operation took too long to complete. Please try again with a smaller file or simpler content.',
        'suggestions': [
            'Try processing smaller files',
            'Break large submissions into smaller parts',
            'Check your internet connection',
            'Contact support if the problem persists'
        ]
    }), status_code

# Global timeout middleware instance
timeout_middleware = TimeoutMiddleware()