"""Tests for API response models."""

import pytest
import json
from datetime import datetime
from unittest.mock import patch

from src.models.api_responses import (
    APIResponse, PaginatedResponse, ErrorResponse, APIMetadata,
    ResponseStatus, ErrorCode, ErrorDetail, PaginationInfo,
    create_success_response, create_error_response, create_loading_response,
    create_paginated_response
)


class TestAPIMetadata:
    """Test APIMetadata class."""
    
    def test_metadata_creation(self):
        """Test metadata creation with default values."""
        metadata = APIMetadata()
        
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.request_id is None
        assert metadata.version == "1.0"
        assert metadata.processing_time_ms is None
        assert metadata.warnings == []
    
    def test_metadata_with_values(self):
        """Test metadata creation with custom values."""
        timestamp = datetime.utcnow()
        metadata = APIMetadata(
            timestamp=timestamp,
            request_id="test-123",
            version="2.0",
            processing_time_ms=150.5,
            warnings=["Test warning"]
        )
        
        assert metadata.timestamp == timestamp
        assert metadata.request_id == "test-123"
        assert metadata.version == "2.0"
        assert metadata.processing_time_ms == 150.5
        assert metadata.warnings == ["Test warning"]
    
    def test_metadata_to_dict(self):
        """Test metadata conversion to dictionary."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        metadata = APIMetadata(
            timestamp=timestamp,
            request_id="test-123",
            processing_time_ms=100.0,
            warnings=["warning1", "warning2"]
        )
        
        result = metadata.to_dict()
        
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["request_id"] == "test-123"
        assert result["version"] == "1.0"
        assert result["processing_time_ms"] == 100.0
        assert result["warnings"] == ["warning1", "warning2"]


class TestErrorDetail:
    """Test ErrorDetail class."""
    
    def test_error_detail_creation(self):
        """Test error detail creation."""
        error = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test error",
            field="test_field",
            details={"key": "value"}
        )
        
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Test error"
        assert error.field == "test_field"
        assert error.details == {"key": "value"}
    
    def test_error_detail_to_dict(self):
        """Test error detail conversion to dictionary."""
        error = ErrorDetail(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            field="id",
            details={"resource_type": "user"}
        )
        
        result = error.to_dict()
        
        assert result["code"] == "NOT_FOUND"
        assert result["message"] == "Resource not found"
        assert result["field"] == "id"
        assert result["details"] == {"resource_type": "user"}
    
    def test_error_detail_minimal(self):
        """Test error detail with minimal fields."""
        error = ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal error"
        )
        
        result = error.to_dict()
        
        assert result["code"] == "INTERNAL_ERROR"
        assert result["message"] == "Internal error"
        assert "field" not in result
        assert "details" not in result


class TestAPIResponse:
    """Test APIResponse class."""
    
    def test_success_response_creation(self):
        """Test creating a success response."""
        response = APIResponse.success(
            data={"key": "value"},
            message="Operation successful"
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert response.errors == []
        assert isinstance(response.metadata, APIMetadata)
    
    def test_error_response_creation(self):
        """Test creating an error response."""
        error_detail = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation failed"
        )
        
        response = APIResponse.error(
            message="Request failed",
            errors=[error_detail]
        )
        
        assert response.status == ResponseStatus.ERROR
        assert response.message == "Request failed"
        assert len(response.errors) == 1
        assert response.errors[0] == error_detail
    
    def test_loading_response_creation(self):
        """Test creating a loading response."""
        progress = {"percentage": 50, "stage": "processing"}
        
        response = APIResponse.loading(
            operation_id="op-123",
            message="Processing request",
            progress=progress
        )
        
        assert response.status == ResponseStatus.LOADING
        assert response.message == "Processing request"
        assert response.data["operation_id"] == "op-123"
        assert response.data["progress"] == progress
    
    def test_response_to_dict(self):
        """Test response conversion to dictionary."""
        response = APIResponse.success(
            data={"test": "data"},
            message="Success"
        )
        
        result = response.to_dict()
        
        assert result["status"] == "success"
        assert result["data"] == {"test": "data"}
        assert result["message"] == "Success"
        assert "metadata" in result
        assert "errors" not in result  # Empty errors should not be included
    
    def test_response_to_json(self):
        """Test response conversion to JSON string."""
        response = APIResponse.success(data={"key": "value"})
        
        json_str = response.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["status"] == "success"
        assert parsed["data"] == {"key": "value"}
    
    def test_response_with_errors(self):
        """Test response with errors included in dict."""
        error = ErrorDetail(code=ErrorCode.VALIDATION_ERROR, message="Error")
        response = APIResponse.error(message="Failed", errors=[error])
        
        result = response.to_dict()
        
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "VALIDATION_ERROR"


class TestPaginationInfo:
    """Test PaginationInfo class."""
    
    def test_pagination_creation(self):
        """Test pagination info creation."""
        pagination = PaginationInfo.create(
            page=2,
            per_page=10,
            total_items=25
        )
        
        assert pagination.page == 2
        assert pagination.per_page == 10
        assert pagination.total_items == 25
        assert pagination.total_pages == 3
        assert pagination.has_next is True
        assert pagination.has_prev is True
        assert pagination.next_page == 3
        assert pagination.prev_page == 1
    
    def test_pagination_first_page(self):
        """Test pagination for first page."""
        pagination = PaginationInfo.create(
            page=1,
            per_page=10,
            total_items=25
        )
        
        assert pagination.has_prev is False
        assert pagination.prev_page is None
        assert pagination.has_next is True
        assert pagination.next_page == 2
    
    def test_pagination_last_page(self):
        """Test pagination for last page."""
        pagination = PaginationInfo.create(
            page=3,
            per_page=10,
            total_items=25
        )
        
        assert pagination.has_next is False
        assert pagination.next_page is None
        assert pagination.has_prev is True
        assert pagination.prev_page == 2
    
    def test_pagination_to_dict(self):
        """Test pagination conversion to dictionary."""
        pagination = PaginationInfo.create(page=2, per_page=5, total_items=12)
        
        result = pagination.to_dict()
        
        expected_keys = [
            'page', 'per_page', 'total_items', 'total_pages',
            'has_next', 'has_prev', 'next_page', 'prev_page'
        ]
        
        for key in expected_keys:
            assert key in result
        
        assert result['page'] == 2
        assert result['total_pages'] == 3


class TestPaginatedResponse:
    """Test PaginatedResponse class."""
    
    def test_paginated_response_creation(self):
        """Test creating a paginated response."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        response = PaginatedResponse.success_paginated(
            items=items,
            page=1,
            per_page=10,
            total_items=3,
            message="Items retrieved"
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["items"] == items
        assert response.data["count"] == 3
        assert response.message == "Items retrieved"
        assert isinstance(response.pagination, PaginationInfo)
    
    def test_paginated_response_to_dict(self):
        """Test paginated response conversion to dictionary."""
        items = [{"id": 1}]
        
        response = PaginatedResponse.success_paginated(
            items=items,
            page=1,
            per_page=10,
            total_items=1
        )
        
        result = response.to_dict()
        
        assert "pagination" in result
        assert result["data"]["items"] == items
        assert result["data"]["count"] == 1
        assert result["pagination"]["total_items"] == 1


class TestErrorResponse:
    """Test ErrorResponse class."""
    
    def test_error_response_creation(self):
        """Test creating an error response."""
        response = ErrorResponse(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            field="test_field",
            details={"key": "value"}
        )
        
        assert response.status == ResponseStatus.ERROR
        assert response.message == "Test error"
        assert len(response.errors) == 1
        assert response.errors[0].code == ErrorCode.VALIDATION_ERROR
        assert response.errors[0].field == "test_field"
    
    def test_validation_error_class_method(self):
        """Test validation error class method."""
        response = ErrorResponse.validation_error(
            message="Invalid input",
            field="email",
            details={"pattern": "email"}
        )
        
        assert response.errors[0].code == ErrorCode.VALIDATION_ERROR
        assert response.errors[0].field == "email"
    
    def test_not_found_class_method(self):
        """Test not found error class method."""
        response = ErrorResponse.not_found("User")
        
        assert response.message == "User not found"
        assert response.errors[0].code == ErrorCode.NOT_FOUND
    
    def test_unauthorized_class_method(self):
        """Test unauthorized error class method."""
        response = ErrorResponse.unauthorized()
        
        assert response.message == "Authentication required"
        assert response.errors[0].code == ErrorCode.AUTHENTICATION_ERROR
    
    def test_service_unavailable_class_method(self):
        """Test service unavailable error class method."""
        response = ErrorResponse.service_unavailable("OCR Service")
        
        assert response.message == "OCR Service is currently unavailable"
        assert response.errors[0].code == ErrorCode.SERVICE_UNAVAILABLE


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_success_response(self):
        """Test create_success_response utility function."""
        result = create_success_response(
            data={"key": "value"},
            message="Success"
        )
        
        assert result["status"] == "success"
        assert result["data"] == {"key": "value"}
        assert result["message"] == "Success"
    
    def test_create_error_response(self):
        """Test create_error_response utility function."""
        result = create_error_response(
            message="Error occurred",
            error_code=ErrorCode.VALIDATION_ERROR
        )
        
        assert result["status"] == "error"
        assert result["message"] == "Error occurred"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "VALIDATION_ERROR"
    
    def test_create_loading_response(self):
        """Test create_loading_response utility function."""
        progress = {"percentage": 75}
        
        result = create_loading_response(
            operation_id="op-456",
            message="Processing",
            progress=progress
        )
        
        assert result["status"] == "loading"
        assert result["data"]["operation_id"] == "op-456"
        assert result["data"]["progress"] == progress
        assert result["message"] == "Processing"
    
    def test_create_paginated_response(self):
        """Test create_paginated_response utility function."""
        items = [{"id": 1}, {"id": 2}]
        
        result = create_paginated_response(
            items=items,
            page=1,
            per_page=10,
            total_items=2,
            message="Items found"
        )
        
        assert result["status"] == "success"
        assert result["data"]["items"] == items
        assert result["data"]["count"] == 2
        assert result["pagination"]["total_items"] == 2
        assert result["message"] == "Items found"


class TestResponseStatusEnum:
    """Test ResponseStatus enum."""
    
    def test_response_status_values(self):
        """Test response status enum values."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.ERROR.value == "error"
        assert ResponseStatus.WARNING.value == "warning"
        assert ResponseStatus.PARTIAL.value == "partial"
        assert ResponseStatus.LOADING.value == "loading"


class TestErrorCodeEnum:
    """Test ErrorCode enum."""
    
    def test_error_code_values(self):
        """Test error code enum values."""
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.AUTHENTICATION_ERROR.value == "AUTHENTICATION_ERROR"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.SERVICE_UNAVAILABLE.value == "SERVICE_UNAVAILABLE"