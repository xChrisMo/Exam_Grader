"""
API response type classes for consistent response formatting
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    VALIDATION_ERROR = 'validation_error'
    UPLOAD_ERROR = 'upload_error'
    MODEL_ERROR = 'model_error'
    TRAINING_ERROR = 'training_error'
    API_ERROR = 'api_error'
    NETWORK_ERROR = 'network_error'


@dataclass
class ErrorResponse:
    type: ErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'type': self.type.value,
            'message': self.message
        }
        if self.details:
            result['details'] = self.details
        if self.suggestions:
            result['suggestions'] = self.suggestions
        return result


@dataclass
class PaginationInfo:
    page: int
    limit: int
    total: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'page': self.page,
            'limit': self.limit,
            'total': self.total,
            'totalPages': self.total_pages
        }


class ApiResponse:
    """Standard API response wrapper"""
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict[str, Any]:
        """Create successful response"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return response
    
    @staticmethod
    def error(error: ErrorResponse, message: str = None) -> Dict[str, Any]:
        """Create error response"""
        response = {
            'success': False,
            'error': error.to_dict()
        }
        if message:
            response['message'] = message
        return response
    
    @staticmethod
    def paginated(data: List[Any], pagination: PaginationInfo, message: str = None) -> Dict[str, Any]:
        """Create paginated response"""
        response = {
            'success': True,
            'data': data,
            'pagination': pagination.to_dict()
        }
        if message:
            response['message'] = message
        return response


class ValidationError:
    """Validation error details"""
    
    def __init__(self, field: str, message: str, code: str, value: Any = None):
        self.field = field
        self.message = message
        self.code = code
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'field': self.field,
            'message': self.message,
            'code': self.code
        }
        if self.value is not None:
            result['value'] = self.value
        return result


class ValidationWarning:
    """Validation warning details"""
    
    def __init__(self, field: str, message: str, suggestion: str = None):
        self.field = field
        self.message = message
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'field': self.field,
            'message': self.message
        }
        if self.suggestion:
            result['suggestion'] = self.suggestion
        return result


class ValidationResult:
    """Validation result container"""
    
    def __init__(self, is_valid: bool = True):
        self.is_valid = is_valid
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationWarning] = []
    
    def add_error(self, field: str, message: str, code: str, value: Any = None):
        """Add validation error"""
        self.errors.append(ValidationError(field, message, code, value))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, suggestion: str = None):
        """Add validation warning"""
        self.warnings.append(ValidationWarning(field, message, suggestion))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'isValid': self.is_valid,
            'errors': [error.to_dict() for error in self.errors],
            'warnings': [warning.to_dict() for warning in self.warnings]
        }