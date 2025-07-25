"""Error mapping system for user-friendly error messages and localization."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List

from .application_errors import ApplicationError, ErrorCode


class MessageSeverity(Enum):
    """Message severity levels for user display."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class UserMessage:
    """User-friendly error message with context."""
    title: str
    message: str
    severity: MessageSeverity
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    help_text: Optional[str] = None
    dismissible: bool = True
    auto_dismiss_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'action_text': self.action_text,
            'action_url': self.action_url,
            'help_text': self.help_text,
            'dismissible': self.dismissible,
            'auto_dismiss_seconds': self.auto_dismiss_seconds
        }


class ErrorMapper(ABC):
    """Abstract base class for error mapping."""
    
    @abstractmethod
    def map_error(self, error: ApplicationError, context: Optional[Dict[str, Any]] = None) -> UserMessage:
        """Map an application error to a user-friendly message.
        
        Args:
            error: ApplicationError instance
            context: Additional context for message customization
            
        Returns:
            UserMessage instance
        """
        pass
    
    @abstractmethod
    def get_supported_error_codes(self) -> List[ErrorCode]:
        """Get list of supported error codes.
        
        Returns:
            List of supported ErrorCode values
        """
        pass


class UserFriendlyErrorMapper(ErrorMapper):
    """Default user-friendly error mapper with contextual messages."""
    
    def __init__(self, language: str = 'en'):
        """Initialize error mapper.
        
        Args:
            language: Language code for localization
        """
        self.language = language
        self._error_templates = self._load_error_templates()
        self._context_patterns = self._load_context_patterns()
    
    def map_error(self, error: ApplicationError, context: Optional[Dict[str, Any]] = None) -> UserMessage:
        """Map an application error to a user-friendly message.
        
        Args:
            error: ApplicationError instance
            context: Additional context for message customization
            
        Returns:
            UserMessage instance
        """
        context = context or {}
        
        # Get base template for error code
        template = self._error_templates.get(
            error.error_code,
            self._error_templates[ErrorCode.INTERNAL_ERROR]
        )
        
        # Apply context-specific customizations
        customized_template = self._apply_context_customizations(template, error, context)
        
        # Replace placeholders with actual values
        message_data = self._replace_placeholders(customized_template, error, context)
        
        return UserMessage(
            title=message_data['title'],
            message=message_data['message'],
            severity=MessageSeverity(message_data['severity']),
            action_text=message_data.get('action_text'),
            action_url=message_data.get('action_url'),
            help_text=message_data.get('help_text'),
            dismissible=message_data.get('dismissible', True),
            auto_dismiss_seconds=message_data.get('auto_dismiss_seconds')
        )
    
    def get_supported_error_codes(self) -> List[ErrorCode]:
        """Get list of supported error codes.
        
        Returns:
            List of supported ErrorCode values
        """
        return list(self._error_templates.keys())
    
    def _load_error_templates(self) -> Dict[ErrorCode, Dict[str, Any]]:
        """Load error message templates.
        
        Returns:
            Dictionary mapping error codes to message templates
        """
        return {
            ErrorCode.VALIDATION_ERROR: {
                'title': 'Input Error',
                'message': 'Please check your input and try again.',
                'severity': 'warning',
                'help_text': 'Make sure all required fields are filled out correctly.',
                'dismissible': True,
                'auto_dismiss_seconds': 10
            },
            ErrorCode.AUTHENTICATION_ERROR: {
                'title': 'Authentication Required',
                'message': 'Please log in to continue.',
                'severity': 'warning',
                'action_text': 'Log In',
                'action_url': '/login',
                'dismissible': False
            },
            ErrorCode.AUTHORIZATION_ERROR: {
                'title': 'Access Denied',
                'message': "You don't have permission to perform this action.",
                'severity': 'error',
                'help_text': 'Contact your administrator if you believe this is an error.',
                'dismissible': True
            },
            ErrorCode.NOT_FOUND: {
                'title': 'Not Found',
                'message': 'The requested resource was not found.',
                'severity': 'error',
                'action_text': 'Go Back',
                'action_url': 'javascript:history.back()',
                'dismissible': True
            },
            ErrorCode.PROCESSING_ERROR: {
                'title': 'Processing Error',
                'message': "We're having trouble processing your request. Please try again.",
                'severity': 'error',
                'action_text': 'Retry',
                'help_text': 'If the problem persists, please contact support.',
                'dismissible': True
            },
            ErrorCode.SERVICE_UNAVAILABLE: {
                'title': 'Service Unavailable',
                'message': 'This service is temporarily unavailable. Please try again later.',
                'severity': 'error',
                'action_text': 'Retry',
                'help_text': 'We are working to resolve this issue as quickly as possible.',
                'dismissible': True,
                'auto_dismiss_seconds': 15
            },
            ErrorCode.RATE_LIMIT_EXCEEDED: {
                'title': 'Too Many Requests',
                'message': 'You are making requests too quickly. Please wait before trying again.',
                'severity': 'warning',
                'help_text': 'Rate limiting helps us maintain service quality for all users.',
                'dismissible': True,
                'auto_dismiss_seconds': 30
            },
            ErrorCode.TIMEOUT_ERROR: {
                'title': 'Request Timeout',
                'message': 'The request took too long to complete. Please try again.',
                'severity': 'warning',
                'action_text': 'Retry',
                'help_text': 'Try breaking large operations into smaller chunks.',
                'dismissible': True
            },
            ErrorCode.INVALID_REQUEST: {
                'title': 'Invalid Request',
                'message': 'The request could not be processed due to invalid data.',
                'severity': 'error',
                'help_text': 'Please check your input and try again.',
                'dismissible': True
            },
            ErrorCode.INTERNAL_ERROR: {
                'title': 'System Error',
                'message': 'An unexpected error occurred. Please try again later.',
                'severity': 'error',
                'action_text': 'Contact Support',
                'action_url': '/support',
                'help_text': 'Our team has been notified and is working to resolve this issue.',
                'dismissible': True
            }
        }
    
    def _load_context_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load context-specific message patterns.
        
        Returns:
            Dictionary mapping context patterns to message customizations
        """
        return {
            'file_upload': {
                ErrorCode.VALIDATION_ERROR: {
                    'title': 'File Upload Error',
                    'message': 'The uploaded file is invalid or corrupted.',
                    'help_text': 'Please ensure the file is in the correct format and try again.'
                },
                ErrorCode.PROCESSING_ERROR: {
                    'title': 'File Processing Error',
                    'message': 'We could not process your uploaded file.',
                    'help_text': 'Try uploading a different file or contact support if the issue persists.'
                }
            },
            'grading': {
                ErrorCode.PROCESSING_ERROR: {
                    'title': 'Grading Error',
                    'message': 'We encountered an error while grading your submission.',
                    'help_text': 'Please try submitting again or contact your instructor.'
                },
                ErrorCode.SERVICE_UNAVAILABLE: {
                    'title': 'Grading Service Unavailable',
                    'message': 'The grading service is temporarily unavailable.',
                    'help_text': 'Your submission has been saved and will be graded when the service is restored.'
                }
            },
            'ocr': {
                ErrorCode.PROCESSING_ERROR: {
                    'title': 'Document Processing Error',
                    'message': 'We could not extract text from your document.',
                    'help_text': 'Please ensure the document is clear and readable, then try again.'
                },
                ErrorCode.SERVICE_UNAVAILABLE: {
                    'title': 'OCR Service Unavailable',
                    'message': 'The document processing service is temporarily unavailable.',
                    'help_text': 'Please try again in a few minutes.'
                }
            },
            'database': {
                ErrorCode.INTERNAL_ERROR: {
                    'title': 'Data Error',
                    'message': 'We encountered a problem accessing your data.',
                    'help_text': 'Please try again. If the problem persists, contact support.'
                }
            },
            'api': {
                ErrorCode.RATE_LIMIT_EXCEEDED: {
                    'message': 'API rate limit exceeded. Please wait {retry_after} seconds before trying again.'
                }
            }
        }
    
    def _apply_context_customizations(
        self,
        template: Dict[str, Any],
        error: ApplicationError,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply context-specific customizations to error template.
        
        Args:
            template: Base error template
            error: ApplicationError instance
            context: Context information
            
        Returns:
            Customized template
        """
        customized = template.copy()
        
        # Check for context-specific patterns
        for pattern, customizations in self._context_patterns.items():
            if pattern in context.get('operation', '').lower():
                error_customization = customizations.get(error.error_code, {})
                customized.update(error_customization)
                break
        
        return customized
    
    def _replace_placeholders(
        self,
        template: Dict[str, Any],
        error: ApplicationError,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Replace placeholders in template with actual values.
        
        Args:
            template: Message template
            error: ApplicationError instance
            context: Context information
            
        Returns:
            Template with replaced placeholders
        """
        result = {}
        
        # Prepare replacement values
        replacements = {
            'error_id': error.error_id,
            'field': error.field or 'input',
            'retry_after': str(error.retry_after or 60),
            'operation': context.get('operation', 'operation'),
            'resource': context.get('resource', 'resource'),
            'user_name': context.get('user_name', 'user')
        }
        
        # Add error details as replacements
        if error.details:
            replacements.update(error.details)
        
        # Replace placeholders in all string values
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = self._replace_string_placeholders(value, replacements)
            else:
                result[key] = value
        
        return result
    
    def _replace_string_placeholders(self, text: str, replacements: Dict[str, str]) -> str:
        """Replace placeholders in a string.
        
        Args:
            text: Text with placeholders
            replacements: Dictionary of replacement values
            
        Returns:
            Text with placeholders replaced
        """
        # Replace {key} style placeholders
        for key, value in replacements.items():
            text = text.replace(f'{{{key}}}', str(value))
        
        return text


class LocalizedErrorMapper(UserFriendlyErrorMapper):
    """Localized error mapper with multi-language support."""
    
    def __init__(self, language: str = 'en', fallback_language: str = 'en'):
        """Initialize localized error mapper.
        
        Args:
            language: Primary language code
            fallback_language: Fallback language code
        """
        self.fallback_language = fallback_language
        self._localized_templates = self._load_localized_templates()
        super().__init__(language)
    
    def _load_error_templates(self) -> Dict[ErrorCode, Dict[str, Any]]:
        """Load error message templates for the specified language.
        
        Returns:
            Dictionary mapping error codes to localized message templates
        """
        # Load templates for current language
        templates = self._localized_templates.get(self.language, {})
        
        # Fall back to default language if needed
        if not templates and self.language != self.fallback_language:
            templates = self._localized_templates.get(self.fallback_language, {})
        
        # Fall back to base templates if no localized templates found
        if not templates:
            return super()._load_error_templates()
        
        return templates
    
    def _load_localized_templates(self) -> Dict[str, Dict[ErrorCode, Dict[str, Any]]]:
        """Load localized error templates.
        
        Returns:
            Dictionary mapping language codes to error templates
        """
        # This would typically load from external files or database
        # For now, we'll include a few examples
        return {
            'en': super()._load_error_templates(),
            'es': {
                ErrorCode.VALIDATION_ERROR: {
                    'title': 'Error de Entrada',
                    'message': 'Por favor, revise su entrada e intente de nuevo.',
                    'severity': 'warning',
                    'help_text': 'Asegúrese de que todos los campos requeridos estén completados correctamente.',
                    'dismissible': True,
                    'auto_dismiss_seconds': 10
                },
                ErrorCode.AUTHENTICATION_ERROR: {
                    'title': 'Autenticación Requerida',
                    'message': 'Por favor, inicie sesión para continuar.',
                    'severity': 'warning',
                    'action_text': 'Iniciar Sesión',
                    'action_url': '/login',
                    'dismissible': False
                }
                # Add more Spanish translations as needed
            }
        }


class ContextAwareErrorMapper(UserFriendlyErrorMapper):
    """Context-aware error mapper that provides highly specific messages."""
    
    def __init__(self, language: str = 'en'):
        """Initialize context-aware error mapper.
        
        Args:
            language: Language code for localization
        """
        super().__init__(language)
        self._field_specific_messages = self._load_field_specific_messages()
    
    def map_error(self, error: ApplicationError, context: Optional[Dict[str, Any]] = None) -> UserMessage:
        """Map error with enhanced context awareness.
        
        Args:
            error: ApplicationError instance
            context: Additional context for message customization
            
        Returns:
            UserMessage instance with context-specific details
        """
        # Get base message
        base_message = super().map_error(error, context)
        
        # Apply field-specific customizations for validation errors
        if error.error_code == ErrorCode.VALIDATION_ERROR and error.field:
            field_message = self._get_field_specific_message(error.field, error.details)
            if field_message:
                base_message.message = field_message
        
        return base_message
    
    def _load_field_specific_messages(self) -> Dict[str, Dict[str, str]]:
        """Load field-specific validation messages.
        
        Returns:
            Dictionary mapping field names to validation messages
        """
        return {
            'email': {
                'required': 'Email address is required.',
                'invalid': 'Please enter a valid email address.',
                'duplicate': 'This email address is already registered.'
            },
            'password': {
                'required': 'Password is required.',
                'too_short': 'Password must be at least 8 characters long.',
                'too_weak': 'Password must contain uppercase, lowercase, numbers, and special characters.'
            },
            'file': {
                'required': 'Please select a file to upload.',
                'too_large': 'File size exceeds the maximum limit.',
                'invalid_type': 'File type is not supported.',
                'corrupted': 'The uploaded file appears to be corrupted.'
            },
            'student_id': {
                'invalid': 'Please enter a valid student ID.',
                'not_found': 'Student ID not found in the system.'
            },
            'marking_guide_id': {
                'required': 'Marking guide selection is required.',
                'invalid': 'Invalid marking guide selected.',
                'not_found': 'The selected marking guide was not found.'
            }
        }
    
    def _get_field_specific_message(self, field: str, details: Dict[str, Any]) -> Optional[str]:
        """Get field-specific validation message.
        
        Args:
            field: Field name
            details: Error details
            
        Returns:
            Field-specific message or None
        """
        field_messages = self._field_specific_messages.get(field, {})
        
        # Check for specific validation type in details
        validation_type = details.get('validation_type', 'invalid')
        return field_messages.get(validation_type, field_messages.get('invalid'))


# Global error mapper instance
_global_error_mapper = None


def get_error_mapper() -> ErrorMapper:
    """Get global error mapper instance.
    
    Returns:
        Global ErrorMapper instance
    """
    global _global_error_mapper
    if _global_error_mapper is None:
        _global_error_mapper = ContextAwareErrorMapper()
    return _global_error_mapper


def set_error_mapper(mapper: ErrorMapper) -> None:
    """Set global error mapper instance.
    
    Args:
        mapper: ErrorMapper instance to use globally
    """
    global _global_error_mapper
    _global_error_mapper = mapper


def map_error_to_user_message(
    error: ApplicationError,
    context: Optional[Dict[str, Any]] = None
) -> UserMessage:
    """Convenience function to map error to user message.
    
    Args:
        error: ApplicationError instance
        context: Additional context for message customization
        
    Returns:
        UserMessage instance
    """
    return get_error_mapper().map_error(error, context)