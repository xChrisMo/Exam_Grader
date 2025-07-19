"""Tests for validation models and utilities."""

import pytest
from src.models.validation import (
    ValidationError, ValidationResult, ValidationSeverity,
    CommonValidators, validate_request_data
)


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test validation error creation."""
        error = ValidationError(
            field="email",
            message="Invalid email format",
            code="INVALID_EMAIL",
            severity=ValidationSeverity.ERROR,
            value="invalid-email",
            constraint="email_format"
        )
        
        assert error.field == "email"
        assert error.message == "Invalid email format"
        assert error.code == "INVALID_EMAIL"
        assert error.severity == ValidationSeverity.ERROR
        assert error.value == "invalid-email"
        assert error.constraint == "email_format"
    
    def test_validation_error_to_dict(self):
        """Test validation error conversion to dictionary."""
        error = ValidationError(
            field="password",
            message="Password too short",
            code="MIN_LENGTH",
            value="123",
            constraint="8"
        )
        
        result = error.to_dict()
        
        assert result["field"] == "password"
        assert result["message"] == "Password too short"
        assert result["code"] == "MIN_LENGTH"
        assert result["severity"] == "error"
        assert result["value"] == "123"
        assert result["constraint"] == "8"
    
    def test_validation_error_minimal(self):
        """Test validation error with minimal fields."""
        error = ValidationError(
            field="name",
            message="Name is required",
            code="REQUIRED"
        )
        
        result = error.to_dict()
        
        assert result["field"] == "name"
        assert result["message"] == "Name is required"
        assert result["code"] == "REQUIRED"
        assert result["severity"] == "error"
        assert "value" not in result
        assert "constraint" not in result


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult.success()
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.has_errors() is False
        assert result.has_warnings() is False
    
    def test_validation_result_failure(self):
        """Test failed validation result."""
        error = ValidationError(
            field="test",
            message="Test error",
            code="TEST_ERROR"
        )
        
        result = ValidationResult.failure([error])
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.has_errors() is True
        assert result.errors[0] == error
    
    def test_add_error(self):
        """Test adding an error to validation result."""
        result = ValidationResult(is_valid=True)
        
        result.add_error(
            field="email",
            message="Invalid email",
            code="INVALID_EMAIL",
            value="bad-email",
            constraint="email_format"
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "email"
        assert result.errors[0].message == "Invalid email"
        assert result.errors[0].code == "INVALID_EMAIL"
        assert result.errors[0].severity == ValidationSeverity.ERROR
    
    def test_add_warning(self):
        """Test adding a warning to validation result."""
        result = ValidationResult(is_valid=True)
        
        result.add_warning(
            field="password",
            message="Password could be stronger",
            code="WEAK_PASSWORD"
        )
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.has_warnings() is True
        assert result.warnings[0].severity == ValidationSeverity.WARNING
    
    def test_get_error_messages(self):
        """Test getting error messages."""
        result = ValidationResult(is_valid=False)
        result.add_error("field1", "Error 1", "CODE1")
        result.add_error("field2", "Error 2", "CODE2")
        
        messages = result.get_error_messages()
        
        assert len(messages) == 2
        assert "Error 1" in messages
        assert "Error 2" in messages
    
    def test_get_warning_messages(self):
        """Test getting warning messages."""
        result = ValidationResult(is_valid=True)
        result.add_warning("field1", "Warning 1", "WARN1")
        result.add_warning("field2", "Warning 2", "WARN2")
        
        messages = result.get_warning_messages()
        
        assert len(messages) == 2
        assert "Warning 1" in messages
        assert "Warning 2" in messages
    
    def test_to_dict(self):
        """Test validation result conversion to dictionary."""
        result = ValidationResult(is_valid=False)
        result.add_error("field1", "Error message", "ERROR_CODE")
        result.add_warning("field2", "Warning message", "WARNING_CODE")
        
        dict_result = result.to_dict()
        
        assert dict_result["is_valid"] is False
        assert dict_result["error_count"] == 1
        assert dict_result["warning_count"] == 1
        assert len(dict_result["errors"]) == 1
        assert len(dict_result["warnings"]) == 1
        assert dict_result["errors"][0]["field"] == "field1"
        assert dict_result["warnings"][0]["field"] == "field2"


class TestCommonValidators:
    """Test CommonValidators class."""
    
    def test_required_validator_success(self):
        """Test required validator with valid input."""
        error = CommonValidators.required("valid value", "test_field")
        assert error is None
    
    def test_required_validator_failure_none(self):
        """Test required validator with None value."""
        error = CommonValidators.required(None, "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "REQUIRED_FIELD"
        assert "required" in error.message.lower()
    
    def test_required_validator_failure_empty_string(self):
        """Test required validator with empty string."""
        error = CommonValidators.required("", "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "REQUIRED_FIELD"
    
    def test_required_validator_failure_whitespace(self):
        """Test required validator with whitespace string."""
        error = CommonValidators.required("   ", "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "REQUIRED_FIELD"
    
    def test_min_length_validator_success(self):
        """Test min length validator with valid input."""
        error = CommonValidators.min_length("hello world", 5, "test_field")
        assert error is None
    
    def test_min_length_validator_failure(self):
        """Test min length validator with invalid input."""
        error = CommonValidators.min_length("hi", 5, "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "MIN_LENGTH"
        assert error.value == 2
        assert error.constraint == "5"
    
    def test_max_length_validator_success(self):
        """Test max length validator with valid input."""
        error = CommonValidators.max_length("hello", 10, "test_field")
        assert error is None
    
    def test_max_length_validator_failure(self):
        """Test max length validator with invalid input."""
        error = CommonValidators.max_length("this is too long", 5, "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "MAX_LENGTH"
        assert error.value == 16
        assert error.constraint == "5"
    
    def test_min_value_validator_success(self):
        """Test min value validator with valid input."""
        error = CommonValidators.min_value(10, 5, "test_field")
        assert error is None
    
    def test_min_value_validator_failure(self):
        """Test min value validator with invalid input."""
        error = CommonValidators.min_value(3, 5, "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "MIN_VALUE"
        assert error.value == 3
        assert error.constraint == "5"
    
    def test_max_value_validator_success(self):
        """Test max value validator with valid input."""
        error = CommonValidators.max_value(5, 10, "test_field")
        assert error is None
    
    def test_max_value_validator_failure(self):
        """Test max value validator with invalid input."""
        error = CommonValidators.max_value(15, 10, "test_field")
        
        assert error is not None
        assert error.field == "test_field"
        assert error.code == "MAX_VALUE"
        assert error.value == 15
        assert error.constraint == "10"
    
    def test_email_format_validator_success(self):
        """Test email format validator with valid email."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@example.org"
        ]
        
        for email in valid_emails:
            error = CommonValidators.email_format(email, "email")
            assert error is None, f"Valid email {email} should not produce error"
    
    def test_email_format_validator_failure(self):
        """Test email format validator with invalid email."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com"
        ]
        
        for email in invalid_emails:
            error = CommonValidators.email_format(email, "email")
            assert error is not None, f"Invalid email {email} should produce error"
            assert error.code == "INVALID_EMAIL"
    
    def test_file_extension_validator_success(self):
        """Test file extension validator with valid extension."""
        error = CommonValidators.file_extension(
            "document.pdf", ["pdf", "doc", "docx"], "file"
        )
        assert error is None
    
    def test_file_extension_validator_case_insensitive(self):
        """Test file extension validator is case insensitive."""
        error = CommonValidators.file_extension(
            "document.PDF", ["pdf", "doc"], "file"
        )
        assert error is None
    
    def test_file_extension_validator_failure(self):
        """Test file extension validator with invalid extension."""
        error = CommonValidators.file_extension(
            "document.txt", ["pdf", "doc"], "file"
        )
        
        assert error is not None
        assert error.field == "file"
        assert error.code == "INVALID_FILE_EXTENSION"
        assert error.value == "txt"
    
    def test_file_size_validator_success(self):
        """Test file size validator with valid size."""
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 3 * 1024 * 1024  # 3MB
        
        error = CommonValidators.file_size(file_size, max_size, "file")
        assert error is None
    
    def test_file_size_validator_failure(self):
        """Test file size validator with invalid size."""
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 10 * 1024 * 1024  # 10MB
        
        error = CommonValidators.file_size(file_size, max_size, "file")
        
        assert error is not None
        assert error.field == "file"
        assert error.code == "FILE_TOO_LARGE"
        assert error.value == file_size
        assert error.constraint == str(max_size)


class TestValidateRequestData:
    """Test validate_request_data function."""
    
    def test_validate_request_data_success(self):
        """Test successful validation of request data."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 25
        }
        
        validators = {
            "name": [lambda v, f: CommonValidators.required(v, f)],
            "email": [
                lambda v, f: CommonValidators.required(v, f),
                lambda v, f: CommonValidators.email_format(v, f)
            ],
            "age": [lambda v, f: CommonValidators.min_value(v, 18, f)]
        }
        
        result = validate_request_data(data, validators)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_request_data_failure(self):
        """Test failed validation of request data."""
        data = {
            "name": "",
            "email": "invalid-email",
            "age": 15
        }
        
        validators = {
            "name": [lambda v, f: CommonValidators.required(v, f)],
            "email": [
                lambda v, f: CommonValidators.required(v, f),
                lambda v, f: CommonValidators.email_format(v, f)
            ],
            "age": [lambda v, f: CommonValidators.min_value(v, 18, f)]
        }
        
        result = validate_request_data(data, validators)
        
        assert result.is_valid is False
        assert len(result.errors) == 3  # name required, email format, age min value
    
    def test_validate_request_data_missing_fields(self):
        """Test validation with missing fields."""
        data = {"name": "John"}
        
        validators = {
            "name": [lambda v, f: CommonValidators.required(v, f)],
            "email": [lambda v, f: CommonValidators.required(v, f)]
        }
        
        result = validate_request_data(data, validators)
        
        assert result.is_valid is False
        assert len(result.errors) == 1  # email required
        assert result.errors[0].field == "email"
    
    def test_validate_request_data_exception_handling(self):
        """Test validation with validator that raises exception."""
        data = {"test": "value"}
        
        def failing_validator(value, field):
            raise ValueError("Test exception")
        
        validators = {
            "test": [failing_validator]
        }
        
        result = validate_request_data(data, validators)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "VALIDATION_EXCEPTION"
        assert "Test exception" in result.errors[0].message


class TestValidationSeverityEnum:
    """Test ValidationSeverity enum."""
    
    def test_validation_severity_values(self):
        """Test validation severity enum values."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"