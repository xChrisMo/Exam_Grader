"""Enhanced error handler that integrates all error handling components."""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Union

from flask import flash, request, session

from ..models.api_responses import ErrorCode
from ..utils.response_utils import create_error_response
from .application_errors import ApplicationError, ErrorSeverity
from .error_mapper import (
    ContextAwareErrorMapper,
    LocalizedErrorMapper,
    UserFriendlyErrorMapper,
    UserMessage,
)
from .error_tracker import ErrorAnalytics, ErrorTracker

logger = logging.getLogger(__name__)

class EnhancedErrorHandler:
    """Enhanced error handler with standardized error management."""

    def __init__(self, max_tracked_errors: int = 1000):
        """Initialize enhanced error handler.

        Args:
            max_tracked_errors: Maximum number of errors to track
        """
        self.tracker = ErrorTracker(max_errors=max_tracked_errors)
        self.analytics = ErrorAnalytics(self.tracker)

        # Error mappers
        self.user_friendly_mapper = UserFriendlyErrorMapper()
        self.localized_mapper = LocalizedErrorMapper()
        self.context_aware_mapper = ContextAwareErrorMapper()

        # Configuration
        self.auto_flash_errors = True
        self.track_all_errors = True
        self.generate_error_reports = True

    def handle_error(
        self,
        error: Union[Exception, ApplicationError],
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        flash_message: bool = None,
        return_response: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Handle error with comprehensive processing.

        Args:
            error: Exception or ApplicationError to handle
            context: Additional context information
            user_id: User ID if available
            request_id: Request ID if available
            flash_message: Whether to flash message to user (uses default if None)
            return_response: Whether to return API response format

        Returns:
            API response dictionary if return_response is True
        """
        if not isinstance(error, ApplicationError):
            app_error = self._convert_to_application_error(error)
        else:
            app_error = error

        # Enhance context with request information
        enhanced_context = self._enhance_context(context, user_id, request_id)

        # Track the error
        if self.track_all_errors:
            self.tracker.track_error(
                app_error,
                user_id=user_id,
                request_id=request_id,
                additional_context=enhanced_context,
            )

        # Log the error
        self._log_error(app_error, enhanced_context)

        # Generate user message
        user_message = self._generate_user_message(app_error, enhanced_context)

        should_flash = (
            flash_message if flash_message is not None else self.auto_flash_errors
        )
        if should_flash:
            self._flash_user_message(user_message)

        # Add to recent activity
        self._add_to_recent_activity(app_error, enhanced_context)

        if return_response:
            return self._create_api_response(app_error, user_message)

        return None

    def handle_validation_errors(
        self,
        validation_errors: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle multiple validation errors.

        Args:
            validation_errors: List of validation error dictionaries
            context: Additional context information

        Returns:
            API response dictionary
        """
        from .application_errors import ValidationError

        error = ValidationError(
            "Multiple validation errors occurred", validation_errors=validation_errors
        )

        return self.handle_error(error, context=context, return_response=True)

    def resolve_error(
        self,
        error_id: str,
        resolution_notes: str = "",
        resolved_by: Optional[str] = None,
    ) -> bool:
        """Resolve a tracked error.

        Args:
            error_id: Error ID to resolve
            resolution_notes: Notes about the resolution
            resolved_by: User who resolved the error

        Returns:
            True if error was resolved, False if not found
        """
        enhanced_notes = resolution_notes
        if resolved_by:
            enhanced_notes = f"Resolved by {resolved_by}: {resolution_notes}"

        return self.tracker.resolve_error(error_id, enhanced_notes)

    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics.

        Returns:
            Dictionary containing error metrics and analytics
        """
        return self.analytics.export_metrics()

    def get_error_report(self) -> Dict[str, Any]:
        """Generate comprehensive error report.

        Returns:
            Dictionary containing error report
        """
        if not self.generate_error_reports:
            return {"error": "Error reporting is disabled"}

        return self.analytics.generate_report()

    def get_recent_errors(
        self,
        limit: int = 10,
        severity_filter: Optional[ErrorSeverity] = None,
        error_code_filter: Optional[ErrorCode] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent errors with optional filtering.

        Args:
            limit: Maximum number of errors to return
            severity_filter: Filter by error severity
            error_code_filter: Filter by error code

        Returns:
            List of recent error dictionaries
        """
        recent_errors = self.tracker.get_recent_errors(
            limit=limit * 2
        )  # Get more for filtering

        # Apply filters
        filtered_errors = []
        for error_info in recent_errors:
            error = error_info["error"]

            # Apply severity filter
            if severity_filter and error.severity != severity_filter:
                continue

            # Apply error code filter
            if error_code_filter and error.error_code != error_code_filter:
                continue

            filtered_errors.append(
                {
                    "error_id": error.error_id,
                    "error_code": error.error_code.value,
                    "message": error.message,
                    "severity": error.severity.value,
                    "timestamp": error_info["timestamp"],
                    "user_id": error_info.get("user_id"),
                    "context": error_info.get("context", {}),
                    "resolved": error_info.get("resolved", False),
                }
            )

            if len(filtered_errors) >= limit:
                break

        return filtered_errors

    def cleanup_old_errors(self, days: int = 30) -> int:
        """Clean up old errors.

        Args:
            days: Number of days to keep errors

        Returns:
            Number of errors cleaned up
        """
        return self.tracker.clear_old_errors(days=days)

    def increment_request_count(self, count: int = 1):
        """Increment total request count for error rate calculation.

        Args:
            count: Number of requests to add
        """
        self.tracker.increment_requests(count)

    def _convert_to_application_error(self, error: Exception) -> ApplicationError:
        """Convert standard exception to ApplicationError.

        Args:
            error: Exception to convert

        Returns:
            ApplicationError instance
        """
        error_type = type(error).__name__

        # Map common exceptions to appropriate error codes
        error_code_mapping = {
            "ValueError": ErrorCode.VALIDATION_ERROR,
            "TypeError": ErrorCode.VALIDATION_ERROR,
            "KeyError": ErrorCode.VALIDATION_ERROR,
            "FileNotFoundError": ErrorCode.NOT_FOUND,
            "PermissionError": ErrorCode.AUTHORIZATION_ERROR,
            "ConnectionError": ErrorCode.SERVICE_UNAVAILABLE,
            "TimeoutError": ErrorCode.TIMEOUT_ERROR,
            "AttributeError": ErrorCode.INTERNAL_ERROR,
        }

        error_code = error_code_mapping.get(error_type, ErrorCode.INTERNAL_ERROR)

        return ApplicationError(
            message=str(error), error_code=error_code, original_error=error
        )

    def _enhance_context(
        self,
        context: Optional[Dict[str, Any]],
        user_id: Optional[str],
        request_id: Optional[str],
    ) -> Dict[str, Any]:
        """Enhance context with request and session information.

        Args:
            context: Original context
            user_id: User ID
            request_id: Request ID

        Returns:
            Enhanced context dictionary
        """
        enhanced_context = context.copy() if context else {}

        try:
            if request:
                enhanced_context.update(
                    {
                        "method": request.method,
                        "endpoint": request.endpoint,
                        "url": request.url,
                        "remote_addr": request.remote_addr,
                        "user_agent": request.headers.get("User-Agent", ""),
                    }
                )
        except RuntimeError:
            # Outside request context
            pass

        try:
            if session:
                enhanced_context.update(
                    {
                        "session_id": session.get("session_id"),
                        "language": session.get("language", "en"),
                    }
                )
        except RuntimeError:
            # Outside request context
            pass

        # Add user and request IDs
        if user_id:
            enhanced_context["user_id"] = user_id
        if request_id:
            enhanced_context["request_id"] = request_id

        return enhanced_context

    def _log_error(self, error: ApplicationError, context: Dict[str, Any]):
        """Log error with appropriate level based on severity.

        Args:
            error: ApplicationError to log
            context: Error context
        """
        log_message = f"[{error.error_code.value}] {error.message}"

        # Add context information
        if context:
            context_str = ", ".join(
                [f"{k}={v}" for k, v in context.items() if k not in ["traceback"]]
            )
            log_message += f" | Context: {context_str}"

        # Log with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=error.original_error)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=error.original_error)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _generate_user_message(
        self, error: ApplicationError, context: Dict[str, Any]
    ) -> UserMessage:
        """Generate user-friendly message for error.

        Args:
            error: ApplicationError to generate message for
            context: Error context

        Returns:
            UserMessage instance
        """
        # Choose appropriate mapper based on context
        language = context.get("language", "en")

        if language != "en":
            mapper = self.localized_mapper
        elif context.get("operation") or context.get("field"):
            mapper = self.context_aware_mapper
        else:
            mapper = self.user_friendly_mapper

        return mapper.map_error(error, context=context)

    def _flash_user_message(self, user_message: UserMessage):
        """Flash user message to session.

        Args:
            user_message: UserMessage to flash
        """
        try:
            # Map message severity to Flask flash category
            category_mapping = {
                "info": "info",
                "warning": "warning",
                "error": "error",
                "critical": "error",
            }

            category = category_mapping.get(user_message.severity.value, "error")
            flash(user_message.message, category)
        except RuntimeError:
            # Outside request context
            pass

    def _add_to_recent_activity(self, error: ApplicationError, context: Dict[str, Any]):
        """Add error to recent activity log.

        Args:
            error: ApplicationError to add
            context: Error context
        """
        try:
            activity = session.get("recent_activity", [])
            activity.insert(
                0,
                {
                    "type": "error",
                    "message": f"Error: {error.message[:100]}{'...' if len(error.message) > 100 else ''}",
                    "timestamp": datetime.now().isoformat(),
                    "icon": "error",
                    "severity": error.severity.value,
                    "error_id": error.error_id,
                },
            )
            session["recent_activity"] = activity[:10]  # Keep last 10 activities
            session.modified = True
        except RuntimeError:
            # Outside request context
            pass

    def _create_api_response(
        self, error: ApplicationError, user_message: UserMessage
    ) -> Dict[str, Any]:
        """Create API response for error.

        Args:
            error: ApplicationError
            user_message: UserMessage for the error

        Returns:
            API response dictionary
        """
        error_detail = ErrorDetail(
            code=error.error_code.value,
            message=error.message,
            field=error.field,
            details=error.details,
        )

        return create_error_response(
            message=user_message.text,
            errors=[error_detail],
            status_code=self._get_http_status_code(error.error_code),
        )

    def _get_http_status_code(self, error_code: ErrorCode) -> int:
        """Get appropriate HTTP status code for error code.

        Args:
            error_code: ErrorCode to map

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
            ErrorCode.TIMEOUT_ERROR: 504,
        }

        return status_code_mapping.get(error_code, 500)

# Global instance
enhanced_error_handler = EnhancedErrorHandler()

def handle_error(
    error: Union[Exception, ApplicationError],
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    flash_message: bool = True,
) -> None:
    """Handle error with enhanced error handler.

    Args:
        error: Exception or ApplicationError to handle
        context: Additional context information
        user_id: User ID if available
        flash_message: Whether to flash message to user
    """
    enhanced_error_handler.handle_error(
        error=error, context=context, user_id=user_id, flash_message=flash_message
    )

def handle_api_error(
    error: Union[Exception, ApplicationError],
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle error and return API response.

    Args:
        error: Exception or ApplicationError to handle
        context: Additional context information
        user_id: User ID if available

    Returns:
        API response dictionary
    """
    return enhanced_error_handler.handle_error(
        error=error,
        context=context,
        user_id=user_id,
        flash_message=False,
        return_response=True,
    )

def get_error_metrics() -> Dict[str, Any]:
    """Get error metrics.

    Returns:
        Error metrics dictionary
    """
    return enhanced_error_handler.get_error_metrics()

def get_error_report() -> Dict[str, Any]:
    """Get error report.

    Returns:
        Error report dictionary
    """
    return enhanced_error_handler.get_error_report()
