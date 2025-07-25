"""Custom exception classes for the Exam Grader application."""

from .application_errors import (
    ApplicationError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ProcessingError,
    ServiceUnavailableError,
    RateLimitError,
    TimeoutError,
    ConfigurationError,
    FileOperationError,
    DatabaseError
)

from ..models.api_responses import ErrorCode


__all__ = [
    'ApplicationError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'NotFoundError',
    'ProcessingError',
    'ServiceUnavailableError',
    'RateLimitError',
    'TimeoutError',
    'ConfigurationError',
    'FileOperationError',
    'DatabaseError',
    'ErrorTracker',
    'ErrorAnalytics',
    'ErrorMapper',
    'UserFriendlyErrorMapper',
    'ErrorCode'
]