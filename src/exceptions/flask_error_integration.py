"""Flask integration for standardized error handling."""

import logging
from functools import wraps
from typing import Any, Dict, Optional, Tuple, Union
from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import HTTPException

from .enhanced_error_handler import enhanced_error_handler
from .application_errors import ApplicationError, ErrorSeverity
from ..models.api_responses import ErrorCode

logger = logging.getLogger(__name__)


class FlaskErrorIntegration:
    """Flask integration for standardized error handling."""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize Flask error integration.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize error handling for Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Register error handlers
        self._register_error_handlers()
        
        # Register before/after request handlers
        self._register_request_handlers()
        
        # Add error handling utilities to app context
        app.error_handler = enhanced_error_handler
    
    def _register_error_handlers(self):
        """Register error handlers for different error types."""
        
        @self.app.errorhandler(ApplicationError)
        def handle_application_error(error: ApplicationError):
            """Handle ApplicationError instances."""
            return self._handle_application_error(error)
        
        @self.app.errorhandler(HTTPException)
        def handle_http_exception(error: HTTPException):
            """Handle HTTP exceptions."""
            return self._handle_http_exception(error)
        
        @self.app.errorhandler(Exception)
        def handle_generic_exception(error: Exception):
            """Handle generic exceptions."""
            return self._handle_generic_exception(error)
        
        @self.app.errorhandler(404)
        def handle_not_found(error):
            """Handle 404 errors."""
            return self._handle_not_found_error()
        
        @self.app.errorhandler(500)
        def handle_internal_server_error(error):
            """Handle 500 errors."""
            return self._handle_internal_server_error(error)
    
    def _register_request_handlers(self):
        """Register before/after request handlers."""
        
        @self.app.before_request
        def before_request():
            """Handle before request processing."""
            # Increment request count for error rate tracking
            enhanced_error_handler.increment_request_count()
        
        @self.app.after_request
        def after_request(response):
            """Handle after request processing."""
            # Log successful requests for analytics
            if response.status_code < 400:
                logger.debug(f"Successful request: {request.method} {request.path}")
            
            return response
    
    def _handle_application_error(self, error: ApplicationError) -> Tuple[Dict[str, Any], int]:
        """Handle ApplicationError instances.
        
        Args:
            error: ApplicationError to handle
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        context = self._get_request_context()
        
        # Handle the error
        response_data = enhanced_error_handler.handle_error(
            error=error,
            context=context,
            user_id=self._get_user_id(),
            request_id=self._get_request_id(),
            flash_message=not self._is_api_request(),
            return_response=True
        )
        
        status_code = self._get_status_code_from_error(error)
        
        if self._is_api_request():
            return jsonify(response_data), status_code
        else:
            return self._render_error_page(error, response_data), status_code
    
    def _handle_http_exception(self, error: HTTPException) -> Tuple[Any, int]:
        """Handle HTTP exceptions.
        
        Args:
            error: HTTPException to handle
            
        Returns:
            Tuple of (response, status_code)
        """
        # Convert HTTP exception to ApplicationError
        app_error = self._convert_http_exception_to_app_error(error)
        
        return self._handle_application_error(app_error)
    
    def _handle_generic_exception(self, error: Exception) -> Tuple[Any, int]:
        """Handle generic exceptions.
        
        Args:
            error: Exception to handle
            
        Returns:
            Tuple of (response, status_code)
        """
        # Convert to ApplicationError
        app_error = ApplicationError(
            message=str(error),
            error_code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.HIGH,
            original_error=error
        )
        
        return self._handle_application_error(app_error)
    
    def _handle_not_found_error(self) -> Tuple[Any, int]:
        """Handle 404 not found errors.
        
        Returns:
            Tuple of (response, status_code)
        """
        from .application_errors import NotFoundError
        
        error = NotFoundError(
            f"The requested URL {request.path} was not found",
            resource_type="page",
            resource_id=request.path
        )
        
        return self._handle_application_error(error)
    
    def _handle_internal_server_error(self, error) -> Tuple[Any, int]:
        """Handle 500 internal server errors.
        
        Args:
            error: Original error that caused 500
            
        Returns:
            Tuple of (response, status_code)
        """
        app_error = ApplicationError(
            message="An internal server error occurred",
            error_code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.CRITICAL,
            original_error=error
        )
        
        return self._handle_application_error(app_error)
    
    def _convert_http_exception_to_app_error(self, http_error: HTTPException) -> ApplicationError:
        """Convert HTTP exception to ApplicationError.
        
        Args:
            http_error: HTTPException to convert
            
        Returns:
            ApplicationError instance
        """
        # Map HTTP status codes to error codes
        status_code_mapping = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.AUTHENTICATION_ERROR,
            403: ErrorCode.AUTHORIZATION_ERROR,
            404: ErrorCode.NOT_FOUND,
            422: ErrorCode.PROCESSING_ERROR,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_ERROR,
            503: ErrorCode.SERVICE_UNAVAILABLE,
            504: ErrorCode.TIMEOUT_ERROR
        }
        
        error_code = status_code_mapping.get(http_error.code, ErrorCode.INTERNAL_ERROR)
        
        # Map status codes to severity
        severity_mapping = {
            400: ErrorSeverity.LOW,
            401: ErrorSeverity.MEDIUM,
            403: ErrorSeverity.MEDIUM,
            404: ErrorSeverity.LOW,
            422: ErrorSeverity.MEDIUM,
            429: ErrorSeverity.MEDIUM,
            500: ErrorSeverity.HIGH,
            503: ErrorSeverity.HIGH,
            504: ErrorSeverity.MEDIUM
        }
        
        severity = severity_mapping.get(http_error.code, ErrorSeverity.MEDIUM)
        
        return ApplicationError(
            message=http_error.description or f"HTTP {http_error.code} error",
            error_code=error_code,
            severity=severity,
            original_error=http_error
        )
    
    def _get_request_context(self) -> Dict[str, Any]:
        """Get context information from current request.
        
        Returns:
            Request context dictionary
        """
        context = {
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.content_type,
            'is_api_request': self._is_api_request()
        }
        
        # Add query parameters
        if request.args:
            context['query_params'] = dict(request.args)
        
        # Add form data (excluding sensitive fields)
        if request.form:
            form_data = {}
            sensitive_fields = {'password', 'token', 'secret', 'key'}
            for key, value in request.form.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    form_data[key] = '[REDACTED]'
                else:
                    form_data[key] = value
            context['form_data'] = form_data
        
        return context
    
    def _get_user_id(self) -> Optional[str]:
        """Get user ID from session or request.
        
        Returns:
            User ID if available
        """
        try:
            from flask import session
            return session.get('user_id') or session.get('current_user_id')
        except RuntimeError:
            return None
    
    def _get_request_id(self) -> Optional[str]:
        """Get request ID from headers or generate one.
        
        Returns:
            Request ID
        """
        # Try to get from headers first
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            # Generate a simple request ID
            import uuid
            request_id = str(uuid.uuid4())[:8]
        
        return request_id
    
    def _is_api_request(self) -> bool:
        """Check if current request is an API request.
        
        Returns:
            True if API request, False otherwise
        """
        # Check if request path starts with /api/
        if request.path.startswith('/api/'):
            return True
        
        # Check Accept header
        accept_header = request.headers.get('Accept', '')
        if 'application/json' in accept_header:
            return True
        
        # Check Content-Type header
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return True
        
        return False
    
    def _get_status_code_from_error(self, error: ApplicationError) -> int:
        """Get HTTP status code from ApplicationError.
        
        Args:
            error: ApplicationError instance
            
        Returns:
            HTTP status code
        """
        status_code_mapping = {
            ErrorCode.VALIDATION_ERROR: 400,
            ErrorCode.AUTHENTICATION_ERROR: 401,
            ErrorCode.AUTHORIZATION_ERROR: 403,
            ErrorCode.NOT_FOUND: 404,
            ErrorCode.PROCESSING_ERROR: 422,
            ErrorCode.RATE_LIMIT_EXCEEDED: 429,
            ErrorCode.INTERNAL_ERROR: 500,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
            ErrorCode.TIMEOUT_ERROR: 504
        }
        
        return status_code_mapping.get(error.error_code, 500)
    
    def _render_error_page(self, error: ApplicationError, response_data: Dict[str, Any]) -> str:
        """Render error page for web requests.
        
        Args:
            error: ApplicationError instance
            response_data: Response data from error handler
            
        Returns:
            Rendered HTML template
        """
        try:
            return render_template(
                'error.html',
                error=error,
                error_data=response_data,
                error_code=error.error_code.value,
                error_message=error.user_message,
                show_details=self.app.debug
            )
        except Exception as template_error:
            logger.error(f"Error rendering error template: {template_error}")
            # Fallback to simple HTML
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error {self._get_status_code_from_error(error)}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .error-container {{ max-width: 600px; margin: 0 auto; }}
                    .error-code {{ color: #d32f2f; font-size: 24px; font-weight: bold; }}
                    .error-message {{ margin: 20px 0; font-size: 16px; }}
                    .error-id {{ color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-code">{error.error_code.value}</div>
                    <div class="error-message">{error.user_message}</div>
                    <div class="error-id">Error ID: {error.error_id}</div>
                </div>
            </body>
            </html>
            """


def error_handler_decorator(flash_errors: bool = True):
    """Decorator for automatic error handling in Flask routes.
    
    Args:
        flash_errors: Whether to flash errors to user
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ApplicationError as e:
                # Handle ApplicationError
                context = {
                    'function': func.__name__,
                    'module': func.__module__
                }
                
                response_data = enhanced_error_handler.handle_error(
                    error=e,
                    context=context,
                    flash_message=flash_errors and not request.path.startswith('/api/'),
                    return_response=request.path.startswith('/api/')
                )
                
                if request.path.startswith('/api/'):
                    status_code = enhanced_error_handler._get_http_status_code(e.error_code)
                    return jsonify(response_data), status_code
                else:
                    # For web requests, let Flask's error handler take over
                    raise
            
            except Exception as e:
                # Convert to ApplicationError and handle
                app_error = ApplicationError(
                    message=str(e),
                    error_code=ErrorCode.INTERNAL_ERROR,
                    original_error=e
                )
                
                context = {
                    'function': func.__name__,
                    'module': func.__module__
                }
                
                response_data = enhanced_error_handler.handle_error(
                    error=app_error,
                    context=context,
                    flash_message=flash_errors and not request.path.startswith('/api/'),
                    return_response=request.path.startswith('/api/')
                )
                
                if request.path.startswith('/api/'):
                    return jsonify(response_data), 500
                else:
                    # For web requests, let Flask's error handler take over
                    raise app_error
        
        return wrapper
    return decorator


# Convenience decorator for API endpoints
api_error_handler = error_handler_decorator(flash_errors=False)

# Convenience decorator for web endpoints
web_error_handler = error_handler_decorator(flash_errors=True)