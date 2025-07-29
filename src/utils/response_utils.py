"""Utilities for standardized API response handling."""
from typing import Any, Dict, List, Tuple, Callable

from functools import wraps
from flask import jsonify, request, g
import time
import uuid
from datetime import datetime

from ..models.api_responses import (
    APIResponse, PaginatedResponse, ErrorResponse, APIMetadata,
    ResponseStatus, ErrorCode, ErrorDetail
)
from ..models.validation import ValidationResult, ValidationError

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())

def get_processing_time() -> float:
    """Get processing time from request start."""
    start_time = getattr(g, 'request_start_time', None)
    if start_time:
        return (time.time() - start_time) * 1000  # Convert to milliseconds
    return None

def create_metadata(request_id: str = None, warnings: List[str] = None) -> APIMetadata:
    """Create API metadata with request tracking."""
    return APIMetadata(
        request_id=request_id or generate_request_id(),
        processing_time_ms=get_processing_time(),
        warnings=warnings or []
    )

def standardize_response(func: Callable) -> Callable:
    """Decorator to standardize API responses."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Set request start time
        g.request_start_time = time.time()
        g.request_id = generate_request_id()
        
        try:
            result = func(*args, **kwargs)
            
            # If result is already a Flask response, return as-is
            if hasattr(result, 'status_code'):
                return result
            
            # If result is a tuple (data, status_code)
            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
                if isinstance(data, dict) and 'status' in data:
                    # Already standardized
                    return jsonify(data), status_code
                else:
                    # Wrap in standard response
                    response = APIResponse.success(
                        data=data,
                        metadata=create_metadata(g.request_id)
                    )
                    return jsonify(response.to_dict()), status_code
            
            # If result is a dictionary with status field, assume it's standardized
            if isinstance(result, dict) and 'status' in result:
                return jsonify(result)
            
            # Wrap plain data in standard response
            response = APIResponse.success(
                data=result,
                metadata=create_metadata(g.request_id)
            )
            return jsonify(response.to_dict())
            
        except ValidationError as e:
            error_response = ErrorResponse.validation_error(
                message=str(e),
                details={"validation_errors": [e.to_dict()] if hasattr(e, 'to_dict') else None}
            )
            error_response.metadata = create_metadata(g.request_id)
            return jsonify(error_response.to_dict()), 400
            
        except Exception as e:
            error_response = ErrorResponse(
                message="Internal server error",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"error": str(e)}
            )
            error_response.metadata = create_metadata(g.request_id)
            return jsonify(error_response.to_dict()), 500
    
    return wrapper

def success_response(data: Any = None, message: str = None, status_code: int = 200) -> Tuple[Dict[str, Any], int]:
    """Create a standardized success response."""
    response = APIResponse.success(
        data=data,
        message=message,
        metadata=create_metadata(getattr(g, 'request_id', None))
    )
    return response.to_dict(), status_code

def error_response(
    message: str, 
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    field: str = None,
    details: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Create a standardized error response."""
    response = ErrorResponse(
        message=message,
        error_code=error_code,
        field=field,
        details=details
    )
    response.metadata = create_metadata(getattr(g, 'request_id', None))
    return response.to_dict(), status_code

def validation_error_response(
    validation_result: ValidationResult,
    status_code: int = 400
) -> Tuple[Dict[str, Any], int]:
    """Create a response from validation result."""
    if validation_result.is_valid:
        return success_response(message="Validation passed")
    
    # Convert validation errors to error details
    error_details = []
    for error in validation_result.errors:
        error_detail = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message=error.message,
            field=error.field,
            details={"code": error.code, "value": error.value, "constraint": error.constraint}
        )
        error_details.append(error_detail)
    
    response = APIResponse(
        status=ResponseStatus.ERROR,
        message="Validation failed",
        errors=error_details,
        metadata=create_metadata(
            getattr(g, 'request_id', None),
            validation_result.get_warning_messages()
        )
    )
    
    return response.to_dict(), status_code

def paginated_response(
    items: List[Any],
    page: int = 1,
    per_page: int = 20,
    total_items: int = None,
    message: str = None,
    status_code: int = 200
) -> Tuple[Dict[str, Any], int]:
    """Create a standardized paginated response."""
    if total_items is None:
        total_items = len(items)
    
    response = PaginatedResponse.success_paginated(
        items=items,
        page=page,
        per_page=per_page,
        total_items=total_items,
        message=message,
        metadata=create_metadata(getattr(g, 'request_id', None))
    )
    
    return response.to_dict(), status_code

def loading_response(
    operation_id: str,
    message: str = "Processing...",
    progress: Dict[str, Any] = None,
    status_code: int = 202
) -> Tuple[Dict[str, Any], int]:
    """Create a standardized loading response."""
    response = APIResponse.loading(
        operation_id=operation_id,
        message=message,
        progress=progress,
        metadata=create_metadata(getattr(g, 'request_id', None))
    )
    
    return response.to_dict(), status_code

def not_found_response(resource: str = "Resource") -> Tuple[Dict[str, Any], int]:
    """Create a standardized not found response."""
    return error_response(
        message=f"{resource} not found",
        error_code=ErrorCode.NOT_FOUND,
        status_code=404
    )

def unauthorized_response(message: str = "Authentication required") -> Tuple[Dict[str, Any], int]:
    """Create a standardized unauthorized response."""
    return error_response(
        message=message,
        error_code=ErrorCode.AUTHENTICATION_ERROR,
        status_code=401
    )

def forbidden_response(message: str = "Access denied") -> Tuple[Dict[str, Any], int]:
    """Create a standardized forbidden response."""
    return error_response(
        message=message,
        error_code=ErrorCode.AUTHORIZATION_ERROR,
        status_code=403
    )

def service_unavailable_response(service: str = "Service") -> Tuple[Dict[str, Any], int]:
    """Create a standardized service unavailable response."""
    return error_response(
        message=f"{service} is currently unavailable",
        error_code=ErrorCode.SERVICE_UNAVAILABLE,
        status_code=503
    )

def rate_limit_response(message: str = "Rate limit exceeded") -> Tuple[Dict[str, Any], int]:
    """Create a standardized rate limit response."""
    return error_response(
        message=message,
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        status_code=429
    )

def processing_error_response(
    message: str = "Processing failed",
    details: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Create a standardized processing error response."""
    return error_response(
        message=message,
        error_code=ErrorCode.PROCESSING_ERROR,
        status_code=422,
        details=details
    )

def handle_service_errors(func: Callable) -> Callable:
    """Decorator to handle common service errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError:
            return service_unavailable_response()
        except TimeoutError:
            return error_response(
                message="Request timeout",
                error_code=ErrorCode.TIMEOUT_ERROR,
                status_code=408
            )
        except ValueError as e:
            return error_response(
                message=f"Invalid input: {str(e)}",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400
            )
        except Exception as e:
            return error_response(
                message="Internal server error",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"error": str(e)}
            )
    
    return wrapper

def extract_pagination_params(default_per_page: int = 20, max_per_page: int = 100) -> Tuple[int, int]:
    """Extract and validate pagination parameters from request."""
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(max_per_page, max(1, int(request.args.get('per_page', default_per_page))))
        return page, per_page
    except (ValueError, TypeError):
        return 1, default_per_page

def format_datetime(dt: datetime) -> str:
    """Format datetime for API responses."""
    if dt:
        return dt.isoformat()
    return None

def sanitize_response_data(data: Any) -> Any:
    """Sanitize data for JSON serialization."""
    if isinstance(data, datetime):
        return format_datetime(data)
    elif isinstance(data, dict):
        return {k: sanitize_response_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    elif hasattr(data, '__dict__'):
        # Handle objects with attributes
        return sanitize_response_data(data.__dict__)
    else:
        return data

def create_error_response(message: str, error_code: str = None, status_code: int = 500, details: Dict[str, Any] = None) -> Tuple[Dict[str, Any], int]:
    """Create a standardized error response.
    
    Args:
        message: Error message
        error_code: Optional error code
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    error_detail = ErrorDetail(
        code=error_code or 'INTERNAL_ERROR',
        message=message,
        details=details or {}
    )
    
    error_response = ErrorResponse(
        status=ResponseStatus.ERROR,
        error=error_detail,
        metadata=create_metadata()
    )
    
    return error_response.to_dict(), status_code