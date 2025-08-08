"""
Enhanced Logging Service

This module provides comprehensive logging capabilities with structured logging,
log aggregation, performance metrics integration, and monitoring dashboards.
"""

import json
import logging
import logging.handlers
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.config.processing_config import ProcessingConfigManager
from utils.logger import logger


class LogLevel(Enum):
    """Enhanced log levels"""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogCategory(Enum):
    """Log categories for better organization"""

    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USER_ACTION = "user_action"
    API = "api"
    DATABASE = "database"
    FILE_PROCESSING = "file_processing"
    CACHE = "cache"
    ERROR = "error"
    AUDIT = "audit"


@dataclass
class StructuredLogEntry:
    """Structured log entry with metadata"""

    timestamp: datetime
    level: LogLevel
    category: LogCategory
    service: str
    operation: str
    message: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "category": self.category.value,
            "service": self.service,
            "operation": self.operation,
            "message": self.message,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "stack_trace": self.stack_trace,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class LogMetrics:
    """Metrics for log analysis"""

    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_service: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_rate: float = 0.0
    average_response_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class LogHandler:
    """Base class for log handlers"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    def handle(self, entry: StructuredLogEntry) -> bool:
        """Handle a log entry"""
        if not self.enabled:
            return False
        return self._process_entry(entry)

    def _process_entry(self, entry: StructuredLogEntry) -> bool:
        """Process the log entry - to be implemented by subclasses"""
        # Default implementation - just return True to indicate processing
        # Subclasses should override this method with specific processing logic
        return True


class FileLogHandler(LogHandler):
    """File-based log handler with rotation"""

    def __init__(
        self,
        name: str,
        log_file: str,
        max_size: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        format_json: bool = True,
    ):
        super().__init__(name)
        self.log_file = log_file
        self.max_size = max_size
        self.backup_count = backup_count
        self.format_json = format_json

        # Ensure log directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        # Setup rotating file handler
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count
        )

        # Setup formatter
        if format_json:
            formatter = logging.Formatter("%(message)s")
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            )
        self.file_handler.setFormatter(formatter)

    def _process_entry(self, entry: StructuredLogEntry) -> bool:
        """Write entry to file"""
        try:
            if self.format_json:
                message = entry.to_json()
            else:
                message = f"[{entry.category.value}] {entry.service}.{entry.operation}: {entry.message}"

            # Create a log record
            record = logging.LogRecord(
                name=entry.service,
                level=entry.level.value,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )

            self.file_handler.emit(record)
            return True

        except Exception as e:
            logger.error(f"Error in FileLogHandler: {e}")
            return False


class MetricsLogHandler(LogHandler):
    """Handler for collecting log metrics"""

    def __init__(self, name: str):
        super().__init__(name)
        self.metrics = LogMetrics()
        self._response_times: deque = deque(maxlen=1000)
        self._lock = threading.RLock()

    def _process_entry(self, entry: StructuredLogEntry) -> bool:
        """Update metrics based on log entry"""
        try:
            with self._lock:
                self.metrics.total_logs += 1
                self.metrics.logs_by_level[entry.level.name] += 1
                self.metrics.logs_by_category[entry.category.value] += 1
                self.metrics.logs_by_service[entry.service] += 1

                # Track response times
                if entry.duration_ms is not None:
                    self._response_times.append(entry.duration_ms)
                    if self._response_times:
                        self.metrics.average_response_time = sum(
                            self._response_times
                        ) / len(self._response_times)

                # Calculate error rate
                error_logs = self.metrics.logs_by_level.get(
                    "ERROR", 0
                ) + self.metrics.logs_by_level.get("CRITICAL", 0)
                self.metrics.error_rate = error_logs / max(1, self.metrics.total_logs)

                self.metrics.last_updated = datetime.now(timezone.utc)

            return True

        except Exception as e:
            logger.error(f"Error in MetricsLogHandler: {e}")
            return False

    def get_metrics(self) -> LogMetrics:
        """Get current metrics"""
        with self._lock:
            return self.metrics


class EnhancedLoggingService:
    """Main enhanced logging service"""

    def __init__(self, service_name: str = "enhanced_logging"):
        self.service_name = service_name
        self.handlers: Dict[str, LogHandler] = {}
        self.filters: List[Callable[[StructuredLogEntry], bool]] = []
        self._lock = threading.RLock()

        # Initialize processing configuration
        self._config_manager = ProcessingConfigManager()
        self._logging_config = self._config_manager.get_logging_config()

        # Setup handlers based on configuration
        self._setup_configured_handlers()

    def _setup_configured_handlers(self):
        """Setup log handlers from processing configuration."""
        try:
            destinations = self._logging_config.output_destinations

            # Setup file handlers based on configuration
            for dest_name, dest_config in destinations.items():
                if not dest_config.enabled:
                    continue

                if dest_config.path:  # File-based destination
                    handler = FileLogHandler(
                        name=f"{dest_name}_handler",
                        log_file=dest_config.path,
                        max_size=dest_config.max_size_mb * 1024 * 1024,
                        backup_count=dest_config.backup_count,
                        format_json=self._logging_config.structured_logging.get(
                            "enabled", True
                        ),
                    )
                    self.add_handler(handler)

            # Always add metrics handler
            self.add_handler(MetricsLogHandler("metrics"))

            logger.info("Log handlers configured from ProcessingConfigManager")

        except Exception as e:
            logger.error(f"Failed to setup configured log handlers: {e}")
            # Fallback to default handlers
            self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default log handlers"""
        self.add_handler(
            FileLogHandler("general_logs", "logs/application.log", format_json=True)
        )

        self.add_handler(
            FileLogHandler("error_logs", "logs/errors.log", format_json=True)
        )

        self.add_handler(
            FileLogHandler("performance_logs", "logs/performance.log", format_json=True)
        )

        # Metrics handler
        self.add_handler(MetricsLogHandler("metrics"))

    def add_handler(self, handler: LogHandler):
        """Add a log handler"""
        with self._lock:
            self.handlers[handler.name] = handler
            logger.info(f"Added log handler: {handler.name}")

    def remove_handler(self, name: str) -> bool:
        """Remove a log handler"""
        with self._lock:
            if name in self.handlers:
                del self.handlers[name]
                logger.info(f"Removed log handler: {name}")
                return True
            return False

    def add_filter(self, filter_func: Callable[[StructuredLogEntry], bool]):
        """Add a log filter function"""
        self.filters.append(filter_func)

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        service: str,
        operation: str,
        message: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
    ):
        """Log a structured entry"""

        entry = StructuredLogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            category=category,
            service=service,
            operation=operation,
            message=message,
            user_id=user_id,
            request_id=request_id,
            session_id=session_id,
            duration_ms=duration_ms,
            metadata=metadata or {},
            stack_trace=stack_trace,
        )

        # Apply filters
        for filter_func in self.filters:
            try:
                if not filter_func(entry):
                    return  # Entry filtered out
            except Exception as e:
                logger.error(f"Error in log filter: {e}")

        # Send to handlers
        with self._lock:
            for handler in self.handlers.values():
                try:
                    handler.handle(entry)
                except Exception as e:
                    logger.error(f"Error in log handler {handler.name}: {e}")

    def log_info(
        self,
        category: LogCategory,
        service: str,
        operation: str,
        message: str,
        **kwargs,
    ):
        """Log info level message"""
        self.log(LogLevel.INFO, category, service, operation, message, **kwargs)

    def log_warning(
        self,
        category: LogCategory,
        service: str,
        operation: str,
        message: str,
        **kwargs,
    ):
        """Log warning level message"""
        self.log(LogLevel.WARNING, category, service, operation, message, **kwargs)

    def log_error(
        self,
        category: LogCategory,
        service: str,
        operation: str,
        message: str,
        **kwargs,
    ):
        """Log error level message"""
        self.log(LogLevel.ERROR, category, service, operation, message, **kwargs)

    def log_performance(
        self,
        service: str,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **kwargs,
    ):
        """Log performance metrics"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Operation {operation} completed in {duration_ms:.2f}ms"

        self.log(
            level,
            LogCategory.PERFORMANCE,
            service,
            operation,
            message,
            duration_ms=duration_ms,
            **kwargs,
        )

    def get_metrics(self) -> Optional[LogMetrics]:
        """Get logging metrics"""
        metrics_handler = self.handlers.get("metrics")
        if isinstance(metrics_handler, MetricsLogHandler):
            return metrics_handler.get_metrics()
        return None

    def get_handler_stats(self) -> Dict[str, Any]:
        """Get statistics for all handlers"""
        stats = {}
        with self._lock:
            for name, handler in self.handlers.items():
                stats[name] = {
                    "name": name,
                    "type": type(handler).__name__,
                    "enabled": handler.enabled,
                }
        return stats


class OperationLogger:
    """Context manager for logging operations with timing"""

    def __init__(
        self,
        logging_service: EnhancedLoggingService,
        category: LogCategory,
        service: str,
        operation: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.logging_service = logging_service
        self.category = category
        self.service = service
        self.operation = operation
        self.user_id = user_id
        self.request_id = request_id
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        self.logging_service.log_info(
            self.category,
            self.service,
            self.operation,
            f"Started operation {self.operation}",
            user_id=self.user_id,
            request_id=self.request_id,
            metadata=self.metadata,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None

            if self.success:
                self.logging_service.log_performance(
                    self.service,
                    self.operation,
                    duration_ms,
                    success=True,
                    user_id=self.user_id,
                    request_id=self.request_id,
                    metadata=self.metadata,
                )
            else:
                self.logging_service.log_error(
                    self.category,
                    self.service,
                    self.operation,
                    f"Operation failed: {exc_val}",
                    user_id=self.user_id,
                    request_id=self.request_id,
                    duration_ms=duration_ms,
                    metadata=self.metadata,
                    stack_trace=str(exc_tb) if exc_tb else None,
                )


# Global instance
enhanced_logging_service = EnhancedLoggingService()


# Convenience functions
def log_operation(
    category: LogCategory,
    service: str,
    operation: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Context manager for logging operations"""
    return OperationLogger(
        enhanced_logging_service,
        category,
        service,
        operation,
        user_id,
        request_id,
        metadata,
    )
