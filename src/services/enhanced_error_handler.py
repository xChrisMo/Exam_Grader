"""
Enhanced Error Handling Infrastructure

This module provides comprehensive error handling with categorization,
fallback strategies, and retry mechanisms for the processing system.
"""

import time
import random
import traceback
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime

from utils.logger import logger

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"
    RECOVERABLE = "recoverable"
    WARNING = "warning"
    INFO = "info"

class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"
    RESOURCE = "resource"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    service: str
    timestamp: datetime
    user_id: Optional[str]
    request_id: str
    additional_data: Dict[str, Any]

@dataclass
class ErrorResponse:
    """Standardized error response"""
    success: bool = False
    error_code: str = ""
    error_message: str = ""
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    category: ErrorCategory = ErrorCategory.UNKNOWN
    fallback_used: bool = False
    retry_attempted: bool = False
    context: Optional[ErrorContext] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[str] = None
    
    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                'timeout', 'connection', 'network', 'temporary',
                'rate limit', 'server error', '429', '500', '502', '503', '504'
            ]

class FallbackStrategy:
    """Base class for fallback strategies"""
    
    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this strategy can handle the error"""
        return True
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute the fallback strategy"""
        # Default implementation - return None to indicate no fallback action
        # Subclasses should override this method with specific fallback logic
        return None

class ProcessingErrorHandler:
    """Central error handling system with categorization and fallback"""
    
    def __init__(self):
        self.fallback_strategies: Dict[str, List[FallbackStrategy]] = {}
        self.error_stats: Dict[str, int] = {}
        self.retry_config = RetryConfig()
        
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorResponse:
        """Handle an error with appropriate categorization and response"""
        try:
            # Categorize the error
            severity = self._categorize_severity(error)
            category = self._categorize_error(error)
            
            # Create error response
            response = ErrorResponse(
                error_code=self._generate_error_code(error, category),
                error_message=str(error),
                severity=severity,
                category=category,
                context=context
            )
            
            # Add suggestions based on error type
            response.suggestions = self._get_error_suggestions(error, category)
            
            # Update error statistics
            self._update_error_stats(category.value)
            
            # Log the error
            self._log_error(error, response, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return ErrorResponse(
                error_code="HANDLER_ERROR",
                error_message="Error handling failed",
                severity=ErrorSeverity.CRITICAL
            )
    
    def _categorize_severity(self, error: Exception) -> ErrorSeverity:
        """Categorize error severity"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Critical errors that require immediate attention
        critical_indicators = [
            'database', 'connection pool', 'out of memory', 'disk full',
            'permission denied', 'authentication failed', 'security'
        ]
        
        # Recoverable errors that can be retried
        recoverable_indicators = [
            'timeout', 'connection', 'network', 'temporary', 'rate limit',
            'server error', 'service unavailable'
        ]
        
        # Warning level errors
        warning_indicators = [
            'deprecated', 'fallback', 'degraded', 'missing optional'
        ]
        
        for indicator in critical_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.CRITICAL
        
        for indicator in recoverable_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.RECOVERABLE
        
        for indicator in warning_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.WARNING
        
        return ErrorSeverity.RECOVERABLE
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error by type"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        category_mapping = {
            ErrorCategory.NETWORK: ['connection', 'timeout', 'network', 'dns', 'socket'],
            ErrorCategory.DEPENDENCY: ['import', 'module', 'package', 'library', 'dependency'],
            ErrorCategory.VALIDATION: ['validation', 'invalid', 'format', 'parse', 'decode'],
            ErrorCategory.RESOURCE: ['memory', 'disk', 'file', 'resource', 'limit'],
            ErrorCategory.PROCESSING: ['processing', 'calculation', 'algorithm', 'logic'],
            ErrorCategory.CONFIGURATION: ['config', 'setting', 'parameter', 'environment']
        }
        
        for category, indicators in category_mapping.items():
            for indicator in indicators:
                if indicator in error_str or indicator in error_type:
                    return category
        
        return ErrorCategory.UNKNOWN
    
    def _generate_error_code(self, error: Exception, category: ErrorCategory) -> str:
        """Generate a standardized error code"""
        error_type = type(error).__name__.upper()
        category_code = category.value.upper()
        timestamp = int(time.time()) % 10000
        
        return f"{category_code}_{error_type}_{timestamp}"
    
    def _get_error_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """Get suggestions for resolving the error"""
        suggestions = []
        error_str = str(error).lower()
        
        if category == ErrorCategory.DEPENDENCY:
            if 'import' in error_str or 'module' in error_str:
                suggestions.append("Install missing Python package using pip")
                suggestions.append("Check if the package name is correct")
                suggestions.append("Verify virtual environment is activated")
        
        elif category == ErrorCategory.NETWORK:
            suggestions.append("Check internet connection")
            suggestions.append("Verify API endpoints are accessible")
            suggestions.append("Check firewall and proxy settings")
        
        elif category == ErrorCategory.RESOURCE:
            suggestions.append("Check available disk space")
            suggestions.append("Monitor memory usage")
            suggestions.append("Clear temporary files")
        
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.append("Verify configuration file exists")
            suggestions.append("Check environment variables")
            suggestions.append("Validate configuration syntax")
        
        # Add general suggestions
        suggestions.append("Check application logs for more details")
        suggestions.append("Retry the operation if it's transient")
        
        return suggestions
    
    def _update_error_stats(self, category: str):
        """Update error statistics"""
        self.error_stats[category] = self.error_stats.get(category, 0) + 1
    
    def _log_error(self, error: Exception, response: ErrorResponse, context: ErrorContext):
        """Log error with appropriate level"""
        log_data = {
            'error_code': response.error_code,
            'operation': context.operation,
            'service': context.service,
            'user_id': context.user_id,
            'request_id': context.request_id,
            'category': response.category.value,
            'severity': response.severity.value
        }
        
        if response.severity == ErrorSeverity.CRITICAL:
            logger.error(f"Critical error: {response.error_message}", extra=log_data)
            logger.error(f"Stack trace: {traceback.format_exc()}")
        elif response.severity == ErrorSeverity.RECOVERABLE:
            logger.warning(f"Recoverable error: {response.error_message}", extra=log_data)
        elif response.severity == ErrorSeverity.WARNING:
            logger.warning(f"Warning: {response.error_message}", extra=log_data)
        else:
            logger.info(f"Info: {response.error_message}", extra=log_data)
    
    def register_fallback_strategy(self, operation: str, strategy: FallbackStrategy):
        """Register a fallback strategy for an operation"""
        if operation not in self.fallback_strategies:
            self.fallback_strategies[operation] = []
        
        self.fallback_strategies[operation].append(strategy)
        # Sort by priority (higher priority first)
        self.fallback_strategies[operation].sort(key=lambda x: x.priority, reverse=True)
    
    def get_fallback_strategy(self, operation: str, error: Exception, context: ErrorContext) -> Optional[FallbackStrategy]:
        """Get the best fallback strategy for an operation"""
        if operation not in self.fallback_strategies:
            return None
        
        for strategy in self.fallback_strategies[operation]:
            if strategy.can_handle(error, context):
                return strategy
        
        return None
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error should be retried"""
        if attempt >= self.retry_config.max_attempts:
            return False
        
        error_str = str(error).lower()
        
        for retryable_error in self.retry_config.retryable_errors:
            if retryable_error in error_str:
                return True
        
        return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = sum(self.error_stats.values())
        return {
            'total_errors': total_errors,
            'by_category': self.error_stats.copy(),
            'error_rate_by_category': {
                category: (count / total_errors * 100) if total_errors > 0 else 0
                for category, count in self.error_stats.items()
            }
        }

class FallbackManager:
    """Manages fallback strategies for failed operations"""
    
    def __init__(self, error_handler: ProcessingErrorHandler):
        self.error_handler = error_handler
        self.fallback_usage_stats: Dict[str, int] = {}
    
    def execute_with_fallback(self, 
                            primary_func: Callable, 
                            fallback_func: Callable,
                            operation: str,
                            context: ErrorContext,
                            *args, **kwargs) -> Any:
        """Execute function with fallback on failure"""
        try:
            # Try primary function
            return primary_func(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"Primary function failed for {operation}: {e}")
            
            # Handle error and get fallback strategy
            error_response = self.error_handler.handle_error(e, context)
            
            try:
                # Execute fallback
                result = fallback_func(*args, **kwargs)
                
                # Update statistics
                self._update_fallback_stats(operation)
                
                logger.info(f"Fallback successful for {operation}")
                return result
                
            except Exception as fallback_error:
                logger.error(f"Fallback also failed for {operation}: {fallback_error}")
                
                # Handle fallback error
                fallback_error_response = self.error_handler.handle_error(fallback_error, context)
                raise fallback_error
    
    def register_fallback(self, operation: str, fallback_func: Callable, priority: int = 0):
        """Register a fallback function for an operation"""
        strategy = FallbackStrategy(f"{operation}_fallback", priority)
        strategy.execute = fallback_func
        self.error_handler.register_fallback_strategy(operation, strategy)
    
    def _update_fallback_stats(self, operation: str):
        """Update fallback usage statistics"""
        self.fallback_usage_stats[operation] = self.fallback_usage_stats.get(operation, 0) + 1
    
    def get_fallback_stats(self) -> Dict[str, int]:
        """Get fallback usage statistics"""
        return self.fallback_usage_stats.copy()

class RetryManager:
    """Implements exponential backoff retry logic"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.retry_stats: Dict[str, Dict[str, int]] = {}
    
    def execute_with_retry(self, 
                          func: Callable,
                          operation: str,
                          error_handler: ProcessingErrorHandler,
                          context: ErrorContext,
                          *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)
                
                # Update success statistics
                self._update_retry_stats(operation, 'success', attempt + 1)
                
                if attempt > 0:
                    logger.info(f"Operation {operation} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_error = e
                
                if not error_handler.should_retry(e, attempt + 1):
                    logger.error(f"Non-retryable error for {operation}: {e}")
                    break
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {operation}, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts exhausted for {operation}")
        
        # Update failure statistics
        self._update_retry_stats(operation, 'failure', self.config.max_attempts)
        
        # Handle the final error
        error_response = error_handler.handle_error(last_error, context)
        error_response.retry_attempted = True
        
        raise last_error
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)
    
    def _update_retry_stats(self, operation: str, result: str, attempts: int):
        """Update retry statistics"""
        if operation not in self.retry_stats:
            self.retry_stats[operation] = {'success': 0, 'failure': 0, 'total_attempts': 0}
        
        self.retry_stats[operation][result] += 1
        self.retry_stats[operation]['total_attempts'] += attempts
    
    def get_retry_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get retry statistics"""
        stats = {}
        for operation, data in self.retry_stats.items():
            total_operations = data['success'] + data['failure']
            stats[operation] = {
                'success_rate': (data['success'] / total_operations * 100) if total_operations > 0 else 0,
                'average_attempts': (data['total_attempts'] / total_operations) if total_operations > 0 else 0,
                'total_operations': total_operations,
                **data
            }
        return stats

# Global instances
error_handler = ProcessingErrorHandler()
fallback_manager = FallbackManager(error_handler)
retry_manager = RetryManager()