"""Standardized API response models for consistent response formatting."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from enum import Enum
from typing import Optional, Dict, Any, List

class ResponseStatus(Enum):
    """Standard response status codes."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"
    LOADING = "loading"

class ErrorCode(Enum):
    """Standard error codes for consistent error handling."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_REQUEST = "INVALID_REQUEST"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

@dataclass
class APIMetadata:
    """Metadata for API responses."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    version: str = "1.0"
    processing_time_ms: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "version": self.version,
            "processing_time_ms": self.processing_time_ms,
            "warnings": self.warnings
        }

@dataclass
class ErrorDetail:
    """Detailed error information."""
    code: ErrorCode
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error detail to dictionary."""
        result = {
            "code": self.code.value,
            "message": self.message
        }
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details
        return result

@dataclass
class APIResponse:
    """Standardized API response format."""
    status: ResponseStatus
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: List[ErrorDetail] = field(default_factory=list)
    metadata: APIMetadata = field(default_factory=APIMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "data": self.data,
            "metadata": self.metadata.to_dict()
        }
        
        if self.message:
            result["message"] = self.message
            
        if self.errors:
            result["errors"] = [error.to_dict() for error in self.errors]
            
        return result
    
    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def success(cls, data: Any = None, message: str = None, **kwargs) -> 'APIResponse':
        """Create a success response."""
        return cls(
            status=ResponseStatus.SUCCESS,
            data=data,
            message=message,
            **kwargs
        )
    
    @classmethod
    def error(cls, message: str, errors: List[ErrorDetail] = None, **kwargs) -> 'APIResponse':
        """Create an error response."""
        return cls(
            status=ResponseStatus.ERROR,
            message=message,
            errors=errors or [],
            **kwargs
        )
    
    @classmethod
    def loading(cls, operation_id: str, message: str = "Processing...", progress: Dict[str, Any] = None, **kwargs) -> 'APIResponse':
        """Create a loading response."""
        data = {"operation_id": operation_id}
        if progress:
            data["progress"] = progress
            
        return cls(
            status=ResponseStatus.LOADING,
            data=data,
            message=message,
            **kwargs
        )

@dataclass
class PaginationInfo:
    """Pagination information for paginated responses."""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination info to dictionary."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_page": self.next_page,
            "prev_page": self.prev_page
        }
    
    @classmethod
    def create(cls, page: int, per_page: int, total_items: int) -> 'PaginationInfo':
        """Create pagination info from basic parameters."""
        total_pages = (total_items + per_page - 1) // per_page if per_page > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        return cls(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None
        )

@dataclass
class PaginatedResponse(APIResponse):
    """Paginated API response format."""
    pagination: Optional[PaginationInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paginated response to dictionary."""
        result = super().to_dict()
        if self.pagination:
            result["pagination"] = self.pagination.to_dict()
        return result
    
    @classmethod
    def success_paginated(
        cls, 
        items: List[Any], 
        page: int, 
        per_page: int, 
        total_items: int,
        message: str = None,
        **kwargs
    ) -> 'PaginatedResponse':
        """Create a successful paginated response."""
        pagination = PaginationInfo.create(page, per_page, total_items)
        
        return cls(
            status=ResponseStatus.SUCCESS,
            data={
                "items": items,
                "count": len(items)
            },
            message=message,
            pagination=pagination,
            **kwargs
        )

@dataclass
class ErrorResponse(APIResponse):
    """Specialized error response."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.INTERNAL_ERROR, 
                 field: str = None, details: Dict[str, Any] = None, **kwargs):
        """Initialize error response."""
        error_detail = ErrorDetail(
            code=error_code,
            message=message,
            field=field,
            details=details
        )
        
        super().__init__(
            status=ResponseStatus.ERROR,
            message=message,
            errors=[error_detail],
            **kwargs
        )
    
    @classmethod
    def validation_error(cls, message: str, field: str = None, details: Dict[str, Any] = None) -> 'ErrorResponse':
        """Create a validation error response."""
        return cls(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            field=field,
            details=details
        )
    
    @classmethod
    def not_found(cls, resource: str = "Resource") -> 'ErrorResponse':
        """Create a not found error response."""
        return cls(
            message=f"{resource} not found",
            error_code=ErrorCode.NOT_FOUND
        )
    
    @classmethod
    def unauthorized(cls, message: str = "Authentication required") -> 'ErrorResponse':
        """Create an unauthorized error response."""
        return cls(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR
        )
    
    @classmethod
    def forbidden(cls, message: str = "Access denied") -> 'ErrorResponse':
        """Create a forbidden error response."""
        return cls(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR
        )
    
    @classmethod
    def service_unavailable(cls, service: str = "Service") -> 'ErrorResponse':
        """Create a service unavailable error response."""
        return cls(
            message=f"{service} is currently unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE
        )
    
    @classmethod
    def processing_error(cls, message: str = "Processing failed", details: Dict[str, Any] = None) -> 'ErrorResponse':
        """Create a processing error response."""
        return cls(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            details=details
        )

def create_success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """Create a success response dictionary."""
    return APIResponse.success(data=data, message=message).to_dict()

def create_error_response(message: str, error_code: ErrorCode = ErrorCode.INTERNAL_ERROR) -> Dict[str, Any]:
    """Create an error response dictionary."""
    return ErrorResponse(message=message, error_code=error_code).to_dict()

def create_loading_response(operation_id: str, message: str = "Processing...", progress: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a loading response dictionary."""
    return APIResponse.loading(operation_id=operation_id, message=message, progress=progress).to_dict()

def create_paginated_response(
    items: List[Any], 
    page: int, 
    per_page: int, 
    total_items: int,
    message: str = None
) -> Dict[str, Any]:
    """Create a paginated response dictionary."""
    return PaginatedResponse.success_paginated(
        items=items,
        page=page,
        per_page=per_page,
        total_items=total_items,
        message=message
    ).to_dict()