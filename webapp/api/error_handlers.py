"""
Unified API Error Handling

This module provides standardized error handling for all API endpoints
with consistent response formats, error categorization, and monitoring.
"""

import time
from datetime import datetime, timezone
import traceback
from typing import Any, Dict, Optional, Tuple

from flask import current_app, jsonify, request

from src.services.enhanced_logging_service import LogCategory, enhanced_logging_service
from src.services.monitoring.monitoring_service import performance_monitor
from src.services.processing_error_handler import ErrorContext, processing_error_handler
from utils.logger import logger

class APIErrorHandler:
    """Unified API error handler with standardized responses"""

    def __init__(self):
        self.error_categories = {
            400: "client_error",
            401: "authentication_error",
            403: "authorization_error",
            404: "not_found_error",
            413: "payload_too_large",
            422: "validation_error",
            429: "rate_limit_error",
            500: "server_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout",
        }

    def create_error_response(
        self,
        error: Exception,
        status_code: int = 500,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create standardized error response

        Args:
            error: The exception that occurred
            status_code: HTTP status code
            message: Custom error message
            details: Additional error details
            request_id: Request tracking ID

        Returns:
            Tuple of (response_dict, status_code)
        """

        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"

        # Determine error category
        error_category = self.error_categories.get(status_code, "unknown_error")

        error_context = ErrorContext(
            operation="api_request",
            service="unified_api",
            timestamp=datetime.now(timezone.utc),
            request_id=request_id,
            additional_data={
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
                "user_agent": request.headers.get("User-Agent"),
                "status_code": status_code,
                "error_type": type(error).__name__,
            },
        )

        # Handle error with processing error handler
        error_response = processing_error_handler.handle_error(error, error_context)

        # Create standardized API response
        api_response = {
            "success": False,
            "error": {
                "code": status_code,
                "category": error_category,
                "type": type(error).__name__,
                "message": message or str(error),
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            },
            "data": None,
            "metadata": {
                "processing_time_ms": 0,  # Will be updated by middleware
                "api_version": "1.0",
                "endpoint": request.endpoint,
                "method": request.method,
            },
        }

        # Add debug information in development
        if current_app.debug:
            api_response["debug"] = {
                "traceback": traceback.format_exc(),
                "error_handler_response": error_response,
            }

        # Log error with enhanced logging
        enhanced_logging_service.log_error(
            f"API Error: {error_category}",
            LogCategory.API_ERROR,
            {
                "request_id": request_id,
                "status_code": status_code,
                "error_type": type(error).__name__,
                "message": str(error),
                "endpoint": request.endpoint,
                "method": request.method,
                "user_id": getattr(request, "user_id", None),
            },
        )

        # Track error metrics
        performance_monitor.track_metric(
            operation=f"api_error_{status_code}",
            metric_type=performance_monitor.MetricType.ERROR_RATE,
            value=1.0,
            metadata={"error_category": error_category},
        )

        return api_response, status_code

    def create_success_response(
        self,
        data: Any = None,
        message: str = "Success",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create standardized success response

        Args:
            data: Response data
            message: Success message
            metadata: Additional metadata
            request_id: Request tracking ID

        Returns:
            Standardized success response dictionary
        """

        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"

        response = {
            "success": True,
            "message": message,
            "data": data,
            "metadata": {
                "processing_time_ms": 0,  # Will be updated by middleware
                "api_version": "1.0",
                "endpoint": request.endpoint,
                "method": request.method,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            },
        }

        return response

    def handle_validation_error(
        self, errors: Dict[str, Any], request_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Handle validation errors with detailed field information"""

        return self.create_error_response(
            error=ValueError("Validation failed"),
            status_code=422,
            message="Request validation failed",
            details={"validation_errors": errors, "error_count": len(errors)},
            request_id=request_id,
        )

    def handle_authentication_error(
        self, message: str = "Authentication required", request_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Handle authentication errors"""

        return self.create_error_response(
            error=PermissionError(message),
            status_code=401,
            message=message,
            details={"auth_required": True},
            request_id=request_id,
        )

    def handle_authorization_error(
        self,
        message: str = "Insufficient permissions",
        request_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """Handle authorization errors"""

        return self.create_error_response(
            error=PermissionError(message),
            status_code=403,
            message=message,
            details={"permission_required": True},
            request_id=request_id,
        )

    def handle_not_found_error(
        self, resource: str = "Resource", request_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Handle not found errors"""

        return self.create_error_response(
            error=FileNotFoundError(f"{resource} not found"),
            status_code=404,
            message=f"{resource} not found",
            details={"resource": resource},
            request_id=request_id,
        )

    def handle_rate_limit_error(
        self, retry_after: int = 60, request_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Handle rate limiting errors"""

        return self.create_error_response(
            error=Exception("Rate limit exceeded"),
            status_code=429,
            message="Rate limit exceeded",
            details={"retry_after_seconds": retry_after, "rate_limit_exceeded": True},
            request_id=request_id,
        )

    def handle_service_unavailable_error(
        self, service: str = "Service", request_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Handle service unavailable errors"""

        return self.create_error_response(
            error=ConnectionError(f"{service} unavailable"),
            status_code=503,
            message=f"{service} is temporarily unavailable",
            details={"service": service, "temporary": True, "retry_recommended": True},
            request_id=request_id,
        )

# Global error handler instance
api_error_handler = APIErrorHandler()

def register_error_handlers(app):
    """Register unified error handlers with Flask app"""

    @app.errorhandler(400)
    def handle_bad_request(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=400, message="Bad request"
            )
            return jsonify(response), status
        from webapp.error_handlers import handle_400

        return handle_400(error)

    @app.errorhandler(401)
    def handle_unauthorized(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.handle_authentication_error()
            return jsonify(response), status
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.handle_authorization_error()
            return jsonify(response), status
        from webapp.error_handlers import handle_403

        return handle_403(error)

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.handle_not_found_error()
            return jsonify(response), status
        from webapp.error_handlers import handle_404

        return handle_404(error)

    @app.errorhandler(413)
    def handle_payload_too_large(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=413, message="Request payload too large"
            )
            return jsonify(response), status
        from webapp.error_handlers import handle_413

        return handle_413(error)

    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=422, message="Unprocessable entity"
            )
            return jsonify(response), status
        return jsonify({"error": "Unprocessable entity"}), 422

    @app.errorhandler(429)
    def handle_too_many_requests(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.handle_rate_limit_error()
            return jsonify(response), status
        return jsonify({"error": "Too many requests"}), 429

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=500, message="Internal server error"
            )
            return jsonify(response), status
        from webapp.error_handlers import handle_500

        return handle_500(error)

    @app.errorhandler(502)
    def handle_bad_gateway(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=502, message="Bad gateway"
            )
            return jsonify(response), status
        return jsonify({"error": "Bad gateway"}), 502

    @app.errorhandler(503)
    def handle_service_unavailable(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.handle_service_unavailable_error()
            return jsonify(response), status
        return jsonify({"error": "Service unavailable"}), 503

    @app.errorhandler(504)
    def handle_gateway_timeout(error):
        if request.path.startswith("/api/"):
            response, status = api_error_handler.create_error_response(
                error=error, status_code=504, message="Gateway timeout"
            )
            return jsonify(response), status
        return jsonify({"error": "Gateway timeout"}), 504

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        if request.path.startswith("/api/"):
            # Handle unexpected exceptions in API routes
            response, status = api_error_handler.create_error_response(
                error=error, status_code=500, message="An unexpected error occurred"
            )
            return jsonify(response), status

        # For non-API routes, log and re-raise
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        raise error
