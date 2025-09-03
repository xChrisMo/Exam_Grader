"""Application-specific exception classes with standardized error handling."""

import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.api_responses import ErrorCode


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApplicationError(Exception):
    """Base application error class with enhanced error tracking.

    This class provides a standardized way to handle errors across the application
    with consistent error codes, user-friendly messages, and detailed context.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        field: Optional[str] = None,
        recoverable: bool = False,
        retry_after: Optional[int] = None,
    ):
        """Initialize application error.

        Args:
            message: Technical error message for developers
            error_code: Standardized error code
            user_message: User-friendly error message
            details: Additional error details
            severity: Error severity level
            context: Context information where error occurred
            original_error: Original exception that caused this error
            field: Field name for validation errors
            recoverable: Whether the error is recoverable
            retry_after: Seconds to wait before retry (for rate limiting)
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code
        self.user_message = user_message or self._get_default_user_message()
        self.details = details or {}
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error
        self.field = field
        self.recoverable = recoverable
        self.retry_after = retry_after

        # Metadata
        self.timestamp = datetime.utcnow()
        self.error_id = self._generate_error_id()
        self.traceback_info = traceback.format_exc() if original_error else None

        if original_error:
            self.details["original_error"] = {
                "type": type(original_error).__name__,
                "message": str(original_error),
            }

    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on error code."""
        user_messages = {
            ErrorCode.VALIDATION_ERROR: "Please check your input and try again.",
            ErrorCode.AUTHENTICATION_ERROR: "Please log in to continue.",
            ErrorCode.AUTHORIZATION_ERROR: "You don't have permission to perform this action.",
            ErrorCode.NOT_FOUND: "The requested resource was not found.",
            ErrorCode.PROCESSING_ERROR: "We're having trouble processing your request. Please try again.",
            ErrorCode.SERVICE_UNAVAILABLE: "This service is temporarily unavailable. Please try again later.",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please wait before trying again.",
            ErrorCode.TIMEOUT_ERROR: "The request took too long to complete. Please try again.",
            ErrorCode.INTERNAL_ERROR: "An unexpected error occurred. Please try again later.",
        }
        return user_messages.get(
            self.error_code, "An error occurred. Please try again."
        )

    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid

        return f"ERR_{uuid.uuid4().hex[:8].upper()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and API responses."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "error_code": self.error_code.value,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "field": self.field,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after,
            "details": self.details,
            "context": self.context,
            "traceback": self.traceback_info,
        }

    def __str__(self) -> str:
        """String representation of the error."""
        return f"[{self.error_code.value}] {self.message} (ID: {self.error_id})"

    def __repr__(self) -> str:
        """Detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code={self.error_code}, "
            f"severity={self.severity}, "
            f"error_id='{self.error_id}'"
            f")"
        )


class ValidationError(ApplicationError):
    """Validation error for input validation failures."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            validation_errors: List of validation error details
            **kwargs: Additional arguments for ApplicationError
        """
        details = kwargs.get("details", {})
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            field=field,
            details=details,
            severity=ErrorSeverity.LOW,
            recoverable=True,
            **kwargs,
        )


class AuthenticationError(ApplicationError):
    """Authentication error for login/auth failures."""

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            user_message="Please log in to continue.",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs,
        )


class AuthorizationError(ApplicationError):
    """Authorization error for permission failures."""

    def __init__(
        self, message: str = "Access denied", resource: Optional[str] = None, **kwargs
    ):
        details = kwargs.get("details", {})
        if resource:
            details["resource"] = resource

        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            user_message="You don't have permission to perform this action.",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class NotFoundError(ApplicationError):
    """Not found error for missing resources."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            user_message="The requested resource was not found.",
            details=details,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            **kwargs,
        )


class ProcessingError(ApplicationError):
    """Processing error for business logic failures."""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            user_message="We're having trouble processing your request. Please try again.",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs,
        )


class ServiceUnavailableError(ApplicationError):
    """Service unavailable error for external service failures."""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name

        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            user_message="This service is temporarily unavailable. Please try again later.",
            details=details,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            retry_after=kwargs.get("retry_after", 60),
            **kwargs,
        )


class RateLimitError(ApplicationError):
    """Rate limit error for too many requests."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int = 60, **kwargs
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            user_message=f"Too many requests. Please wait {retry_after} seconds before trying again.",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            retry_after=retry_after,
            **kwargs,
        )


class TimeoutError(ApplicationError):
    """Timeout error for operations that take too long."""

    def __init__(
        self, message: str, timeout_duration: Optional[float] = None, **kwargs
    ):
        details = kwargs.get("details", {})
        if timeout_duration:
            details["timeout_duration"] = timeout_duration

        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT_ERROR,
            user_message="The request took too long to complete. Please try again.",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs,
        )


class ConfigurationError(ApplicationError):
    """Configuration error for invalid or missing configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message=message,
            error_code=ErrorCode.INTERNAL_ERROR,
            user_message="A configuration error occurred. Please contact support.",
            details=details,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs,
        )


class FileOperationError(ApplicationError):
    """File operation error for file system operations."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            user_message="File operation failed. Please try again.",
            details=details,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs,
        )


class DatabaseError(ApplicationError):
    """Database error for database operation failures."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table

        super().__init__(
            message=message,
            error_code=ErrorCode.INTERNAL_ERROR,
            user_message="A database error occurred. Please try again later.",
            details=details,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            **kwargs,
        )
