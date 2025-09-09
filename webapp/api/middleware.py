"""
API Middleware

This module provides middleware for request tracking, performance monitoring,
and response enhancement for unified API endpoints.
"""

import time
from datetime import datetime, timezone
import uuid
from functools import wraps

from flask import current_app, g, request

from src.services.enhanced_logging_service import LogCategory, enhanced_logging_service
from src.services.monitoring.monitoring_service import performance_monitor
from utils.logger import logger

class APIMiddleware:
    """Middleware for API request processing"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)

    def before_request(self):
        """Process request before handling"""
        # Only process API requests
        if not request.path.startswith("/api/"):
            return

        # Generate request ID
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()

        # Log request start
        enhanced_logging_service.log_info(
            "API Request Started",
            LogCategory.API_REQUEST,
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "endpoint": request.endpoint,
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type"),
                "content_length": request.headers.get("Content-Length"),
                "remote_addr": request.remote_addr,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Track request metrics
        performance_monitor.track_metric(
            operation=f"api_request_{request.method.lower()}",
            metric_type=performance_monitor.MetricType.THROUGHPUT,
            value=1.0,
            metadata={"endpoint": request.endpoint, "path": request.path},
        )

    def after_request(self, response):
        """Process response after handling"""
        # Only process API requests
        if not request.path.startswith("/api/"):
            return response

        # Calculate processing time
        processing_time = 0
        if hasattr(g, "start_time"):
            processing_time = (
                time.time() - g.start_time
            ) * 1000  # Convert to milliseconds

        # Add request tracking headers
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id

        response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
        response.headers["X-API-Version"] = "1.0"
        response.headers["X-Timestamp"] = datetime.now(timezone.utc).isoformat()

        if response.is_json and response.get_json():
            try:
                data = response.get_json()
                if isinstance(data, dict) and "metadata" in data:
                    data["metadata"]["processing_time_ms"] = round(processing_time, 2)
                    response.set_data(response.get_json().__class__(data))
            except Exception as e:
                logger.debug(f"Could not update response metadata: {e}")

        # Log response
        enhanced_logging_service.log_info(
            "API Request Completed",
            LogCategory.API_RESPONSE,
            {
                "request_id": getattr(g, "request_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "endpoint": request.endpoint,
                "status_code": response.status_code,
                "processing_time_ms": processing_time,
                "response_size": len(response.get_data()),
                "content_type": response.headers.get("Content-Type"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Track response metrics
        performance_monitor.track_operation(
            operation=f"api_response_{request.endpoint or 'unknown'}",
            duration=processing_time / 1000,  # Convert back to seconds
            success=response.status_code < 400,
            metadata={
                "status_code": response.status_code,
                "method": request.method,
                "path": request.path,
            },
        )

        return response

    def teardown_request(self, exception):
        """Clean up after request"""
        if exception:
            # Log any unhandled exceptions
            enhanced_logging_service.log_error(
                "Unhandled API Exception",
                LogCategory.API_ERROR,
                {
                    "request_id": getattr(g, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "endpoint": request.endpoint,
                    "exception": str(exception),
                    "exception_type": type(exception).__name__,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

def require_api_key(f):
    """Decorator to require API key for certain endpoints"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            from .error_handlers import api_error_handler

            response, status = api_error_handler.handle_authentication_error(
                message="API key required", request_id=getattr(g, "request_id", None)
            )
            return response, status

        # Validate API key (implement your validation logic)
        if not validate_api_key(api_key):

            response, status = api_error_handler.handle_authentication_error(
                message="Invalid API key", request_id=getattr(g, "request_id", None)
            )
            return response, status

        return f(*args, **kwargs)

    return decorated_function

def validate_api_key(api_key: str) -> bool:
    """Validate API key (implement your validation logic)"""
    # This is a placeholder - implement your actual API key validation
    # You might check against a database, environment variable, etc.
    valid_keys = current_app.config.get("API_KEYS", [])
    return api_key in valid_keys

def rate_limit(requests_per_minute: int = 60):
    """Decorator to implement rate limiting"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP address or user ID)
            client_id = request.remote_addr
            if hasattr(request, "user") and request.user:
                client_id = f"user_{request.user.id}"

            # Check rate limit (implement your rate limiting logic)
            if not check_rate_limit(client_id, requests_per_minute):

                response, status = api_error_handler.handle_rate_limit_error(
                    retry_after=60, request_id=getattr(g, "request_id", None)
                )
                return response, status

            return f(*args, **kwargs)

        return decorated_function

    return decorator

def check_rate_limit(client_id: str, requests_per_minute: int) -> bool:
    """Check if client is within rate limits"""
    # This is a placeholder - implement your actual rate limiting logic
    # You might use Redis, in-memory cache, or database to track requests
    return True  # For now, always allow requests

def validate_json_request(required_fields: list = None):
    """Decorator to validate JSON request data"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:

                response, status = api_error_handler.create_error_response(
                    error=ValueError("Content-Type must be application/json"),
                    status_code=400,
                    message="Request must contain JSON data",
                    request_id=getattr(g, "request_id", None),
                )
                return response, status

            data = request.get_json()
            if not data:

                response, status = api_error_handler.create_error_response(
                    error=ValueError("Empty JSON data"),
                    status_code=400,
                    message="Request body cannot be empty",
                    request_id=getattr(g, "request_id", None),
                )
                return response, status

            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None:
                        missing_fields.append(field)

                if missing_fields:

                    response, status = api_error_handler.handle_validation_error(
                        {
                            field: f"Field '{field}' is required"
                            for field in missing_fields
                        },
                        request_id=getattr(g, "request_id", None),
                    )
                    return response, status

            return f(*args, **kwargs)

        return decorated_function

    return decorator

def log_api_usage(operation: str):
    """Decorator to log API usage for analytics"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Log API usage
            enhanced_logging_service.log_info(
                f"API Usage: {operation}",
                LogCategory.API_USAGE,
                {
                    "operation": operation,
                    "request_id": getattr(g, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "endpoint": request.endpoint,
                    "user_id": getattr(request, "user_id", None),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return f(*args, **kwargs)

        return decorated_function

    return decorator

# Global middleware instance
api_middleware = APIMiddleware()
