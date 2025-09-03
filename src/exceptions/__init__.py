"""Custom exception classes for the Exam Grader application."""

from ..models.api_responses import ErrorCode
from .application_errors import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    FileOperationError,
    NotFoundError,
    ProcessingError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)

__all__ = [
    "ApplicationError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ProcessingError",
    "ServiceUnavailableError",
    "RateLimitError",
    "TimeoutError",
    "ConfigurationError",
    "FileOperationError",
    "DatabaseError",
    "ErrorTracker",
    "ErrorAnalytics",
    "ErrorMapper",
    "UserFriendlyErrorMapper",
    "ErrorCode",
]
