"""Validation models and utilities for API request/response validation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class ValidationSeverity(Enum):
    """Validation error severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationError:
    """Individual validation error."""

    field: str
    message: str
    code: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    value: Optional[Any] = None
    constraint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation error to dictionary."""
        result = {
            "field": self.field,
            "message": self.message,
            "code": self.code,
            "severity": self.severity.value,
        }

        if self.value is not None:
            result["value"] = self.value
        if self.constraint:
            result["constraint"] = self.constraint

        return result

@dataclass
class ValidationResult:
    """Result of validation operation."""

    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_ERROR",
        value: Any = None,
        constraint: str = None,
    ) -> None:
        """Add a validation error."""
        error = ValidationError(
            field=field,
            message=message,
            code=code,
            severity=ValidationSeverity.ERROR,
            value=value,
            constraint=constraint,
        )
        self.errors.append(error)
        self.is_valid = False

    def add_warning(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_WARNING",
        value: Any = None,
        constraint: str = None,
    ) -> None:
        """Add a validation warning."""
        warning = ValidationError(
            field=field,
            message=message,
            code=code,
            severity=ValidationSeverity.WARNING,
            value=value,
            constraint=constraint,
        )
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return len(self.warnings) > 0

    def get_error_messages(self) -> List[str]:
        """Get list of error messages."""
        return [error.message for error in self.errors]

    def get_warning_messages(self) -> List[str]:
        """Get list of warning messages."""
        return [warning.message for warning in self.warnings]

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True)

    @classmethod
    def failure(cls, errors: List[ValidationError] = None) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors or [])

class CommonValidators:
    """Common validation functions."""

    @staticmethod
    def required(value: Any, field: str) -> Optional[ValidationError]:
        """Validate that a field is required."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return ValidationError(
                field=field,
                message=f"{field} is required",
                code="REQUIRED_FIELD",
                value=value,
            )
        return None

    @staticmethod
    def min_length(value: str, min_len: int, field: str) -> Optional[ValidationError]:
        """Validate minimum string length."""
        if value and len(value) < min_len:
            return ValidationError(
                field=field,
                message=f"{field} must be at least {min_len} characters long",
                code="MIN_LENGTH",
                value=len(value),
                constraint=str(min_len),
            )
        return None

    @staticmethod
    def max_length(value: str, max_len: int, field: str) -> Optional[ValidationError]:
        """Validate maximum string length."""
        if value and len(value) > max_len:
            return ValidationError(
                field=field,
                message=f"{field} must be no more than {max_len} characters long",
                code="MAX_LENGTH",
                value=len(value),
                constraint=str(max_len),
            )
        return None

    @staticmethod
    def min_value(
        value: Union[int, float], min_val: Union[int, float], field: str
    ) -> Optional[ValidationError]:
        """Validate minimum numeric value."""
        if value is not None and value < min_val:
            return ValidationError(
                field=field,
                message=f"{field} must be at least {min_val}",
                code="MIN_VALUE",
                value=value,
                constraint=str(min_val),
            )
        return None

    @staticmethod
    def max_value(
        value: Union[int, float], max_val: Union[int, float], field: str
    ) -> Optional[ValidationError]:
        """Validate maximum numeric value."""
        if value is not None and value > max_val:
            return ValidationError(
                field=field,
                message=f"{field} must be no more than {max_val}",
                code="MAX_VALUE",
                value=value,
                constraint=str(max_val),
            )
        return None

    @staticmethod
    def email_format(value: str, field: str) -> Optional[ValidationError]:
        """Validate email format."""
        if value:
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, value):
                return ValidationError(
                    field=field,
                    message=f"{field} must be a valid email address",
                    code="INVALID_EMAIL",
                    value=value,
                )
        return None

    @staticmethod
    def file_extension(
        filename: str, allowed_extensions: List[str], field: str
    ) -> Optional[ValidationError]:
        """Validate file extension."""
        if filename:
            extension = filename.lower().split(".")[-1] if "." in filename else ""
            if extension not in [ext.lower() for ext in allowed_extensions]:
                return ValidationError(
                    field=field,
                    message=f"{field} must have one of these extensions: {', '.join(allowed_extensions)}",
                    code="INVALID_FILE_EXTENSION",
                    value=extension,
                    constraint=", ".join(allowed_extensions),
                )
        return None

    @staticmethod
    def file_size(
        file_size: int, max_size: int, field: str
    ) -> Optional[ValidationError]:
        """Validate file size in bytes."""
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            return ValidationError(
                field=field,
                message=f"{field} size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)",
                code="FILE_TOO_LARGE",
                value=file_size,
                constraint=str(max_size),
            )
        return None

def validate_request_data(
    data: Dict[str, Any], validators: Dict[str, List[callable]]
) -> ValidationResult:
    """Validate request data using provided validators.

    Args:
        data: Dictionary of data to validate
        validators: Dictionary mapping field names to lists of validator functions

    Returns:
        ValidationResult with any errors found
    """
    result = ValidationResult(is_valid=True)

    for field, field_validators in validators.items():
        value = data.get(field)

        for validator in field_validators:
            try:
                error = validator(value, field)
                if error:
                    result.errors.append(error)
                    result.is_valid = False
            except Exception as e:
                result.add_error(
                    field=field,
                    message=f"Validation error: {str(e)}",
                    code="VALIDATION_EXCEPTION",
                )

    return result
