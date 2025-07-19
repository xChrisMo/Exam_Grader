"""Unified API Router with consolidated routing structure.

This module provides:
- Consolidated API routing structure
- Consistent authentication and authorization middleware
- Rate limiting and CORS handling
- Standardized error handling and validation
- Request/response logging and monitoring
"""

import time
import functools
from typing import Dict, Any, Optional, Callable
from flask import (
    Blueprint, request, jsonify, g, current_app,
    session, abort
)
from flask_login import current_user
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from src.models.api_responses import APIResponse, ErrorResponse
from src.models.validation import validate_request_data, ValidationError
from src.utils.response_utils import (
    standardize_response, generate_request_id, create_metadata,
    handle_service_errors, extract_pagination_params
)
from utils.logger import logger
from webapp.auth import login_required

# Create unified API blueprint
unified_api_bp = Blueprint('unified_api', __name__, url_prefix='/api/v1')

# Rate limiting storage (in-memory for now, should use Redis in production)
rate_limit_storage = {}


class APIMiddleware:
    """Middleware for API request processing."""
    
    @staticmethod
    def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
        """Rate limiting decorator.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Get client identifier (IP address or user ID)
                identifier = (
                    current_user.id if current_user.is_authenticated 
                    else request.remote_addr
                )
                
                current_time = time.time()
                cutoff_time = current_time - window_seconds
                
                # Clean old entries
                if identifier in rate_limit_storage:
                    rate_limit_storage[identifier] = [
                        timestamp for timestamp in rate_limit_storage[identifier]
                        if timestamp > cutoff_time
                    ]
                else:
                    rate_limit_storage[identifier] = []
                
                # Check rate limit
                if len(rate_limit_storage[identifier]) >= max_requests:
                    return jsonify(ErrorResponse.rate_limit(
                        message=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds",
                        retry_after=window_seconds
                    ).to_dict()), 429
                
                # Add current request
                rate_limit_storage[identifier].append(current_time)
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def validate_json(required_fields: Optional[list] = None):
        """JSON validation decorator.
        
        Args:
            required_fields: List of required field names
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not request.is_json:
                    return jsonify(ErrorResponse.validation_error(
                        message="Request must be JSON",
                        details=[{"field": "content-type", "message": "Expected application/json"}]
                    ).to_dict()), 400
                
                data = request.get_json()
                if not data:
                    return jsonify(ErrorResponse.validation_error(
                        message="Request body cannot be empty"
                    ).to_dict()), 400
                
                # Validate required fields
                if required_fields:
                    # Convert list of required fields to validator format
                    def create_required_validator(field_name):
                        return lambda value, fn: None if value is not None else f"Field '{field_name}' is required"
                    
                    validators = {field: [create_required_validator(field)] for field in required_fields}
                    validation_result = validate_request_data(data, validators)
                    if not validation_result.is_valid:
                        return jsonify(ErrorResponse.validation_error(
                            message="Validation failed",
                            details=[{
                                "field": error.field,
                                "message": error.message,
                                "code": error.code
                            } for error in validation_result.errors]
                        ).to_dict()), 400
                
                # Store validated data in g for use in route
                g.validated_data = data
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_auth(allow_api_key: bool = False):
        """Authentication decorator with optional API key support.
        
        Args:
            allow_api_key: Whether to allow API key authentication
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Check session-based authentication first
                if current_user.is_authenticated:
                    return func(*args, **kwargs)
                
                # Check API key authentication if allowed
                if allow_api_key:
                    api_key = request.headers.get('X-API-Key')
                    if api_key and _validate_api_key(api_key):
                        return func(*args, **kwargs)
                
                return jsonify(ErrorResponse.unauthorized(
                    message="Authentication required"
                ).to_dict()), 401
            return wrapper
        return decorator
    
    @staticmethod
    def log_request():
        """Request logging decorator."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Set request metadata
                g.request_start_time = time.time()
                g.request_id = generate_request_id()
                
                # Log request
                logger.info(
                    f"API Request: {request.method} {request.path} "
                    f"[{g.request_id}] from {request.remote_addr}"
                )
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful response
                    processing_time = time.time() - g.request_start_time
                    logger.info(
                        f"API Response: {request.method} {request.path} "
                        f"[{g.request_id}] completed in {processing_time:.3f}s"
                    )
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    processing_time = time.time() - g.request_start_time
                    logger.error(
                        f"API Error: {request.method} {request.path} "
                        f"[{g.request_id}] failed in {processing_time:.3f}s: {str(e)}"
                    )
                    raise
            return wrapper
        return decorator


def _validate_api_key(api_key: str) -> bool:
    """Validate API key (placeholder implementation).
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    # TODO: Implement proper API key validation
    # This should check against a database or secure storage
    return False


# Error handlers for the unified API
@unified_api_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors."""
    return jsonify(ErrorResponse.validation_error(
        message="Bad request",
        details=[{"message": str(error)}]
    ).to_dict()), 400


@unified_api_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors."""
    return jsonify(ErrorResponse.unauthorized(
        message="Unauthorized access"
    ).to_dict()), 401


@unified_api_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors."""
    return jsonify(ErrorResponse.forbidden(
        message="Access forbidden"
    ).to_dict()), 403


@unified_api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return jsonify(ErrorResponse.not_found(
        message="Resource not found"
    ).to_dict()), 404


@unified_api_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 Rate Limit Exceeded errors."""
    return jsonify(ErrorResponse.rate_limit(
        message="Rate limit exceeded"
    ).to_dict()), 429


@unified_api_bp.errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server Error."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify(ErrorResponse.processing_error(
        message="Internal server error"
    ).to_dict()), 500


@unified_api_bp.errorhandler(HTTPException)
def handle_http_exception(error):
    """Handle all HTTP exceptions."""
    return jsonify(ErrorResponse.processing_error(
        message=error.description or "HTTP error occurred",
        error_code=f"HTTP_{error.code}"
    ).to_dict()), error.code


@unified_api_bp.errorhandler(Exception)
def handle_generic_exception(error):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception in API: {str(error)}", exc_info=True)
    return jsonify(ErrorResponse.processing_error(
        message="An unexpected error occurred"
    ).to_dict()), 500


# Health check endpoint
@unified_api_bp.route('/health', methods=['GET'])
@APIMiddleware.log_request()
@standardize_response
def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


# API info endpoint
@unified_api_bp.route('/info', methods=['GET'])
@APIMiddleware.log_request()
@APIMiddleware.rate_limit(max_requests=50, window_seconds=3600)
@standardize_response
def api_info():
    """API information endpoint."""
    return {
        "name": "Exam Grader API",
        "version": "1.0.0",
        "description": "AI-powered exam grading and assessment platform",
        "endpoints": {
            "health": "/api/v1/health",
            "info": "/api/v1/info",
            "guides": "/api/v1/guides",
            "submissions": "/api/v1/submissions",
            "processing": "/api/v1/processing",
            "upload": "/api/v1/upload"
        }
    }


def init_unified_api(app):
    """Initialize unified API with Flask app.
    
    Args:
        app: Flask application instance
    """
    # Import consolidated endpoints to register routes
    try:
        import src.api.consolidated_endpoints
        logger.info("Consolidated endpoints imported successfully")
    except Exception as e:
        logger.error(f"Failed to import consolidated endpoints: {str(e)}")
    
    # Enable CORS for API endpoints
    CORS(unified_api_bp, 
         origins=['http://localhost:3000', 'http://localhost:5000', 'http://localhost:8501', 'http://127.0.0.1:8501'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-API-Key', 'X-CSRFToken'],
         supports_credentials=True)
    
    # Register the unified API blueprint
    app.register_blueprint(unified_api_bp)
    
    logger.info("Unified API router initialized with CORS and middleware")
    
    return unified_api_bp


# Utility decorators for common API patterns
def api_endpoint(methods=['GET'], auth_required=True, rate_limit_config=None, 
                validate_json_fields=None):
    """Composite decorator for API endpoints.
    
    Args:
        methods: HTTP methods allowed
        auth_required: Whether authentication is required
        rate_limit_config: Rate limiting configuration dict
        validate_json_fields: List of required JSON fields
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in reverse order (bottom to top execution)
        decorated_func = func
        
        # Response standardization (always applied)
        decorated_func = standardize_response(decorated_func)
        
        # JSON validation (if specified)
        if validate_json_fields and 'POST' in methods or 'PUT' in methods:
            decorated_func = APIMiddleware.validate_json(validate_json_fields)(decorated_func)
        
        # Authentication (if required)
        if auth_required:
            decorated_func = APIMiddleware.require_auth()(decorated_func)
        
        # Rate limiting (if configured)
        if rate_limit_config:
            decorated_func = APIMiddleware.rate_limit(**rate_limit_config)(decorated_func)
        
        # Request logging (always applied)
        decorated_func = APIMiddleware.log_request()(decorated_func)
        
        return decorated_func
    return decorator