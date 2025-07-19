"""Tests for error mapping and user-friendly message generation."""

import pytest
from unittest.mock import patch, MagicMock

from src.exceptions.error_mapper import (
    MessageSeverity,
    UserMessage,
    ErrorMapper,
    UserFriendlyErrorMapper,
    LocalizedErrorMapper,
    ContextAwareErrorMapper
)
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
    FileOperationError,
    DatabaseError,
    ErrorSeverity
)
from src.models.api_responses import ErrorCode


class TestMessageSeverity:
    """Test MessageSeverity enum."""
    
    def test_message_severity_values(self):
        """Test message severity enum values."""
        assert MessageSeverity.INFO.value == "info"
        assert MessageSeverity.WARNING.value == "warning"
        assert MessageSeverity.ERROR.value == "error"
        assert MessageSeverity.CRITICAL.value == "critical"
    
    def test_message_severity_ordering(self):
        """Test message severity ordering."""
        severities = [MessageSeverity.INFO, MessageSeverity.WARNING, 
                     MessageSeverity.ERROR, MessageSeverity.CRITICAL]
        
        # Test that they can be compared
        assert MessageSeverity.INFO < MessageSeverity.WARNING
        assert MessageSeverity.WARNING < MessageSeverity.ERROR
        assert MessageSeverity.ERROR < MessageSeverity.CRITICAL


class TestUserMessage:
    """Test UserMessage dataclass."""
    
    def test_user_message_creation(self):
        """Test user message creation."""
        message = UserMessage(
            text="Something went wrong",
            severity=MessageSeverity.ERROR,
            action_required=True,
            suggested_actions=["Try again", "Contact support"]
        )
        
        assert message.text == "Something went wrong"
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
        assert message.suggested_actions == ["Try again", "Contact support"]
    
    def test_user_message_defaults(self):
        """Test user message with default values."""
        message = UserMessage("Test message")
        
        assert message.text == "Test message"
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is False
        assert message.suggested_actions == []
    
    def test_user_message_to_dict(self):
        """Test user message serialization to dictionary."""
        message = UserMessage(
            text="Error occurred",
            severity=MessageSeverity.WARNING,
            action_required=True,
            suggested_actions=["Retry", "Check input"]
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["text"] == "Error occurred"
        assert message_dict["severity"] == "warning"
        assert message_dict["action_required"] is True
        assert message_dict["suggested_actions"] == ["Retry", "Check input"]


class TestErrorMapper:
    """Test ErrorMapper abstract base class."""
    
    def test_error_mapper_is_abstract(self):
        """Test that ErrorMapper cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ErrorMapper()
    
    def test_error_mapper_subclass_must_implement_map_error(self):
        """Test that subclasses must implement map_error method."""
        class IncompleteMapper(ErrorMapper):
            pass
        
        with pytest.raises(TypeError):
            IncompleteMapper()
    
    def test_error_mapper_subclass_implementation(self):
        """Test that proper subclass implementation works."""
        class TestMapper(ErrorMapper):
            def map_error(self, error, context=None):
                return UserMessage("Test message")
        
        mapper = TestMapper()
        error = ValidationError("Test error")
        message = mapper.map_error(error)
        
        assert isinstance(message, UserMessage)
        assert message.text == "Test message"


class TestUserFriendlyErrorMapper:
    """Test UserFriendlyErrorMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = UserFriendlyErrorMapper()
    
    def test_validation_error_mapping(self):
        """Test mapping of validation errors."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error)
        
        assert isinstance(message, UserMessage)
        assert "email" in message.text.lower()
        assert message.severity == MessageSeverity.WARNING
        assert message.action_required is True
        assert "check" in message.suggested_actions[0].lower()
    
    def test_validation_error_with_validation_errors(self):
        """Test mapping validation error with multiple validation errors."""
        validation_errors = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Password too short"}
        ]
        
        error = ValidationError(
            "Multiple validation errors",
            validation_errors=validation_errors
        )
        
        message = self.mapper.map_error(error)
        
        assert "email" in message.text.lower()
        assert "password" in message.text.lower()
        assert len(message.suggested_actions) > 0
    
    def test_authentication_error_mapping(self):
        """Test mapping of authentication errors."""
        error = AuthenticationError("Invalid credentials")
        message = self.mapper.map_error(error)
        
        assert "log in" in message.text.lower() or "sign in" in message.text.lower()
        assert message.severity == MessageSeverity.WARNING
        assert message.action_required is True
        assert any("credentials" in action.lower() for action in message.suggested_actions)
    
    def test_authorization_error_mapping(self):
        """Test mapping of authorization errors."""
        error = AuthorizationError("Access denied", resource="admin_panel")
        message = self.mapper.map_error(error)
        
        assert "permission" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
    
    def test_not_found_error_mapping(self):
        """Test mapping of not found errors."""
        error = NotFoundError(
            "User not found",
            resource_type="user",
            resource_id="123"
        )
        message = self.mapper.map_error(error)
        
        assert "not found" in message.text.lower()
        assert "user" in message.text.lower()
        assert message.severity == MessageSeverity.WARNING
    
    def test_processing_error_mapping(self):
        """Test mapping of processing errors."""
        error = ProcessingError("OCR processing failed", operation="ocr")
        message = self.mapper.map_error(error)
        
        assert "processing" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
        assert any("try again" in action.lower() for action in message.suggested_actions)
    
    def test_service_unavailable_error_mapping(self):
        """Test mapping of service unavailable errors."""
        error = ServiceUnavailableError("OCR service down", service_name="OCR")
        message = self.mapper.map_error(error)
        
        assert "unavailable" in message.text.lower() or "down" in message.text.lower()
        assert "ocr" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
    
    def test_rate_limit_error_mapping(self):
        """Test mapping of rate limit errors."""
        error = RateLimitError(retry_after=60)
        message = self.mapper.map_error(error)
        
        assert "too many" in message.text.lower() or "rate limit" in message.text.lower()
        assert "60" in message.text or "minute" in message.text.lower()
        assert message.severity == MessageSeverity.WARNING
        assert message.action_required is True
    
    def test_timeout_error_mapping(self):
        """Test mapping of timeout errors."""
        error = TimeoutError("Request timed out", timeout_duration=30.0)
        message = self.mapper.map_error(error)
        
        assert "timeout" in message.text.lower() or "too long" in message.text.lower()
        assert message.severity == MessageSeverity.WARNING
        assert message.action_required is True
    
    def test_file_operation_error_mapping(self):
        """Test mapping of file operation errors."""
        error = FileOperationError(
            "Cannot read file",
            file_path="/path/to/file.pdf",
            operation="read"
        )
        message = self.mapper.map_error(error)
        
        assert "file" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
    
    def test_database_error_mapping(self):
        """Test mapping of database errors."""
        error = DatabaseError("Connection failed", operation="SELECT")
        message = self.mapper.map_error(error)
        
        assert "temporarily unavailable" in message.text.lower() or "try again" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
    
    def test_generic_application_error_mapping(self):
        """Test mapping of generic application errors."""
        error = ApplicationError("Unknown error", error_code=ErrorCode.INTERNAL_ERROR)
        message = self.mapper.map_error(error)
        
        assert "unexpected error" in message.text.lower()
        assert message.severity == MessageSeverity.ERROR
        assert message.action_required is True
    
    def test_mapping_with_context(self):
        """Test error mapping with additional context."""
        error = ValidationError("Invalid input", field="email")
        context = {
            "user_type": "student",
            "operation": "registration",
            "attempt_count": 3
        }
        
        message = self.mapper.map_error(error, context=context)
        
        # Context should influence the message
        assert isinstance(message, UserMessage)
        assert message.action_required is True


class TestLocalizedErrorMapper:
    """Test LocalizedErrorMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = LocalizedErrorMapper()
    
    def test_english_localization(self):
        """Test English error message localization."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error, context={"language": "en"})
        
        assert isinstance(message, UserMessage)
        assert "email" in message.text.lower()
        # Should be in English (default)
        assert any(word in message.text.lower() for word in ["please", "check", "required"])
    
    def test_spanish_localization(self):
        """Test Spanish error message localization."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error, context={"language": "es"})
        
        assert isinstance(message, UserMessage)
        # Should contain Spanish words
        assert any(word in message.text.lower() for word in ["por favor", "correo", "requerido"])
    
    def test_french_localization(self):
        """Test French error message localization."""
        error = AuthenticationError("Invalid credentials")
        message = self.mapper.map_error(error, context={"language": "fr"})
        
        assert isinstance(message, UserMessage)
        # Should contain French words
        assert any(word in message.text.lower() for word in ["veuillez", "connexion", "identifiants"])
    
    def test_unsupported_language_fallback(self):
        """Test fallback to English for unsupported languages."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error, context={"language": "unsupported"})
        
        assert isinstance(message, UserMessage)
        # Should fall back to English
        assert any(word in message.text.lower() for word in ["please", "check", "email"])
    
    def test_no_language_context_fallback(self):
        """Test fallback to English when no language is specified."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error)
        
        assert isinstance(message, UserMessage)
        # Should fall back to English
        assert any(word in message.text.lower() for word in ["please", "check", "email"])
    
    def test_localized_suggested_actions(self):
        """Test that suggested actions are also localized."""
        error = ValidationError("Email is required", field="email")
        message = self.mapper.map_error(error, context={"language": "es"})
        
        assert len(message.suggested_actions) > 0
        # At least one action should contain Spanish words
        spanish_actions = [action for action in message.suggested_actions 
                          if any(word in action.lower() for word in ["verificar", "comprobar", "revisar"])]
        assert len(spanish_actions) > 0


class TestContextAwareErrorMapper:
    """Test ContextAwareErrorMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ContextAwareErrorMapper()
    
    def test_file_upload_context(self):
        """Test error mapping with file upload context."""
        error = ValidationError("File too large", field="file")
        context = {
            "operation": "file_upload",
            "file_type": "pdf",
            "file_size": 10485760,  # 10MB
            "max_size": 5242880     # 5MB
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "file" in message.text.lower()
        assert "size" in message.text.lower()
        assert "5 MB" in message.text or "5MB" in message.text
        assert message.action_required is True
        assert any("smaller" in action.lower() for action in message.suggested_actions)
    
    def test_login_context(self):
        """Test error mapping with login context."""
        error = AuthenticationError("Invalid credentials")
        context = {
            "operation": "login",
            "attempt_count": 3,
            "user_type": "student",
            "last_login": "2023-01-01"
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "credentials" in message.text.lower() or "password" in message.text.lower()
        assert message.action_required is True
        # Should suggest password reset after multiple attempts
        assert any("reset" in action.lower() for action in message.suggested_actions)
    
    def test_api_context(self):
        """Test error mapping with API context."""
        error = RateLimitError(retry_after=120)
        context = {
            "operation": "api_request",
            "endpoint": "/api/upload",
            "user_id": "user123",
            "requests_count": 100
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "requests" in message.text.lower()
        assert "120" in message.text or "2 minutes" in message.text.lower()
        assert message.action_required is True
    
    def test_processing_context(self):
        """Test error mapping with processing context."""
        error = ProcessingError("OCR failed", operation="ocr")
        context = {
            "operation": "document_processing",
            "document_type": "exam_submission",
            "page_count": 5,
            "processing_stage": "text_extraction"
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "document" in message.text.lower() or "processing" in message.text.lower()
        assert "exam" in message.text.lower() or "submission" in message.text.lower()
        assert message.action_required is True
    
    def test_field_specific_context(self):
        """Test error mapping with field-specific context."""
        error = ValidationError("Invalid format", field="student_id")
        context = {
            "field": "student_id",
            "expected_format": "XXXXXXXX",
            "provided_value": "12345",
            "validation_rule": "8_digits"
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "student id" in message.text.lower() or "student_id" in message.text.lower()
        assert "8" in message.text and "digits" in message.text.lower()
        assert message.action_required is True
        assert any("format" in action.lower() for action in message.suggested_actions)
    
    def test_user_type_context(self):
        """Test error mapping with user type context."""
        error = AuthorizationError("Access denied")
        context = {
            "user_type": "student",
            "required_role": "instructor",
            "resource": "marking_guide"
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "instructor" in message.text.lower() or "permission" in message.text.lower()
        assert "marking" in message.text.lower() or "guide" in message.text.lower()
        assert message.action_required is True
    
    def test_no_context_fallback(self):
        """Test that mapper works without context."""
        error = ValidationError("Invalid input", field="email")
        message = self.mapper.map_error(error)
        
        assert isinstance(message, UserMessage)
        assert "email" in message.text.lower()
        assert message.action_required is True
    
    def test_partial_context(self):
        """Test error mapping with partial context information."""
        error = FileOperationError("Cannot read file")
        context = {
            "operation": "file_upload"
            # Missing other context fields
        }
        
        message = self.mapper.map_error(error, context=context)
        
        assert "file" in message.text.lower()
        assert message.action_required is True
        # Should still provide helpful suggestions
        assert len(message.suggested_actions) > 0


class TestErrorMapperIntegration:
    """Test integration between different error mappers."""
    
    def test_mapper_comparison(self):
        """Test that different mappers produce different but valid messages."""
        error = ValidationError("Email is required", field="email")
        context = {
            "operation": "registration",
            "language": "en",
            "user_type": "student"
        }
        
        mappers = [
            UserFriendlyErrorMapper(),
            LocalizedErrorMapper(),
            ContextAwareErrorMapper()
        ]
        
        messages = [mapper.map_error(error, context=context) for mapper in mappers]
        
        # All should produce valid UserMessage objects
        for message in messages:
            assert isinstance(message, UserMessage)
            assert len(message.text) > 0
            assert message.severity in [MessageSeverity.INFO, MessageSeverity.WARNING, 
                                      MessageSeverity.ERROR, MessageSeverity.CRITICAL]
        
        # Messages might be different but should all be helpful
        for message in messages:
            assert "email" in message.text.lower()
    
    def test_mapper_chaining(self):
        """Test using multiple mappers in sequence."""
        error = ValidationError("Invalid input", field="password")
        context = {
            "language": "es",
            "operation": "login",
            "attempt_count": 2
        }
        
        # Use localized mapper first, then context-aware
        localized_mapper = LocalizedErrorMapper()
        context_mapper = ContextAwareErrorMapper()
        
        localized_message = localized_mapper.map_error(error, context=context)
        
        # Use the localized message text as input for context-aware mapping
        enhanced_context = context.copy()
        enhanced_context["localized_message"] = localized_message.text
        
        final_message = context_mapper.map_error(error, context=enhanced_context)
        
        assert isinstance(final_message, UserMessage)
        assert len(final_message.suggested_actions) > 0
    
    def test_error_mapper_factory_pattern(self):
        """Test a factory pattern for selecting appropriate mapper."""
        def get_mapper(context):
            """Factory function to select appropriate mapper based on context."""
            if context.get("language") and context["language"] != "en":
                return LocalizedErrorMapper()
            elif context.get("operation") or context.get("field"):
                return ContextAwareErrorMapper()
            else:
                return UserFriendlyErrorMapper()
        
        test_cases = [
            ({"language": "es"}, LocalizedErrorMapper),
            ({"operation": "file_upload"}, ContextAwareErrorMapper),
            ({"field": "email"}, ContextAwareErrorMapper),
            ({}, UserFriendlyErrorMapper)
        ]
        
        error = ValidationError("Test error")
        
        for context, expected_mapper_type in test_cases:
            mapper = get_mapper(context)
            assert isinstance(mapper, expected_mapper_type)
            
            message = mapper.map_error(error, context=context)
            assert isinstance(message, UserMessage)