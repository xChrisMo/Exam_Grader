"""Comprehensive Logging System with Advanced Features.

This module provides a unified logging system that integrates with the
standardized error handling system and offers advanced features like
structured logging, performance monitoring, security logging, and audit trails.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from logging.handlers import RotatingFileHandler
from threading import Lock
from typing import Any, Dict, List, Optional, Union

try:
    from src.exceptions.error_tracker import ErrorTracker

    ENHANCED_ERROR_HANDLING_AVAILABLE = True
except ImportError:
    ENHANCED_ERROR_HANDLING_AVAILABLE = False
    ApplicationError = None
    ErrorTracker = None

class LogLevel(Enum):
    """Enhanced log levels with additional granularity."""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    AUDIT = 60
    SECURITY = 70

@dataclass
class LogContext:
    """Context information for log entries."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "operation": self.operation,
            "component": self.component,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            **self.additional_data,
        }

class ComprehensiveLogger:
    """Advanced logger with comprehensive features."""

    def __init__(
        self,
        name: str,
        log_level: Union[str, LogLevel] = LogLevel.INFO,
        log_dir: Optional[str] = None,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = False,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 10,
        enable_performance_tracking: bool = True,
        enable_security_logging: bool = True,
    ):
        """Initialize comprehensive logger.

        Args:
            name: Logger name
            log_level: Logging level
            log_dir: Directory for log files
            enable_console: Enable console logging
            enable_file: Enable file logging
            enable_json: Enable JSON structured logging
            max_file_size: Maximum file size before rotation
            backup_count: Number of backup files to keep
            enable_performance_tracking: Enable performance metrics
            enable_security_logging: Enable security event logging
        """
        self.name = name
        self.log_level = (
            log_level
            if isinstance(log_level, LogLevel)
            else LogLevel[log_level.upper()]
        )
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_performance_tracking = enable_performance_tracking
        self.enable_security_logging = enable_security_logging

        # Create logger instance
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level.value)

        # Performance tracking
        self.performance_metrics = {
            "start_time": datetime.now(timezone.utc),
            "log_counts": {level.name: 0 for level in LogLevel},
            "operations": {},
            "errors": [],
            "warnings": [],
        }
        self._metrics_lock = Lock()

        self.context_stack: List[LogContext] = []
        self._context_lock = Lock()

        # Setup handlers
        self._setup_handlers()

        # Integration with error tracking
        self.error_tracker = None
        if ENHANCED_ERROR_HANDLING_AVAILABLE:
            try:
                self.error_tracker = ErrorTracker()
            except Exception:
                pass  # Fallback gracefully

    def _setup_handlers(self):
        """Setup logging handlers."""
        # Clear existing handlers
        self.logger.handlers.clear()

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level.value)

            if self.enable_json:
                console_formatter = self._create_json_formatter()
            else:
                console_formatter = self._create_standard_formatter()

            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # File handlers
        if self.enable_file:
            # Main log file
            main_file_handler = RotatingFileHandler(
                self.log_dir / f"{self.name}.log",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            main_file_handler.setLevel(logging.DEBUG)
            main_file_handler.setFormatter(self._create_detailed_formatter())
            self.logger.addHandler(main_file_handler)

            # Error-only file
            error_file_handler = RotatingFileHandler(
                self.log_dir / f"{self.name}_errors.log",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            error_file_handler.setLevel(logging.ERROR)
            error_file_handler.setFormatter(self._create_detailed_formatter())
            self.logger.addHandler(error_file_handler)

            if self.enable_security_logging:
                security_file_handler = RotatingFileHandler(
                    self.log_dir / f"{self.name}_security.log",
                    maxBytes=self.max_file_size,
                    backupCount=self.backup_count,
                    encoding="utf-8",
                )
                security_file_handler.setLevel(LogLevel.SECURITY.value)
                security_file_handler.setFormatter(self._create_security_formatter())
                self.logger.addHandler(security_file_handler)

            if self.enable_json:
                json_file_handler = RotatingFileHandler(
                    self.log_dir / f"{self.name}_structured.jsonl",
                    maxBytes=self.max_file_size,
                    backupCount=self.backup_count,
                    encoding="utf-8",
                )
                json_file_handler.setLevel(logging.DEBUG)
                json_file_handler.setFormatter(self._create_json_formatter())
                self.logger.addHandler(json_file_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _create_standard_formatter(self) -> logging.Formatter:
        """Create standard log formatter."""
        return logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _create_detailed_formatter(self) -> logging.Formatter:
        """Create detailed log formatter."""
        return logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] %(funcName)s(): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _create_security_formatter(self) -> logging.Formatter:
        """Create security-focused log formatter."""
        return logging.Formatter(
            "%(asctime)s [SECURITY] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON log formatter."""

        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(
                        record.created, timezone.utc
                    ).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                    "thread": record.thread,
                    "process": record.process,
                }

                if record.exc_info:
                    log_entry["exception"] = {
                        "type": record.exc_info[0].__name__,
                        "message": str(record.exc_info[1]),
                        "traceback": traceback.format_exception(*record.exc_info),
                    }

                if hasattr(record, "context"):
                    log_entry["context"] = record.context

                return json.dumps(log_entry, default=str)

        return JSONFormatter()

    def _update_metrics(self, level: LogLevel, operation: Optional[str] = None):
        """Update performance metrics."""
        if not self.enable_performance_tracking:
            return

        with self._metrics_lock:
            self.performance_metrics["log_counts"][level.name] += 1

            if operation:
                if operation not in self.performance_metrics["operations"]:
                    self.performance_metrics["operations"][operation] = {
                        "count": 0,
                        "first_seen": datetime.now(timezone.utc),
                        "last_seen": datetime.now(timezone.utc),
                    }

                self.performance_metrics["operations"][operation]["count"] += 1
                self.performance_metrics["operations"][operation]["last_seen"] = (
                    datetime.now(timezone.utc)
                )

    def _get_current_context(self) -> Dict[str, Any]:
        """Get current logging context."""
        with self._context_lock:
            if self.context_stack:
                return self.context_stack[-1].to_dict()
            return {}

    def push_context(self, context: LogContext):
        """Push a new context onto the stack."""
        with self._context_lock:
            self.context_stack.append(context)

    def pop_context(self) -> Optional[LogContext]:
        """Pop the current context from the stack."""
        with self._context_lock:
            if self.context_stack:
                return self.context_stack.pop()
            return None

    def log(
        self,
        level: Union[LogLevel, str],
        message: str,
        context: Optional[LogContext] = None,
        **kwargs,
    ):
        """Log a message with optional context."""
        if isinstance(level, str):
            level = LogLevel[level.upper()]

        # Update metrics
        operation = context.operation if context else kwargs.get("operation")
        self._update_metrics(level, operation)

        # Prepare log record
        extra = kwargs.copy()

        # Add context information
        if context:
            extra["context"] = context.to_dict()
        else:
            current_context = self._get_current_context()
            if current_context:
                extra["context"] = current_context

        # Log the message
        self.logger.log(level.value, message, extra=extra)

        # Track errors and warnings
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            with self._metrics_lock:
                self.performance_metrics["errors"].append(
                    {
                        "timestamp": datetime.now(timezone.utc),
                        "level": level.name,
                        "message": message,
                        "context": extra.get("context", {}),
                    }
                )
        elif level == LogLevel.WARNING:
            with self._metrics_lock:
                self.performance_metrics["warnings"].append(
                    {
                        "timestamp": datetime.now(timezone.utc),
                        "message": message,
                        "context": extra.get("context", {}),
                    }
                )

    # Convenience methods
    def trace(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log a trace message."""
        self.log(LogLevel.TRACE, message, context, **kwargs)

    def debug(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message, context, **kwargs)

    def info(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log an info message."""
        self.log(LogLevel.INFO, message, context, **kwargs)

    def warning(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log a warning message."""
        self.log(LogLevel.WARNING, message, context, **kwargs)

    def error(
        self,
        message: str,
        context: Optional[LogContext] = None,
        exception: Optional[Exception] = None,
        **kwargs,
    ):
        """Log an error message."""
        if exception:
            kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)

            # Integrate with error tracking
            if self.error_tracker and ENHANCED_ERROR_HANDLING_AVAILABLE:
                try:
                    context_dict = (
                        context.to_dict() if context else self._get_current_context()
                    )
                    self.error_tracker.track_error(
                        exception, additional_context=context_dict
                    )
                except Exception:
                    pass  # Don't let error tracking break logging

        self.log(LogLevel.ERROR, message, context, **kwargs)

    def critical(
        self,
        message: str,
        context: Optional[LogContext] = None,
        exception: Optional[Exception] = None,
        **kwargs,
    ):
        """Log a critical message."""
        if exception:
            kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)

            # Integrate with error tracking
            if self.error_tracker and ENHANCED_ERROR_HANDLING_AVAILABLE:
                try:
                    context_dict = (
                        context.to_dict() if context else self._get_current_context()
                    )
                    self.error_tracker.track_error(
                        exception, additional_context=context_dict
                    )
                except Exception:
                    pass  # Don't let error tracking break logging

        self.log(LogLevel.CRITICAL, message, context, **kwargs)

    def audit(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log an audit message."""
        self.log(LogLevel.AUDIT, message, context, **kwargs)

    def security(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Log a security message."""
        self.log(LogLevel.SECURITY, message, context, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        with self._metrics_lock:
            uptime = (
                datetime.now(timezone.utc) - self.performance_metrics["start_time"]
            ).total_seconds()

            return {
                "uptime_seconds": uptime,
                "log_counts": self.performance_metrics["log_counts"].copy(),
                "operations": self.performance_metrics["operations"].copy(),
                "error_count": len(self.performance_metrics["errors"]),
                "warning_count": len(self.performance_metrics["warnings"]),
                "recent_errors": self.performance_metrics["errors"][
                    -10:
                ],  # Last 10 errors
                "recent_warnings": self.performance_metrics["warnings"][
                    -10:
                ],  # Last 10 warnings
            }

class PerformanceLogger(ComprehensiveLogger):
    """Specialized logger for performance monitoring."""

    def __init__(self, name: str = "performance", **kwargs):
        super().__init__(name, **kwargs)
        self.operation_timings = {}
        self._timing_lock = Lock()

    def start_operation(
        self, operation_name: str, context: Optional[LogContext] = None
    ) -> str:
        """Start timing an operation."""
        operation_id = f"{operation_name}_{int(time.time() * 1000000)}"

        with self._timing_lock:
            self.operation_timings[operation_id] = {
                "name": operation_name,
                "start_time": time.time(),
                "context": context.to_dict() if context else {},
            }

        self.debug(
            f"Started operation: {operation_name}", context, operation_id=operation_id
        )
        return operation_id

    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        result_info: Optional[Dict] = None,
    ):
        """End timing an operation."""
        end_time = time.time()

        with self._timing_lock:
            if operation_id in self.operation_timings:
                operation = self.operation_timings.pop(operation_id)
                duration = end_time - operation["start_time"]

                context = (
                    LogContext(**operation["context"]) if operation["context"] else None
                )

                log_message = (
                    f"Completed operation: {operation['name']} in {duration:.3f}s"
                )
                if result_info:
                    log_message += f" - {result_info}"

                if success:
                    self.info(
                        log_message,
                        context,
                        operation_id=operation_id,
                        duration=duration,
                        success=success,
                    )
                else:
                    self.warning(
                        log_message,
                        context,
                        operation_id=operation_id,
                        duration=duration,
                        success=success,
                    )

                return duration

        self.warning(f"Unknown operation ID: {operation_id}")
        return None

class SecurityLogger(ComprehensiveLogger):
    """Specialized logger for security events."""

    def __init__(self, name: str = "security", **kwargs):
        kwargs["enable_security_logging"] = True
        super().__init__(name, **kwargs)

    def log_authentication_attempt(
        self, user_id: str, success: bool, ip_address: str, user_agent: str = None
    ):
        """Log authentication attempt."""
        context = LogContext(
            user_id=user_id,
            additional_data={
                "ip_address": ip_address,
                "user_agent": user_agent,
                "event_type": "authentication",
            },
        )

        if success:
            self.security(f"Successful authentication for user: {user_id}", context)
        else:
            self.security(f"Failed authentication attempt for user: {user_id}", context)

    def log_authorization_failure(
        self, user_id: str, resource: str, action: str, ip_address: str
    ):
        """Log authorization failure."""
        context = LogContext(
            user_id=user_id,
            additional_data={
                "resource": resource,
                "action": action,
                "ip_address": ip_address,
                "event_type": "authorization_failure",
            },
        )

        self.security(
            f"Authorization failure: User {user_id} attempted {action} on {resource}",
            context,
        )

    def log_suspicious_activity(
        self, description: str, user_id: str = None, ip_address: str = None, **kwargs
    ):
        """Log suspicious activity."""
        context = LogContext(
            user_id=user_id,
            additional_data={
                "ip_address": ip_address,
                "event_type": "suspicious_activity",
                **kwargs,
            },
        )

        self.security(f"Suspicious activity detected: {description}", context)

class AuditLogger(ComprehensiveLogger):
    """Specialized logger for audit trails."""

    def __init__(self, name: str = "audit", **kwargs):
        super().__init__(name, **kwargs)

    def log_data_access(
        self, user_id: str, resource_type: str, resource_id: str, action: str
    ):
        """Log data access event."""
        context = LogContext(
            user_id=user_id,
            additional_data={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "event_type": "data_access",
            },
        )

        self.audit(
            f"Data access: {action} on {resource_type}:{resource_id} by user {user_id}",
            context,
        )

    def log_data_modification(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        changes: Dict[str, Any],
        old_values: Dict[str, Any] = None,
    ):
        """Log data modification event."""
        context = LogContext(
            user_id=user_id,
            additional_data={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "changes": changes,
                "old_values": old_values,
                "event_type": "data_modification",
            },
        )

        self.audit(
            f"Data modified: {resource_type}:{resource_id} by user {user_id}", context
        )

    def log_system_event(
        self, event_type: str, description: str, user_id: str = None, **kwargs
    ):
        """Log system event."""
        context = LogContext(
            user_id=user_id, additional_data={"event_type": event_type, **kwargs}
        )

        self.audit(f"System event: {event_type} - {description}", context)

# Global logger registry
_logger_registry: Dict[str, ComprehensiveLogger] = {}
_registry_lock = Lock()

def get_logger(
    name: str, logger_type: str = "comprehensive", **kwargs
) -> ComprehensiveLogger:
    """Get or create a logger instance.

    Args:
        name: Logger name
        logger_type: Type of logger ('comprehensive', 'performance', 'security', 'audit')
        **kwargs: Additional arguments for logger initialization

    Returns:
        Logger instance
    """
    with _registry_lock:
        if name not in _logger_registry:
            if logger_type == "performance":
                _logger_registry[name] = PerformanceLogger(name, **kwargs)
            elif logger_type == "security":
                _logger_registry[name] = SecurityLogger(name, **kwargs)
            elif logger_type == "audit":
                _logger_registry[name] = AuditLogger(name, **kwargs)
            else:
                _logger_registry[name] = ComprehensiveLogger(name, **kwargs)

        return _logger_registry[name]

def setup_logging(
    log_level: Union[str, LogLevel] = LogLevel.INFO,
    log_dir: str = "logs",
    enable_json: bool = False,
    enable_performance_tracking: bool = True,
    enable_security_logging: bool = True,
    quiet_third_party: bool = True,
) -> ComprehensiveLogger:
    """Setup application-wide logging.

    Args:
        log_level: Default log level
        log_dir: Directory for log files
        enable_json: Enable JSON structured logging
        enable_performance_tracking: Enable performance metrics
        enable_security_logging: Enable security event logging
        quiet_third_party: Reduce third-party library log verbosity

    Returns:
        Main application logger
    """
    # Setup main application logger
    main_logger = get_logger(
        "exam_grader",
        log_level=log_level,
        log_dir=log_dir,
        enable_json=enable_json,
        enable_performance_tracking=enable_performance_tracking,
        enable_security_logging=enable_security_logging,
    )

    # Setup specialized loggers
    get_logger("performance", "performance", log_level=log_level, log_dir=log_dir)
    get_logger("security", "security", log_level=log_level, log_dir=log_dir)
    get_logger("audit", "audit", log_level=log_level, log_dir=log_dir)

    # Configure third-party loggers
    if quiet_third_party:
        third_party_loggers = [
            "sqlalchemy.engine",
            "sqlalchemy.dialects",
            "sqlalchemy.pool",
            "sqlalchemy.orm",
            "werkzeug",
            "urllib3",
            "requests",
            "PIL",
            "matplotlib",
            "celery",
        ]

        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    main_logger.info("Comprehensive logging system initialized")
    return main_logger
