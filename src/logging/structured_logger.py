"""Structured Logging System.

This module provides structured logging capabilities with JSON output,
field validation, and integration with the comprehensive logging system.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback
import uuid


class StructuredLogLevel(Enum):
    """Structured log levels with numeric values."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60
    AUDIT = 70


@dataclass
class StructuredLogEntry:
    """Structured log entry with standardized fields."""
    
    # Core fields
    timestamp: str
    level: str
    message: str
    logger_name: str
    
    # Context fields
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Application fields
    component: Optional[str] = None
    operation: Optional[str] = None
    duration: Optional[float] = None
    
    # Error fields
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    error_id: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Performance fields
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    response_time: Optional[float] = None
    
    # Security fields
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    security_event: Optional[str] = None
    
    # Custom fields
    extra: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    hostname: Optional[str] = None
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        """Initialize structured formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
        
        # Fields to exclude from extra
        self.exclude_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'lineno', 'funcName', 'created',
            'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'getMessage', 'exc_info',
            'exc_text', 'stack_info', 'message'
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Create structured log entry
        entry = StructuredLogEntry(
            timestamp=datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            process_id=record.process,
            thread_id=record.thread
        )
        
        # Add hostname if available
        import socket
        try:
            entry.hostname = socket.gethostname()
        except Exception:
            pass
        
        # Extract structured fields from record
        if hasattr(record, 'correlation_id'):
            entry.correlation_id = record.correlation_id
        if hasattr(record, 'user_id'):
            entry.user_id = record.user_id
        if hasattr(record, 'session_id'):
            entry.session_id = record.session_id
        if hasattr(record, 'request_id'):
            entry.request_id = record.request_id
        if hasattr(record, 'component'):
            entry.component = record.component
        if hasattr(record, 'operation'):
            entry.operation = record.operation
        if hasattr(record, 'duration'):
            entry.duration = record.duration
        if hasattr(record, 'error_type'):
            entry.error_type = record.error_type
        if hasattr(record, 'error_code'):
            entry.error_code = record.error_code
        if hasattr(record, 'error_id'):
            entry.error_id = record.error_id
        if hasattr(record, 'memory_usage'):
            entry.memory_usage = record.memory_usage
        if hasattr(record, 'cpu_usage'):
            entry.cpu_usage = record.cpu_usage
        if hasattr(record, 'response_time'):
            entry.response_time = record.response_time
        if hasattr(record, 'ip_address'):
            entry.ip_address = record.ip_address
        if hasattr(record, 'user_agent'):
            entry.user_agent = record.user_agent
        if hasattr(record, 'security_event'):
            entry.security_event = record.security_event
        
        # Handle exception info
        if record.exc_info:
            entry.error_type = record.exc_info[0].__name__ if record.exc_info[0] else None
            entry.stack_trace = self.formatException(record.exc_info)
        
        # Add extra fields
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in self.exclude_fields and not key.startswith('_'):
                    entry.extra[key] = value
        
        return entry.to_json()


class StructuredLogger:
    """Structured logger with JSON output and field validation."""
    
    def __init__(
        self,
        name: str,
        level: Union[str, int, StructuredLogLevel] = StructuredLogLevel.INFO,
        output_file: Optional[Union[str, Path]] = None,
        console_output: bool = True,
        validate_fields: bool = True
    ):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level
            output_file: Optional file for JSON output
            console_output: Whether to output to console
            validate_fields: Whether to validate log fields
        """
        self.name = name
        self.validate_fields = validate_fields
        
        # Create underlying logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self._get_level_value(level))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create structured formatter
        self.formatter = StructuredFormatter()
        
        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler
        if output_file:
            file_handler = logging.FileHandler(output_file, encoding='utf-8')
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)
        
        # Context storage
        self.context: Dict[str, Any] = {}
    
    def _get_level_value(self, level: Union[str, int, StructuredLogLevel]) -> int:
        """Get numeric level value."""
        if isinstance(level, StructuredLogLevel):
            return level.value
        elif isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        else:
            return level
    
    def set_context(self, **kwargs):
        """Set persistent context for all log entries.
        
        Args:
            **kwargs: Context fields to set
        """
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context."""
        self.context.clear()
    
    def _validate_fields(self, fields: Dict[str, Any]):
        """Validate log fields.
        
        Args:
            fields: Fields to validate
        
        Raises:
            ValueError: If validation fails
        """
        if not self.validate_fields:
            return
        
        # Validate correlation_id format
        if 'correlation_id' in fields and fields['correlation_id']:
            if not isinstance(fields['correlation_id'], str):
                raise ValueError("correlation_id must be a string")
        
        # Validate duration is positive
        if 'duration' in fields and fields['duration'] is not None:
            if not isinstance(fields['duration'], (int, float)) or fields['duration'] < 0:
                raise ValueError("duration must be a positive number")
        
        # Validate response_time is positive
        if 'response_time' in fields and fields['response_time'] is not None:
            if not isinstance(fields['response_time'], (int, float)) or fields['response_time'] < 0:
                raise ValueError("response_time must be a positive number")
        
        # Validate memory_usage is positive
        if 'memory_usage' in fields and fields['memory_usage'] is not None:
            if not isinstance(fields['memory_usage'], (int, float)) or fields['memory_usage'] < 0:
                raise ValueError("memory_usage must be a positive number")
    
    def _prepare_extra(self, **kwargs) -> Dict[str, Any]:
        """Prepare extra fields for logging.
        
        Args:
            **kwargs: Additional fields
        
        Returns:
            Combined context and additional fields
        """
        extra = self.context.copy()
        extra.update(kwargs)
        
        # Validate fields
        self._validate_fields(extra)
        
        return extra
    
    def trace(self, message: str, **kwargs):
        """Log trace message.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.log(StructuredLogLevel.TRACE.value, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info message.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message.
        
        Args:
            message: Log message
            exc_info: Whether to include exception info
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message.
        
        Args:
            message: Log message
            exc_info: Whether to include exception info
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.critical(message, exc_info=exc_info, extra=extra)
    
    def security(self, message: str, **kwargs):
        """Log security event.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        extra['security_event'] = kwargs.get('security_event', 'general')
        self.logger.log(StructuredLogLevel.SECURITY.value, message, extra=extra)
    
    def audit(self, message: str, **kwargs):
        """Log audit event.
        
        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(**kwargs)
        self.logger.log(StructuredLogLevel.AUDIT.value, message, extra=extra)
    
    def log_operation(
        self,
        operation: str,
        message: str,
        duration: Optional[float] = None,
        success: bool = True,
        **kwargs
    ):
        """Log operation with standardized fields.
        
        Args:
            operation: Operation name
            message: Log message
            duration: Operation duration in seconds
            success: Whether operation was successful
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(
            operation=operation,
            duration=duration,
            success=success,
            **kwargs
        )
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, message, extra=extra)
    
    def log_performance(
        self,
        message: str,
        response_time: float,
        memory_usage: Optional[float] = None,
        cpu_usage: Optional[float] = None,
        **kwargs
    ):
        """Log performance metrics.
        
        Args:
            message: Log message
            response_time: Response time in seconds
            memory_usage: Memory usage in MB
            cpu_usage: CPU usage percentage
            **kwargs: Additional structured fields
        """
        extra = self._prepare_extra(
            response_time=response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            **kwargs
        )
        
        self.logger.info(message, extra=extra)
    
    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ):
        """Log HTTP request.
        
        Args:
            method: HTTP method
            url: Request URL
            status_code: HTTP status code
            response_time: Response time in seconds
            user_id: User ID
            ip_address: Client IP address
            user_agent: User agent string
            **kwargs: Additional structured fields
        """
        # Use operation from kwargs if provided, otherwise default to 'http_request'
        operation = kwargs.pop('operation', 'http_request')
        extra = self._prepare_extra(
            operation=operation,
            http_method=method,
            url=url,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs
        )
        
        # Determine log level based on status code
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        
        message = f"{method} {url} {status_code} ({response_time:.3f}s)"
        self.logger.log(level, message, extra=extra)
    
    def log_exception(
        self,
        exception: Exception,
        message: Optional[str] = None,
        error_id: Optional[str] = None,
        **kwargs
    ):
        """Log exception with structured fields.
        
        Args:
            exception: Exception to log
            message: Optional custom message
            error_id: Optional error ID for tracking
            **kwargs: Additional structured fields
        """
        if message is None:
            message = f"Exception occurred: {str(exception)}"
        
        if error_id is None:
            error_id = str(uuid.uuid4())
        
        extra = self._prepare_extra(
            error_type=exception.__class__.__name__,
            error_id=error_id,
            **kwargs
        )
        
        self.logger.error(message, exc_info=True, extra=extra)
        return error_id


class StructuredLoggerManager:
    """Manager for structured loggers."""
    
    def __init__(self):
        """Initialize logger manager."""
        self.loggers: Dict[str, StructuredLogger] = {}
        self.default_config = {
            'level': StructuredLogLevel.INFO,
            'console_output': True,
            'validate_fields': True
        }
    
    def get_logger(
        self,
        name: str,
        **config_overrides
    ) -> StructuredLogger:
        """Get or create structured logger.
        
        Args:
            name: Logger name
            **config_overrides: Configuration overrides
        
        Returns:
            StructuredLogger instance
        """
        if name not in self.loggers:
            config = self.default_config.copy()
            config.update(config_overrides)
            
            self.loggers[name] = StructuredLogger(name, **config)
        
        return self.loggers[name]
    
    def configure_default(
        self,
        level: Union[str, int, StructuredLogLevel] = StructuredLogLevel.INFO,
        output_dir: Optional[Union[str, Path]] = None,
        console_output: bool = True,
        validate_fields: bool = True
    ):
        """Configure default settings for new loggers.
        
        Args:
            level: Default logging level
            output_dir: Directory for log files
            console_output: Whether to output to console
            validate_fields: Whether to validate fields
        """
        self.default_config.update({
            'level': level,
            'console_output': console_output,
            'validate_fields': validate_fields
        })
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            self.default_config['output_file'] = output_dir / 'structured.log'
    
    def set_global_context(self, **kwargs):
        """Set context for all managed loggers.
        
        Args:
            **kwargs: Context fields to set
        """
        for logger in self.loggers.values():
            logger.set_context(**kwargs)
    
    def clear_global_context(self):
        """Clear context for all managed loggers."""
        for logger in self.loggers.values():
            logger.clear_context()


# Global manager instance
_manager = StructuredLoggerManager()


def get_structured_logger(name: str, **config) -> StructuredLogger:
    """Get structured logger instance.
    
    Args:
        name: Logger name
        **config: Configuration overrides
    
    Returns:
        StructuredLogger instance
    """
    return _manager.get_logger(name, **config)


def configure_structured_logging(
    level: Union[str, int, StructuredLogLevel] = StructuredLogLevel.INFO,
    output_dir: Optional[Union[str, Path]] = None,
    console_output: bool = True,
    validate_fields: bool = True
):
    """Configure structured logging globally.
    
    Args:
        level: Default logging level
        output_dir: Directory for log files
        console_output: Whether to output to console
        validate_fields: Whether to validate fields
    """
    _manager.configure_default(
        level=level,
        output_dir=output_dir,
        console_output=console_output,
        validate_fields=validate_fields
    )


def set_global_context(**kwargs):
    """Set global context for all structured loggers.
    
    Args:
        **kwargs: Context fields to set
    """
    _manager.set_global_context(**kwargs)


def clear_global_context():
    """Clear global context for all structured loggers."""
    _manager.clear_global_context()