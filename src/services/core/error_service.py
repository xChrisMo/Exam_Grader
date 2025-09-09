"""
Consolidated Error Service

This service consolidates all error handling functionality from:
- error_handling_service.py
- enhanced_error_handler.py
- error_tracking_service.py
- processing_error_handler.py
- enhanced_processing_error_system.py
- error_reporter.py
"""

import time
from datetime import datetime, timezone
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger

class ErrorSeverity(Enum):
    """Error severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ErrorCategory(Enum):
    """Error categories for classification"""

    NETWORK = "network"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"
    RESOURCE = "resource"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
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
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    fallback_used: bool = False
    retry_attempted: bool = False
    context: Optional[ErrorContext] = None
    suggestions: List[str] = None
    recoverable: bool = True

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

class ProcessingError(Exception):
    """Custom exception for processing operations"""

    def __init__(
        self,
        message: str,
        error_type: ErrorCategory = ErrorCategory.PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now(timezone.utc)
        self.error_id = f"{error_type.value}_{int(time.time())}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "error_id": self.error_id,
            "message": str(self),
            "type": self.error_type.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

class ErrorService(BaseService):
    """Consolidated error handling service"""

    def __init__(self):
        super().__init__("error_service")
        self.error_history: List[Dict[str, Any]] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.error_stats: Dict[str, int] = {}
        self.max_error_history = 10000

        # Setup default recovery strategies
        self._setup_recovery_strategies()

    async def initialize(self) -> bool:
        """Initialize the error service"""
        try:
            self.status = ServiceStatus.HEALTHY
            logger.info("Error service initialized successfully")
            return True
        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize error service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            return len(self.error_history) < self.max_error_history
        except Exception as e:
            logger.error(f"Error service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.error_history.clear()
            self.error_stats.clear()
            logger.info("Error service cleanup completed")
        except Exception as e:
            logger.error(f"Error during error service cleanup: {str(e)}")

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
                context=context,
                suggestions=self._get_error_suggestions(error, category),
            )

            # Update error statistics
            self._update_error_stats(category.value)

            # Log the error
            self._log_error(error, response, context)

            # Store in history
            self._store_error_history(error, response, context)

            return response

        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return ErrorResponse(
                error_code="HANDLER_ERROR",
                error_message="Error handling failed",
                severity=ErrorSeverity.CRITICAL,
            )

    def handle_file_processing_error(
        self, error: Exception, file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle file processing errors with fallback options"""
        try:
            # Categorize the error
            if "encoding" in str(error).lower():
                error_type = ErrorCategory.PROCESSING
                recovery_suggestions = [
                    "Try different character encoding (UTF-8, Latin-1, CP1252)",
                    "Check if file is corrupted or incomplete",
                    "Use alternative text extraction method",
                ]
            elif "permission" in str(error).lower():
                error_type = ErrorCategory.PERMISSION
                recovery_suggestions = [
                    "Check file permissions",
                    "Ensure file is not locked by another process",
                    "Try copying file to temporary location",
                ]
            elif "not found" in str(error).lower():
                error_type = ErrorCategory.PROCESSING
                recovery_suggestions = [
                    "Verify file path is correct",
                    "Check if file was moved or deleted",
                    "Re-upload the file",
                ]
            else:
                error_type = ErrorCategory.PROCESSING
                recovery_suggestions = [
                    "Try alternative file processing method",
                    "Check file format compatibility",
                    "Contact support if issue persists",
                ]

            # Create structured error response
            error_response = {
                "success": False,
                "error_type": error_type.value,
                "error_message": str(error),
                "file_info": {
                    "name": file_info.get("name", "unknown"),
                    "size": file_info.get("size", 0),
                    "type": file_info.get("type", "unknown"),
                },
                "recovery_suggestions": recovery_suggestions,
                "retry_possible": True,
                "fallback_available": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.error(
                f"File processing error for {file_info.get('name', 'unknown')}: {error}"
            )
            return error_response

        except Exception as e:
            logger.error(f"Error in file processing error handler: {e}")
            return {
                "success": False,
                "error_type": ErrorCategory.UNKNOWN.value,
                "error_message": "Unknown error occurred during file processing",
                "recovery_suggestions": ["Contact support"],
                "retry_possible": False,
                "fallback_available": False,
            }

    def handle_api_error(
        self, error: Exception, service_type: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle external API errors with retry logic"""
        context = context or {}

        try:
            error_str = str(error).lower()

            if "rate limit" in error_str or "429" in error_str:
                error_type = ErrorCategory.NETWORK
                recovery_suggestions = [
                    "Wait before retrying the request",
                    "Implement exponential backoff",
                    "Check API rate limits",
                ]
                auto_recovery = {
                    "retry_with_backoff": True,
                    "max_retries": 3,
                    "base_delay": 60,
                }
            elif "connection" in error_str or "timeout" in error_str:
                error_type = ErrorCategory.NETWORK
                recovery_suggestions = [
                    "Check internet connection",
                    "Verify API endpoint is accessible",
                    "Try again in a few moments",
                ]
                auto_recovery = {
                    "retry_with_backoff": True,
                    "max_retries": 5,
                    "base_delay": 2,
                }
            elif "unauthorized" in error_str or "401" in error_str:
                error_type = ErrorCategory.AUTHENTICATION
                recovery_suggestions = [
                    "Check API key is valid",
                    "Verify API key has required permissions",
                    "Regenerate API key if necessary",
                ]
                auto_recovery = {"retry_possible": False}
            else:
                error_type = ErrorCategory.NETWORK
                recovery_suggestions = [
                    f"Check {service_type} service status",
                    "Review API documentation",
                    "Contact service provider if issue persists",
                ]
                auto_recovery = {"retry_with_backoff": True, "max_retries": 2}

            error_response = {
                "success": False,
                "error_type": error_type.value,
                "error_message": str(error),
                "service_type": service_type,
                "context": context,
                "recovery_suggestions": recovery_suggestions,
                "auto_recovery_options": auto_recovery,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.error(f"{service_type} API error: {error}")
            return error_response

        except Exception as e:
            logger.error(f"Error in API error handler: {e}")
            return {
                "success": False,
                "error_type": ErrorCategory.UNKNOWN.value,
                "error_message": f"Unknown {service_type} API error occurred",
                "recovery_suggestions": ["Contact support"],
            }

    def _categorize_severity(self, error: Exception) -> ErrorSeverity:
        """Categorize error severity"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Critical errors that require immediate attention
        critical_indicators = [
            "database",
            "connection pool",
            "out of memory",
            "disk full",
            "permission denied",
            "authentication failed",
            "security",
        ]

        # High severity errors
        high_indicators = [
            "timeout",
            "connection",
            "network",
            "service unavailable",
            "rate limit",
            "server error",
        ]

        # Medium severity errors
        medium_indicators = ["validation", "invalid", "format", "parse", "decode"]

        # Low severity errors
        low_indicators = ["deprecated", "fallback", "degraded", "missing optional"]

        for indicator in critical_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.CRITICAL

        for indicator in high_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.HIGH

        for indicator in medium_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.MEDIUM

        for indicator in low_indicators:
            if indicator in error_str or indicator in error_type:
                return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error by type"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        category_mapping = {
            ErrorCategory.NETWORK: [
                "connection",
                "timeout",
                "network",
                "dns",
                "socket",
                "http",
            ],
            ErrorCategory.DEPENDENCY: [
                "import",
                "module",
                "package",
                "library",
                "dependency",
            ],
            ErrorCategory.VALIDATION: [
                "validation",
                "invalid",
                "format",
                "parse",
                "decode",
            ],
            ErrorCategory.RESOURCE: ["memory", "disk", "file", "resource", "limit"],
            ErrorCategory.PROCESSING: [
                "processing",
                "calculation",
                "algorithm",
                "logic",
            ],
            ErrorCategory.CONFIGURATION: [
                "config",
                "setting",
                "parameter",
                "environment",
            ],
            ErrorCategory.DATABASE: [
                "database",
                "sql",
                "query",
                "transaction",
                "connection",
            ],
            ErrorCategory.AUTHENTICATION: [
                "auth",
                "login",
                "token",
                "credential",
                "unauthorized",
            ],
            ErrorCategory.PERMISSION: ["permission", "access", "forbidden", "denied"],
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

    def _get_error_suggestions(
        self, error: Exception, category: ErrorCategory
    ) -> List[str]:
        """Get suggestions for resolving the error"""
        suggestions = []
        error_str = str(error).lower()

        if category == ErrorCategory.DEPENDENCY:
            if "import" in error_str or "module" in error_str:
                suggestions.extend(
                    [
                        "Install missing Python package using pip",
                        "Check if the package name is correct",
                        "Verify virtual environment is activated",
                    ]
                )
        elif category == ErrorCategory.NETWORK:
            suggestions.extend(
                [
                    "Check internet connection",
                    "Verify API endpoints are accessible",
                    "Check firewall and proxy settings",
                ]
            )
        elif category == ErrorCategory.RESOURCE:
            suggestions.extend(
                [
                    "Check available disk space",
                    "Monitor memory usage",
                    "Clear temporary files",
                ]
            )
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.extend(
                [
                    "Verify configuration file exists",
                    "Check environment variables",
                    "Validate configuration syntax",
                ]
            )
        elif category == ErrorCategory.DATABASE:
            suggestions.extend(
                [
                    "Check database connection",
                    "Verify database credentials",
                    "Check database server status",
                ]
            )

        # Add general suggestions
        suggestions.extend(
            [
                "Check application logs for more details",
                "Retry the operation if it's transient",
            ]
        )

        return suggestions

    def _setup_recovery_strategies(self):
        """Setup default recovery strategies"""
        # This would be expanded with actual recovery strategy implementations
        self.recovery_strategies = {
            ErrorCategory.NETWORK: [],
            ErrorCategory.PROCESSING: [],
            ErrorCategory.RESOURCE: [],
            ErrorCategory.DATABASE: [],
        }

    def _update_error_stats(self, category: str):
        """Update error statistics"""
        self.error_stats[category] = self.error_stats.get(category, 0) + 1

    def _log_error(
        self, error: Exception, response: ErrorResponse, context: ErrorContext
    ):
        """Log error with appropriate level"""
        log_data = {
            "error_code": response.error_code,
            "operation": context.operation,
            "service": context.service,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "category": response.category.value,
            "severity": response.severity.value,
        }

        if response.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {response.error_message}", extra=log_data)
            logger.critical(f"Stack trace: {traceback.format_exc()}")
        elif response.severity == ErrorSeverity.HIGH:
            logger.error(
                f"High severity error: {response.error_message}", extra=log_data
            )
        elif response.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                f"Medium severity error: {response.error_message}", extra=log_data
            )
        else:
            logger.info(f"Low severity error: {response.error_message}", extra=log_data)

    def _store_error_history(
        self, error: Exception, response: ErrorResponse, context: ErrorContext
    ):
        """Store error in history"""
        error_entry = {
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "category": response.category.value,
                "severity": response.severity.value,
            },
            "context": {
                "operation": context.operation,
                "service": context.service,
                "user_id": context.user_id,
                "request_id": context.request_id,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.error_history.append(error_entry)

        # Maintain history size limit
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history :]

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {"total_errors": 0}

        total_errors = len(self.error_history)

        return {
            "total_errors": total_errors,
            "error_types": self.error_stats.copy(),
            "error_rate_by_category": {
                category: (count / total_errors * 100) if total_errors > 0 else 0
                for category, count in self.error_stats.items()
            },
            "recent_errors": self.error_history[-10:] if self.error_history else [],
        }

class RetryManager:
    """Retry manager for operations that can be retried"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    logger.warning(f"Retry attempt {attempt + 1} after {delay}s delay: {str(e)}")
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")

        raise last_error

# Global instances
error_service = ErrorService()
retry_manager = RetryManager()