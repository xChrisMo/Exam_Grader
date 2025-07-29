"""Flask Integration for Comprehensive Logging System.

This module provides Flask-specific logging integration, including
request/response logging, error handling, and performance monitoring.
"""

import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional, Callable, List
from werkzeug.exceptions import HTTPException
import psutil
import os

try:
    from flask import Flask, request, g, session
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from flask import Flask
    else:
        Flask = None
    request = None
    g = None
    session = None

try:
    from .comprehensive_logger import ComprehensiveLogger, LogLevel, LogContext
    from .structured_logger import get_structured_logger
    from ..exceptions.application_errors import ApplicationError
except ImportError:
    ComprehensiveLogger = None
    LogLevel = None
    LogContext = None
    get_structured_logger = None
    StructuredLogger = None
    get_structured_logger = None
    ApplicationError = Exception

class FlaskLoggingIntegration:
    """Flask logging integration with comprehensive logging system."""
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        logger_name: str = 'flask_app',
        log_requests: bool = True,
        log_responses: bool = True,
        log_performance: bool = True,
        log_errors: bool = True,
        exclude_paths: Optional[List[str]] = None,
        sensitive_headers: Optional[List[str]] = None
    ):
        """Initialize Flask logging integration.
        
        Args:
            app: Flask application instance
            logger_name: Name for the logger
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses
            log_performance: Whether to log performance metrics
            log_errors: Whether to log errors
            exclude_paths: Paths to exclude from logging
            sensitive_headers: Headers to exclude from logs
        """
        self.logger_name = logger_name
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_performance = log_performance
        self.log_errors = log_errors
        self.exclude_paths = exclude_paths or ['/health', '/favicon.ico']
        self.sensitive_headers = sensitive_headers or [
            'authorization', 'cookie', 'x-api-key', 'x-auth-token'
        ]
        
        # Initialize loggers
        if ComprehensiveLogger:
            self.comprehensive_logger = ComprehensiveLogger(logger_name)
        else:
            self.comprehensive_logger = None
        
        if get_structured_logger:
            self.structured_logger = get_structured_logger(f"{logger_name}_structured")
        else:
            self.structured_logger = None
        
        # Request tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize logging integration with Flask app.
        
        Args:
            app: Flask application instance
        """
        # Store reference to integration in app
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['logging_integration'] = self
        
        # Register handlers
        if self.log_requests or self.log_performance:
            app.before_request(self._before_request)
        
        if self.log_responses or self.log_performance:
            app.after_request(self._after_request)
        
        if self.log_errors:
            app.errorhandler(Exception)(self._handle_exception)
            app.errorhandler(HTTPException)(self._handle_http_exception)
            app.errorhandler(ApplicationError)(self._handle_application_error)
        
        # Register teardown handler
        app.teardown_appcontext(self._teardown_request)
    
    def _should_log_path(self, path: str) -> bool:
        """Check if path should be logged.
        
        Args:
            path: Request path
        
        Returns:
            True if path should be logged
        """
        return not any(excluded in path for excluded in self.exclude_paths)
    
    def _get_request_id(self) -> str:
        """Get or create request ID.
        
        Returns:
            Request ID
        """
        if not hasattr(g, 'request_id'):
            g.request_id = str(uuid.uuid4())
        return g.request_id
    
    def _get_user_id(self) -> Optional[str]:
        """Get user ID from session or request.
        
        Returns:
            User ID if available
        """
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                return str(current_user.id)
        except:
            pass
        
        return request.headers.get('X-User-ID')
    
    def _get_session_id(self) -> Optional[str]:
        """Get session ID.
        
        Returns:
            Session ID if available
        """
        if hasattr(session, 'sid'):
            return session.sid
        return request.headers.get('X-Session-ID')
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers by removing sensitive information.
        
        Args:
            headers: Original headers
        
        Returns:
            Sanitized headers
        """
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        return sanitized
    
    def _get_client_info(self) -> Dict[str, Any]:
        """Get client information from request.
        
        Returns:
            Client information dictionary
        """
        return {
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            'user_agent': request.headers.get('User-Agent'),
            'referer': request.headers.get('Referer'),
            'accept_language': request.headers.get('Accept-Language')
        }
    
    def _get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'memory_usage_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent()
            }
        except Exception:
            return {}
    
    def _before_request(self):
        """Handle before request logging."""
        if not self._should_log_path(request.path):
            return
        
        request_id = self._get_request_id()
        start_time = time.time()
        
        # Store request start time
        g.request_start_time = start_time
        
        # Track active request
        self.active_requests[request_id] = {
            'start_time': start_time,
            'method': request.method,
            'path': request.path,
            'user_id': self._get_user_id()
        }
        
        if self.log_requests:
            client_info = self._get_client_info()
            
            # Log with comprehensive logger
            if self.comprehensive_logger:
                context = LogContext(
                    correlation_id=request_id,
                    user_id=self._get_user_id(),
                    session_id=self._get_session_id(),
                    component='flask_request',
                    operation='http_request_start'
                )
                
                self.comprehensive_logger.info(
                    f"Request started: {request.method} {request.path}",
                    context=context,
                    extra={
                        'request_method': request.method,
                        'request_path': request.path,
                        'request_args': dict(request.args),
                        'request_headers': self._sanitize_headers(dict(request.headers)),
                        **client_info
                    }
                )
            
            # Log with structured logger
            if self.structured_logger:
                self.structured_logger.log_request(
                    method=request.method,
                    url=request.path,
                    status_code=0,  # Not available yet
                    response_time=0,  # Not available yet
                    user_id=self._get_user_id(),
                    ip_address=client_info.get('ip_address'),
                    user_agent=client_info.get('user_agent'),
                    correlation_id=request_id,
                    request_id=request_id,
                    operation='request_start'
                )
    
    def _after_request(self, response):
        """Handle after request logging.
        
        Args:
            response: Flask response object
        
        Returns:
            Modified response object
        """
        if not self._should_log_path(request.path):
            return response
        
        request_id = self._get_request_id()
        
        # Calculate response time
        response_time = 0
        if hasattr(g, 'request_start_time'):
            response_time = time.time() - g.request_start_time
        
        # Clean up active request tracking
        self.active_requests.pop(request_id, None)
        
        if self.log_responses:
            client_info = self._get_client_info()
            performance_metrics = self._get_performance_metrics() if self.log_performance else {}
            
            # Log with comprehensive logger
            if self.comprehensive_logger:
                context = LogContext(
                    correlation_id=request_id,
                    user_id=self._get_user_id(),
                    session_id=self._get_session_id(),
                    component='flask_response',
                    operation='http_request_complete'
                )
                
                log_level = LogLevel.INFO
                if response.status_code >= 500:
                    log_level = LogLevel.ERROR
                elif response.status_code >= 400:
                    log_level = LogLevel.WARNING
                
                self.comprehensive_logger.log(
                    log_level,
                    f"Request completed: {request.method} {request.path} {response.status_code} ({response_time:.3f}s)",
                    context=context,
                    extra={
                        'request_method': request.method,
                        'request_path': request.path,
                        'response_status': response.status_code,
                        'response_time': response_time,
                        'response_size': len(response.get_data()),
                        **client_info,
                        **performance_metrics
                    }
                )
            
            # Log with structured logger
            if self.structured_logger:
                self.structured_logger.log_request(
                    method=request.method,
                    url=request.path,
                    status_code=response.status_code,
                    response_time=response_time,
                    user_id=self._get_user_id(),
                    ip_address=client_info.get('ip_address'),
                    user_agent=client_info.get('user_agent'),
                    correlation_id=request_id,
                    request_id=request_id,
                    operation='request_complete',
                    response_size=len(response.get_data()),
                    **performance_metrics
                )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response
    
    def _handle_exception(self, error: Exception):
        """Handle general exceptions.
        
        Args:
            error: Exception that occurred
        
        Returns:
            Error response
        """
        request_id = self._get_request_id()
        error_id = str(uuid.uuid4())
        
        # Log with comprehensive logger
        if self.comprehensive_logger:
            context = LogContext(
                correlation_id=request_id,
                user_id=self._get_user_id(),
                session_id=self._get_session_id(),
                component='flask_error',
                operation='exception_handler'
            )
            
            self.comprehensive_logger.error(
                f"Unhandled exception in {request.method} {request.path}: {str(error)}",
                context=context,
                extra={
                    'error_id': error_id,
                    'error_type': error.__class__.__name__,
                    'request_method': request.method,
                    'request_path': request.path,
                    'client_info': self._get_client_info()
                },
                exc_info=True
            )
        
        # Log with structured logger
        if self.structured_logger:
            self.structured_logger.log_exception(
                error,
                message=f"Unhandled exception in {request.method} {request.path}",
                error_id=error_id,
                correlation_id=request_id,
                request_id=request_id,
                user_id=self._get_user_id(),
                operation='exception_handler'
            )
        
        # Return error response
        return {
            'error': 'Internal server error',
            'error_id': error_id,
            'request_id': request_id
        }, 500
    
    def _handle_http_exception(self, error: HTTPException):
        """Handle HTTP exceptions.
        
        Args:
            error: HTTP exception that occurred
        
        Returns:
            Error response
        """
        request_id = self._get_request_id()
        
        # Only log 4xx and 5xx errors
        if error.code >= 400:
            # Log with comprehensive logger
            if self.comprehensive_logger:
                context = LogContext(
                    correlation_id=request_id,
                    user_id=self._get_user_id(),
                    session_id=self._get_session_id(),
                    component='flask_http_error',
                    operation='http_exception_handler'
                )
                
                log_level = LogLevel.ERROR if error.code >= 500 else LogLevel.WARNING
                
                self.comprehensive_logger.log(
                    log_level,
                    f"HTTP {error.code} in {request.method} {request.path}: {error.description}",
                    context=context,
                    extra={
                        'http_status': error.code,
                        'request_method': request.method,
                        'request_path': request.path,
                        'client_info': self._get_client_info()
                    }
                )
            
            # Log with structured logger
            if self.structured_logger:
                log_method = self.structured_logger.error if error.code >= 500 else self.structured_logger.warning
                log_method(
                    f"HTTP {error.code} in {request.method} {request.path}: {error.description}",
                    correlation_id=request_id,
                    request_id=request_id,
                    user_id=self._get_user_id(),
                    operation='http_exception_handler',
                    http_status=error.code,
                    error_type='HTTPException'
                )
        
        # Return original HTTP exception response
        return error
    
    def _handle_application_error(self, error: ApplicationError):
        """Handle application-specific errors.
        
        Args:
            error: Application error that occurred
        
        Returns:
            Error response
        """
        request_id = self._get_request_id()
        
        # Log with comprehensive logger
        if self.comprehensive_logger:
            context = LogContext(
                correlation_id=request_id,
                user_id=self._get_user_id(),
                session_id=self._get_session_id(),
                component='flask_app_error',
                operation='application_error_handler'
            )
            
            self.comprehensive_logger.error(
                f"Application error in {request.method} {request.path}: {str(error)}",
                context=context,
                extra={
                    'error_id': getattr(error, 'error_id', None),
                    'error_code': getattr(error, 'error_code', None),
                    'error_type': error.__class__.__name__,
                    'request_method': request.method,
                    'request_path': request.path,
                    'client_info': self._get_client_info()
                }
            )
        
        # Log with structured logger
        if self.structured_logger:
            self.structured_logger.log_exception(
                error,
                message=f"Application error in {request.method} {request.path}",
                error_id=getattr(error, 'error_id', None),
                correlation_id=request_id,
                request_id=request_id,
                user_id=self._get_user_id(),
                operation='application_error_handler'
            )
        
        # Return application error response
        return {
            'error': getattr(error, 'user_message', str(error)),
            'error_code': getattr(error, 'error_code', 'APPLICATION_ERROR'),
            'error_id': getattr(error, 'error_id', None),
            'request_id': request_id
        }, getattr(error, 'http_status_code', 500)
    
    def _teardown_request(self, exception=None):
        """Handle request teardown.
        
        Args:
            exception: Exception if any occurred
        """
        # Clean up any remaining request data
        request_id = getattr(g, 'request_id', None)
        if request_id and request_id in self.active_requests:
            del self.active_requests[request_id]
    
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active requests.
        
        Returns:
            Dictionary of active requests
        """
        return self.active_requests.copy()
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get request metrics.
        
        Returns:
            Request metrics dictionary
        """
        active_count = len(self.active_requests)
        
        if active_count == 0:
            return {
                'active_requests': 0,
                'avg_request_duration': 0,
                'longest_running_request': None
            }
        
        current_time = time.time()
        durations = []
        longest_request = None
        longest_duration = 0
        
        for request_id, request_info in self.active_requests.items():
            duration = current_time - request_info['start_time']
            durations.append(duration)
            
            if duration > longest_duration:
                longest_duration = duration
                longest_request = {
                    'request_id': request_id,
                    'duration': duration,
                    'method': request_info['method'],
                    'path': request_info['path'],
                    'user_id': request_info.get('user_id')
                }
        
        return {
            'active_requests': active_count,
            'avg_request_duration': sum(durations) / len(durations),
            'longest_running_request': longest_request
        }

def log_route(logger_name: Optional[str] = None, log_args: bool = True, log_result: bool = True):
    """Decorator for logging route functions.
    
    Args:
        logger_name: Custom logger name
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger
            name = logger_name or f"route.{func.__name__}"
            logger = None
            
            if get_structured_logger:
                logger = get_structured_logger(name)
            
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            start_time = time.time()
            
            # Log function start
            if logger:
                extra_data = {
                    'correlation_id': request_id,
                    'operation': f"route_{func.__name__}",
                    'component': 'flask_route'
                }
                
                if log_args:
                    extra_data.update({
                        'function_args': str(args),
                        'function_kwargs': {k: str(v) for k, v in kwargs.items()}
                    })
                
                logger.info(f"Route function started: {func.__name__}", **extra_data)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success
                duration = time.time() - start_time
                if logger:
                    extra_data = {
                        'correlation_id': request_id,
                        'operation': f"route_{func.__name__}",
                        'component': 'flask_route',
                        'duration': duration,
                        'success': True
                    }
                    
                    if log_result:
                        extra_data['result_type'] = type(result).__name__
                    
                    logger.info(f"Route function completed: {func.__name__} ({duration:.3f}s)", **extra_data)
                
                return result
                
            except Exception as e:
                # Log error
                duration = time.time() - start_time
                if logger:
                    logger.log_exception(
                        e,
                        message=f"Route function failed: {func.__name__}",
                        correlation_id=request_id,
                        operation=f"route_{func.__name__}",
                        component='flask_route',
                        duration=duration
                    )
                
                raise
        
        return wrapper
    return decorator

def log_performance(operation_name: Optional[str] = None):
    """Decorator for logging performance metrics.
    
    Args:
        operation_name: Custom operation name
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation = operation_name or func.__name__
            start_time = time.time()
            start_metrics = None
            
            # Get initial performance metrics
            try:
                process = psutil.Process(os.getpid())
                start_metrics = {
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'cpu_percent': process.cpu_percent()
                }
            except Exception:
                pass
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate performance metrics
                duration = time.time() - start_time
                end_metrics = None
                
                try:
                    process = psutil.Process(os.getpid())
                    end_metrics = {
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'cpu_percent': process.cpu_percent()
                    }
                except Exception:
                    pass
                
                # Log performance
                if get_structured_logger:
                    logger = get_structured_logger('performance')
                    
                    extra_data = {
                        'operation': operation,
                        'duration': duration,
                        'success': True
                    }
                    
                    if start_metrics and end_metrics:
                        extra_data.update({
                            'memory_usage_mb': end_metrics['memory_mb'],
                            'memory_delta_mb': end_metrics['memory_mb'] - start_metrics['memory_mb'],
                            'cpu_usage_percent': end_metrics['cpu_percent']
                        })
                    
                    logger.log_performance(
                        f"Operation completed: {operation}",
                        response_time=duration,
                        memory_usage=end_metrics['memory_mb'] if end_metrics else None,
                        cpu_usage=end_metrics['cpu_percent'] if end_metrics else None,
                        **extra_data
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log failed performance
                if get_structured_logger:
                    logger = get_structured_logger('performance')
                    logger.log_exception(
                        e,
                        message=f"Operation failed: {operation}",
                        operation=operation,
                        duration=duration
                    )
                
                raise
        
        return wrapper
    return decorator

def setup_flask_logging(
    app: Flask,
    logger_name: str = 'flask_app',
    log_level: str = 'INFO',
    log_requests: bool = True,
    log_responses: bool = True,
    log_performance: bool = True,
    exclude_paths: Optional[List[str]] = None
) -> FlaskLoggingIntegration:
    """Setup Flask logging integration.
    
    Args:
        app: Flask application
        logger_name: Logger name
        log_level: Logging level
        log_requests: Whether to log requests
        log_responses: Whether to log responses
        log_performance: Whether to log performance
        exclude_paths: Paths to exclude from logging
    
    Returns:
        FlaskLoggingIntegration instance
    """
    integration = FlaskLoggingIntegration(
        app=app,
        logger_name=logger_name,
        log_requests=log_requests,
        log_responses=log_responses,
        log_performance=log_performance,
        exclude_paths=exclude_paths
    )
    
    return integration