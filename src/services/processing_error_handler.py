"""
Processing Error Handler - Enhanced error handling infrastructure for processing services.

This module provides comprehensive error handling with categorization, fallback strategies,
and retry mechanisms specifically designed for the processing system.
"""

import time
import random
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from src.exceptions.application_errors import (
    ApplicationError, ProcessingError, ServiceUnavailableError, 
    TimeoutError, ErrorSeverity
)
from src.models.api_responses import ErrorCode
from utils.logger import logger

class ErrorCategory(Enum):
    """Error categories for processing operations."""
    TRANSIENT = "transient"  # Temporary errors that can be retried
    PERMANENT = "permanent"  # Permanent errors that should not be retried
    CONFIGURATION = "configuration"  # Configuration-related errors
    DEPENDENCY = "dependency"  # Missing dependency errors
    RESOURCE = "resource"  # Resource exhaustion errors
    VALIDATION = "validation"  # Input validation errors

class FallbackStrategy(Enum):
    """Available fallback strategies."""
    RETRY = "retry"  # Retry the operation
    ALTERNATIVE_METHOD = "alternative_method"  # Use alternative method
    DEGRADED_SERVICE = "degraded_service"  # Continue with reduced functionality
    CACHED_RESULT = "cached_result"  # Use cached result if available
    DEFAULT_VALUE = "default_value"  # Return default value
    SKIP_OPERATION = "skip_operation"  # Skip the operation entirely

@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    service: str
    timestamp: datetime
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    file_path: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_multiplier: float = 1.5

@dataclass
class FallbackResult:
    """Result of a fallback operation."""
    success: bool
    data: Any = None
    strategy_used: Optional[FallbackStrategy] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ProcessingErrorHandler:
    """
    Central error handler for processing operations with categorization and fallback strategies.
    """
    
    def __init__(self):
        self.error_categories = {}
        self.fallback_strategies = {}
        self.retry_configs = {}
        self.error_history = []
        self.max_history_size = 1000
        
        # Initialize default configurations
        self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Set up default error categorization and retry configurations."""
        
        # Default error categorizations
        self.error_categories.update({
            # Transient errors
            'ConnectionError': ErrorCategory.TRANSIENT,
            'TimeoutError': ErrorCategory.TRANSIENT,
            'ServiceUnavailableError': ErrorCategory.TRANSIENT,
            'RateLimitError': ErrorCategory.TRANSIENT,
            'TemporaryFailure': ErrorCategory.TRANSIENT,
            
            # Permanent errors
            'ValidationError': ErrorCategory.PERMANENT,
            'AuthenticationError': ErrorCategory.PERMANENT,
            'AuthorizationError': ErrorCategory.PERMANENT,
            'NotFoundError': ErrorCategory.PERMANENT,
            'FileNotFoundError': ErrorCategory.PERMANENT,
            
            # Configuration errors
            'ConfigurationError': ErrorCategory.CONFIGURATION,
            'MissingConfigError': ErrorCategory.CONFIGURATION,
            
            # Dependency errors
            'ImportError': ErrorCategory.DEPENDENCY,
            'ModuleNotFoundError': ErrorCategory.DEPENDENCY,
            'MissingDependencyError': ErrorCategory.DEPENDENCY,
            
            # Resource errors
            'MemoryError': ErrorCategory.RESOURCE,
            'DiskSpaceError': ErrorCategory.RESOURCE,
            'ResourceExhaustedError': ErrorCategory.RESOURCE,
        })
        
        # Default retry configurations
        self.retry_configs.update({
            'ocr_processing': RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
            'llm_processing': RetryConfig(max_attempts=5, base_delay=0.5, max_delay=60.0),
            'file_processing': RetryConfig(max_attempts=2, base_delay=2.0, max_delay=20.0),
            'mapping_service': RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
            'grading_service': RetryConfig(max_attempts=3, base_delay=1.5, max_delay=45.0),
            'default': RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
        })
        
        # Default fallback strategies
        self.fallback_strategies.update({
            'ocr_processing': [
                FallbackStrategy.ALTERNATIVE_METHOD,
                FallbackStrategy.DEGRADED_SERVICE,
                FallbackStrategy.DEFAULT_VALUE
            ],
            'llm_processing': [
                FallbackStrategy.RETRY,
                FallbackStrategy.CACHED_RESULT,
                FallbackStrategy.DEGRADED_SERVICE
            ],
            'file_processing': [
                FallbackStrategy.ALTERNATIVE_METHOD,
                FallbackStrategy.RETRY,
                FallbackStrategy.SKIP_OPERATION
            ],
            'mapping_service': [
                FallbackStrategy.ALTERNATIVE_METHOD,
                FallbackStrategy.DEGRADED_SERVICE,
                FallbackStrategy.DEFAULT_VALUE
            ],
            'grading_service': [
                FallbackStrategy.CACHED_RESULT,
                FallbackStrategy.DEGRADED_SERVICE,
                FallbackStrategy.DEFAULT_VALUE
            ]
        })
    
    def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> Dict[str, Any]:
        """
        Handle error with comprehensive processing including categorization and fallback.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            Dictionary containing error handling results and recommendations
        """
        try:
            if not isinstance(error, ApplicationError):
                app_error = self._convert_to_application_error(error, context)
            else:
                app_error = error
            
            # Categorize the error
            category = self._categorize_error(error, context)
            
            # Get fallback strategy
            fallback_strategy = self._get_fallback_strategy(context.operation, category)
            
            should_retry = self._should_retry(error, context, category)
            
            # Log the error with context
            self._log_error_with_context(app_error, context, category)
            
            # Record error in history
            self._record_error_history(app_error, context, category)
            
            # Prepare error response
            error_response = {
                'error_id': app_error.error_id,
                'category': category.value,
                'severity': app_error.severity.value,
                'message': app_error.message,
                'user_message': app_error.user_message,
                'should_retry': should_retry,
                'fallback_strategy': fallback_strategy.value if fallback_strategy else None,
                'context': {
                    'operation': context.operation,
                    'service': context.service,
                    'timestamp': context.timestamp.isoformat(),
                    'user_id': context.user_id,
                    'request_id': context.request_id
                },
                'retry_config': self._get_retry_config(context.operation).to_dict() if should_retry else None,
                'recommendations': self._get_error_recommendations(category, context)
            }
            
            return error_response
            
        except Exception as handler_error:
            logger.error(f"Error in error handler: {handler_error}")
            # Return minimal error response
            return {
                'error_id': 'HANDLER_ERROR',
                'category': ErrorCategory.PERMANENT.value,
                'severity': ErrorSeverity.HIGH.value,
                'message': f"Error handler failed: {str(handler_error)}",
                'user_message': "An unexpected error occurred. Please try again.",
                'should_retry': False,
                'fallback_strategy': None,
                'context': {
                    'operation': context.operation if context else 'unknown',
                    'service': context.service if context else 'unknown',
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
    
    def _convert_to_application_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> ApplicationError:
        """Convert standard exception to ApplicationError."""
        error_type = type(error).__name__
        
        # Map to appropriate ApplicationError subclass
        if error_type in ['ConnectionError', 'requests.ConnectionError']:
            return ServiceUnavailableError(
                message=str(error),
                service_name=context.service,
                context=context.additional_data
            )
        elif error_type in ['TimeoutError', 'requests.Timeout']:
            return TimeoutError(
                message=str(error),
                context=context.additional_data
            )
        else:
            return ProcessingError(
                message=str(error),
                operation=context.operation,
                context=context.additional_data,
                original_error=error
            )
    
    def _categorize_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Categorize error based on type and context."""
        error_type = type(error).__name__
        
        # Check explicit categorization
        if error_type in self.error_categories:
            return self.error_categories[error_type]
        
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network']):
            return ErrorCategory.TRANSIENT
        elif any(keyword in error_message for keyword in ['not found', 'missing', 'invalid']):
            return ErrorCategory.PERMANENT
        elif any(keyword in error_message for keyword in ['import', 'module', 'dependency']):
            return ErrorCategory.DEPENDENCY
        elif any(keyword in error_message for keyword in ['memory', 'disk', 'resource']):
            return ErrorCategory.RESOURCE
        elif any(keyword in error_message for keyword in ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        
        return ErrorCategory.TRANSIENT
    
    def _get_fallback_strategy(
        self, 
        operation: str, 
        category: ErrorCategory
    ) -> Optional[FallbackStrategy]:
        """Get appropriate fallback strategy for operation and error category."""
        
        # Get operation-specific strategies
        strategies = self.fallback_strategies.get(operation, [])
        
        if not strategies:
            # Default strategies based on error category
            if category == ErrorCategory.TRANSIENT:
                return FallbackStrategy.RETRY
            elif category == ErrorCategory.DEPENDENCY:
                return FallbackStrategy.DEGRADED_SERVICE
            elif category == ErrorCategory.RESOURCE:
                return FallbackStrategy.CACHED_RESULT
            elif category == ErrorCategory.CONFIGURATION:
                return FallbackStrategy.DEFAULT_VALUE
            else:
                return FallbackStrategy.SKIP_OPERATION
        
        # Return first applicable strategy
        return strategies[0] if strategies else None
    
    def _should_retry(
        self, 
        error: Exception, 
        context: ErrorContext, 
        category: ErrorCategory
    ) -> bool:
        """Determine if error should be retried."""
        
        # Never retry permanent errors
        if category in [ErrorCategory.PERMANENT, ErrorCategory.VALIDATION]:
            return False
        
        # Always retry transient errors
        if category == ErrorCategory.TRANSIENT:
            return True
        
        # Check specific error types
        error_type = type(error).__name__
        non_retryable_types = [
            'ValidationError', 'AuthenticationError', 'AuthorizationError',
            'NotFoundError', 'FileNotFoundError'
        ]
        
        if error_type in non_retryable_types:
            return False
        
        error_message = str(error).lower()
        non_retryable_patterns = [
            'invalid', 'unauthorized', 'forbidden', 'not found',
            'bad request', 'malformed', 'syntax error'
        ]
        
        if any(pattern in error_message for pattern in non_retryable_patterns):
            return False
        
        return True
    
    def _get_retry_config(self, operation: str) -> RetryConfig:
        """Get retry configuration for operation."""
        return self.retry_configs.get(operation, self.retry_configs['default'])
    
    def _log_error_with_context(
        self, 
        error: ApplicationError, 
        context: ErrorContext, 
        category: ErrorCategory
    ):
        """Log error with comprehensive context information."""
        
        log_data = {
            'error_id': error.error_id,
            'error_type': type(error).__name__,
            'category': category.value,
            'severity': error.severity.value,
            'operation': context.operation,
            'service': context.service,
            'user_id': context.user_id,
            'request_id': context.request_id,
            'file_path': context.file_path,
            'message': error.message
        }
        
        # Add additional context data
        if context.additional_data:
            log_data.update(context.additional_data)
        
        # Log with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Processing error: {log_data}", exc_info=error.original_error)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"Processing error: {log_data}", exc_info=error.original_error)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Processing error: {log_data}")
        else:
            logger.info(f"Processing error: {log_data}")
    
    def _record_error_history(
        self, 
        error: ApplicationError, 
        context: ErrorContext, 
        category: ErrorCategory
    ):
        """Record error in history for analysis."""
        
        error_record = {
            'timestamp': context.timestamp,
            'error_id': error.error_id,
            'error_type': type(error).__name__,
            'category': category.value,
            'severity': error.severity.value,
            'operation': context.operation,
            'service': context.service,
            'message': error.message,
            'user_id': context.user_id,
            'request_id': context.request_id
        }
        
        self.error_history.append(error_record)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _get_error_recommendations(
        self, 
        category: ErrorCategory, 
        context: ErrorContext
    ) -> List[str]:
        """Get recommendations for handling the error."""
        
        recommendations = []
        
        if category == ErrorCategory.TRANSIENT:
            recommendations.extend([
                "Retry the operation after a brief delay",
                "Check network connectivity",
                "Verify service availability"
            ])
        elif category == ErrorCategory.DEPENDENCY:
            recommendations.extend([
                "Install missing dependencies",
                "Check system requirements",
                "Use fallback processing methods"
            ])
        elif category == ErrorCategory.CONFIGURATION:
            recommendations.extend([
                "Review configuration settings",
                "Check environment variables",
                "Verify file paths and permissions"
            ])
        elif category == ErrorCategory.RESOURCE:
            recommendations.extend([
                "Free up system resources",
                "Clear caches",
                "Reduce processing load"
            ])
        elif category == ErrorCategory.VALIDATION:
            recommendations.extend([
                "Validate input data",
                "Check data format and structure",
                "Review processing parameters"
            ])
        else:
            recommendations.extend([
                "Review error details",
                "Check system logs",
                "Contact support if issue persists"
            ])
        
        return recommendations
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics from history."""
        
        if not self.error_history:
            return {
                'total_errors': 0,
                'error_rate': 0.0,
                'categories': {},
                'services': {},
                'operations': {},
                'recent_errors': []
            }
        
        total_errors = len(self.error_history)
        
        # Count by category
        categories = {}
        for record in self.error_history:
            category = record['category']
            categories[category] = categories.get(category, 0) + 1
        
        # Count by service
        services = {}
        for record in self.error_history:
            service = record['service']
            services[service] = services.get(service, 0) + 1
        
        # Count by operation
        operations = {}
        for record in self.error_history:
            operation = record['operation']
            operations[operation] = operations.get(operation, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = self.error_history[-10:] if len(self.error_history) >= 10 else self.error_history
        
        return {
            'total_errors': total_errors,
            'categories': categories,
            'services': services,
            'operations': operations,
            'recent_errors': recent_errors,
            'history_size': len(self.error_history)
        }
    
    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        logger.info("Error history cleared")
    
    def register_error_category(self, error_type: str, category: ErrorCategory):
        """Register custom error categorization."""
        self.error_categories[error_type] = category
        logger.info(f"Registered error category: {error_type} -> {category.value}")
    
    def register_fallback_strategy(self, operation: str, strategies: List[FallbackStrategy]):
        """Register fallback strategies for operation."""
        self.fallback_strategies[operation] = strategies
        logger.info(f"Registered fallback strategies for {operation}: {[s.value for s in strategies]}")
    
    def register_retry_config(self, operation: str, config: RetryConfig):
        """Register retry configuration for operation."""
        self.retry_configs[operation] = config
        logger.info(f"Registered retry config for {operation}: {config}")

def retry_config_to_dict(self) -> Dict[str, Any]:
    """Convert RetryConfig to dictionary."""
    return {
        'max_attempts': self.max_attempts,
        'base_delay': self.base_delay,
        'max_delay': self.max_delay,
        'exponential_base': self.exponential_base,
        'jitter': self.jitter,
        'backoff_multiplier': self.backoff_multiplier
    }

# Add to_dict method to RetryConfig
RetryConfig.to_dict = retry_config_to_dict

# Global instance
processing_error_handler = ProcessingErrorHandler()