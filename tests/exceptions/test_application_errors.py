"""Tests for application error classes."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.exceptions.application_errors import (
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
    DatabaseError,
    ErrorSeverity
)
from src.models.api_responses import ErrorCode


class TestApplicationError:
    """Test ApplicationError base class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = ApplicationError("Test error")
        
        assert error.message == "Test error"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is False
        assert error.retry_after is None
        assert error.field is None
        assert isinstance(error.timestamp, datetime)
        assert error.error_id.startswith("ERR_")
        assert len(error.error_id) == 12  # ERR_ + 8 chars
    
    def test_error_with_all_parameters(self):
        """Test error creation with all parameters."""
        details = {"key": "value"}
        context = {"operation": "test"}
        original_error = ValueError("Original error")
        
        error = ApplicationError(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Custom user message",
            details=details,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_error=original_error,
            field="test_field",
            recoverable=True,
            retry_after=30
        )
        
        assert error.message == "Test error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.user_message == "Custom user message"
        assert error.details == details
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert error.original_error == original_error
        assert error.field == "test_field"
        assert error.recoverable is True
        assert error.retry_after == 30
    
    def test_default_user_messages(self):
        """Test default user messages for different error codes."""
        test_cases = [
            (ErrorCode.VALIDATION_ERROR, "Please check your input and try again."),
            (ErrorCode.AUTHENTICATION_ERROR, "Please log in to continue."),
            (ErrorCode.AUTHORIZATION_ERROR, "You don't have permission to perform this action."),
            (ErrorCode.NOT_FOUND, "The requested resource was not found."),
            (ErrorCode.PROCESSING_ERROR, "We're having trouble processing your request. Please try again."),
            (ErrorCode.SERVICE_UNAVAILABLE, "This service is temporarily unavailable. Please try again later."),
            (ErrorCode.RATE_LIMIT_EXCEEDED, "Too many requests. Please wait before trying again."),
            (ErrorCode.TIMEOUT_ERROR, "The request took too long to complete. Please try again."),
            (ErrorCode.INTERNAL_ERROR, "An unexpected error occurred. Please try again later.")
        ]
        
        for error_code, expected_message in test_cases:
            error = ApplicationError("Test", error_code=error_code)
            assert error.user_message == expected_message
    
    def test_original_error_details(self):
        """Test that original error details are added to error details."""
        original_error = ValueError("Original error message")
        error = ApplicationError("Test error", original_error=original_error)
        
        assert "original_error" in error.details
        assert error.details["original_error"]["type"] == "ValueError"
        assert error.details["original_error"]["message"] == "Original error message"
    
    def test_to_dict(self):
        """Test error serialization to dictionary."""
        error = ApplicationError(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            field="test_field",
            details={"key": "value"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_id"] == error.error_id
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        assert error_dict["message"] == "Test error"
        assert error_dict["field"] == "test_field"
        assert error_dict["details"] == {"key": "value"}
        assert error_dict["severity"] == "medium"
        assert "timestamp" in error_dict
    
    def test_string_representation(self):
        """Test string representation of error."""
        error = ApplicationError("Test error", error_code=ErrorCode.VALIDATION_ERROR)
        
        str_repr = str(error)
        assert "[VALIDATION_ERROR]" in str_repr
        assert "Test error" in str_repr
        assert error.error_id in str_repr
    
    def test_repr_representation(self):
        """Test repr representation of error."""
        error = ApplicationError("Test error", error_code=ErrorCode.VALIDATION_ERROR)
        
        repr_str = repr(error)
        assert "ApplicationError" in repr_str
        assert "Test error" in repr_str
        assert "VALIDATION_ERROR" in repr_str
        assert error.error_id in repr_str


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test validation error creation."""
        error = ValidationError("Invalid input", field="email")
        
        assert error.message == "Invalid input"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.field == "email"
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is True
    
    def test_validation_error_with_validation_errors(self):
        """Test validation error with validation error list."""
        validation_errors = [
            {"field": "email", "message": "Invalid email"},
            {"field": "password", "message": "Too short"}
        ]
        
        error = ValidationError(
            "Multiple validation errors",
            validation_errors=validation_errors
        )
        
        assert error.details["validation_errors"] == validation_errors


class TestAuthenticationError:
    """Test AuthenticationError class."""
    
    def test_authentication_error_creation(self):
        """Test authentication error creation."""
        error = AuthenticationError()
        
        assert error.message == "Authentication required"
        assert error.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert error.user_message == "Please log in to continue."
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
    
    def test_authentication_error_custom_message(self):
        """Test authentication error with custom message."""
        error = AuthenticationError("Invalid credentials")
        
        assert error.message == "Invalid credentials"
        assert error.error_code == ErrorCode.AUTHENTICATION_ERROR


class TestAuthorizationError:
    """Test AuthorizationError class."""
    
    def test_authorization_error_creation(self):
        """Test authorization error creation."""
        error = AuthorizationError()
        
        assert error.message == "Access denied"
        assert error.error_code == ErrorCode.AUTHORIZATION_ERROR
        assert error.user_message == "You don't have permission to perform this action."
        assert error.severity == ErrorSeverity.MEDIUM
    
    def test_authorization_error_with_resource(self):
        """Test authorization error with resource information."""
        error = AuthorizationError("Access denied", resource="marking_guide")
        
        assert error.details["resource"] == "marking_guide"


class TestNotFoundError:
    """Test NotFoundError class."""
    
    def test_not_found_error_creation(self):
        """Test not found error creation."""
        error = NotFoundError("Resource not found")
        
        assert error.message == "Resource not found"
        assert error.error_code == ErrorCode.NOT_FOUND
        assert error.user_message == "The requested resource was not found."
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is False
    
    def test_not_found_error_with_resource_info(self):
        """Test not found error with resource information."""
        error = NotFoundError(
            "User not found",
            resource_type="user",
            resource_id="123"
        )
        
        assert error.details["resource_type"] == "user"
        assert error.details["resource_id"] == "123"


class TestProcessingError:
    """Test ProcessingError class."""
    
    def test_processing_error_creation(self):
        """Test processing error creation."""
        error = ProcessingError("Processing failed")
        
        assert error.message == "Processing failed"
        assert error.error_code == ErrorCode.PROCESSING_ERROR
        assert error.user_message == "We're having trouble processing your request. Please try again."
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
    
    def test_processing_error_with_operation(self):
        """Test processing error with operation information."""
        error = ProcessingError("OCR failed", operation="ocr_processing")
        
        assert error.details["operation"] == "ocr_processing"


class TestServiceUnavailableError:
    """Test ServiceUnavailableError class."""
    
    def test_service_unavailable_error_creation(self):
        """Test service unavailable error creation."""
        error = ServiceUnavailableError("Service down")
        
        assert error.message == "Service down"
        assert error.error_code == ErrorCode.SERVICE_UNAVAILABLE
        assert error.user_message == "This service is temporarily unavailable. Please try again later."
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is True
        assert error.retry_after == 60
    
    def test_service_unavailable_error_with_service_name(self):
        """Test service unavailable error with service name."""
        error = ServiceUnavailableError("OCR service down", service_name="OCR")
        
        assert error.details["service_name"] == "OCR"


class TestRateLimitError:
    """Test RateLimitError class."""
    
    def test_rate_limit_error_creation(self):
        """Test rate limit error creation."""
        error = RateLimitError()
        
        assert error.message == "Rate limit exceeded"
        assert error.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert "60 seconds" in error.user_message
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert error.retry_after == 60
    
    def test_rate_limit_error_custom_retry_after(self):
        """Test rate limit error with custom retry after."""
        error = RateLimitError(retry_after=120)
        
        assert error.retry_after == 120
        assert "120 seconds" in error.user_message


class TestTimeoutError:
    """Test TimeoutError class."""
    
    def test_timeout_error_creation(self):
        """Test timeout error creation."""
        error = TimeoutError("Request timed out")
        
        assert error.message == "Request timed out"
        assert error.error_code == ErrorCode.TIMEOUT_ERROR
        assert error.user_message == "The request took too long to complete. Please try again."
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
    
    def test_timeout_error_with_duration(self):
        """Test timeout error with timeout duration."""
        error = TimeoutError("Request timed out", timeout_duration=30.5)
        
        assert error.details["timeout_duration"] == 30.5


class TestConfigurationError:
    """Test ConfigurationError class."""
    
    def test_configuration_error_creation(self):
        """Test configuration error creation."""
        error = ConfigurationError("Missing config")
        
        assert error.message == "Missing config"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.user_message == "A configuration error occurred. Please contact support."
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False
    
    def test_configuration_error_with_config_key(self):
        """Test configuration error with config key."""
        error = ConfigurationError("Missing API key", config_key="api_key")
        
        assert error.details["config_key"] == "api_key"


class TestFileOperationError:
    """Test FileOperationError class."""
    
    def test_file_operation_error_creation(self):
        """Test file operation error creation."""
        error = FileOperationError("File not found")
        
        assert error.message == "File not found"
        assert error.error_code == ErrorCode.PROCESSING_ERROR
        assert error.user_message == "File operation failed. Please try again."
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
    
    def test_file_operation_error_with_details(self):
        """Test file operation error with file details."""
        error = FileOperationError(
            "Cannot read file",
            file_path="/path/to/file.txt",
            operation="read"
        )
        
        assert error.details["file_path"] == "/path/to/file.txt"
        assert error.details["operation"] == "read"


class TestDatabaseError:
    """Test DatabaseError class."""
    
    def test_database_error_creation(self):
        """Test database error creation."""
        error = DatabaseError("Connection failed")
        
        assert error.message == "Connection failed"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.user_message == "A database error occurred. Please try again later."
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is True
    
    def test_database_error_with_details(self):
        """Test database error with operation details."""
        error = DatabaseError(
            "Query failed",
            operation="SELECT",
            table="users"
        )
        
        assert error.details["operation"] == "SELECT"
        assert error.details["table"] == "users"


class TestErrorIdGeneration:
    """Test error ID generation."""
    
    def test_unique_error_ids(self):
        """Test that error IDs are unique."""
        errors = [ApplicationError("Test") for _ in range(100)]
        error_ids = [error.error_id for error in errors]
        
        # All IDs should be unique
        assert len(set(error_ids)) == len(error_ids)
        
        # All IDs should follow the format
        for error_id in error_ids:
            assert error_id.startswith("ERR_")
            assert len(error_id) == 12
            assert error_id[4:].isupper()  # Hex part should be uppercase


class TestErrorInheritance:
    """Test error inheritance and polymorphism."""
    
    def test_all_errors_inherit_from_application_error(self):
        """Test that all custom errors inherit from ApplicationError."""
        error_classes = [
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
        ]
        
        for error_class in error_classes:
            error = error_class("Test")
            assert isinstance(error, ApplicationError)
            assert isinstance(error, Exception)
    
    def test_error_polymorphism(self):
        """Test that errors can be handled polymorphically."""
        errors = [
            ValidationError("Validation failed"),
            AuthenticationError("Auth failed"),
            ProcessingError("Processing failed")
        ]
        
        # All should be treatable as ApplicationError
        for error in errors:
            assert hasattr(error, 'error_id')
            assert hasattr(error, 'error_code')
            assert hasattr(error, 'to_dict')
            assert callable(error.to_dict)