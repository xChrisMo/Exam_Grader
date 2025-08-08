"""Comprehensive Logging System for Exam Grader Application.

This module provides a unified, comprehensive logging system that integrates
with the standardized error handling system and provides advanced features
like structured logging, log aggregation, and performance monitoring.
"""

try:
    from .comprehensive_logger import (
        AuditLogger,
        ComprehensiveLogger,
        LogContext,
        LogLevel,
        PerformanceLogger,
        SecurityLogger,
        get_logger,
        setup_logging,
    )
    from .config import (
        LoggingConfiguration,
        get_application_logger,
        get_application_structured_logger,
        get_logging_metrics,
        setup_application_logging,
    )
    from .flask_integration import (
        FlaskLoggingIntegration,
        log_performance,
        log_route,
        setup_flask_logging,
    )
    from .log_aggregator import LogAggregator, LogAnalytics, LogMetrics
    from .structured_logger import (
        StructuredFormatter,
        StructuredLogEntry,
        StructuredLogger,
        StructuredLoggerManager,
        get_structured_logger,
        setup_structured_logging,
    )
except ImportError as e:
    ComprehensiveLogger = None
    LogLevel = None
    LogContext = None
    PerformanceLogger = None
    SecurityLogger = None
    AuditLogger = None
    get_logger = None
    setup_logging = None
    LogAggregator = None
    LogMetrics = None
    LogAnalytics = None
    StructuredLogger = None
    StructuredLogEntry = None
    StructuredFormatter = None
    StructuredLoggerManager = None
    get_structured_logger = None
    setup_structured_logging = None
    FlaskLoggingIntegration = None
    setup_flask_logging = None
    log_route = None
    log_performance = None
    LoggingConfiguration = None
    setup_application_logging = None
    get_application_logger = None
    get_application_structured_logger = None
    get_logging_metrics = None

    import warnings

    warnings.warn(f"Some logging components unavailable: {e}", ImportWarning)


def configure_logging(
    app_name: str = "exam_grader",
    log_level: str = "INFO",
    log_dir: str = "logs",
    **kwargs,
):
    """Configure comprehensive logging system.

    Args:
        app_name: Application name
        log_level: Logging level
        log_dir: Log directory
        **kwargs: Additional configuration options

    Returns:
        LoggingConfiguration instance
    """
    if setup_application_logging:
        return setup_application_logging(
            app_name=app_name, log_level=log_level, log_dir=log_dir, **kwargs
        )
    return None


def get_comprehensive_logger(name: str = None):
    """Get a comprehensive logger instance.

    Args:
        name: Logger name

    Returns:
        ComprehensiveLogger instance or None
    """
    if get_application_logger:
        return get_application_logger(name)
    elif get_logger:
        return get_logger(name)
    return None


def get_json_logger(name: str = None):
    """Get a structured JSON logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance or None
    """
    if get_application_structured_logger:
        return get_application_structured_logger(name)
    elif get_structured_logger:
        return get_structured_logger(name)
    return None


__all__ = [
    # Core logging
    "ComprehensiveLogger",
    "LogLevel",
    "LogContext",
    "PerformanceLogger",
    "SecurityLogger",
    "AuditLogger",
    "get_logger",
    "setup_logging",
    # Log aggregation
    "LogAggregator",
    "LogMetrics",
    "LogAnalytics",
    # Structured logging
    "StructuredLogger",
    "StructuredLogEntry",
    "StructuredFormatter",
    "StructuredLoggerManager",
    "get_structured_logger",
    "setup_structured_logging",
    # Flask integration
    "FlaskLoggingIntegration",
    "setup_flask_logging",
    "log_route",
    "log_performance",
    # Configuration
    "LoggingConfiguration",
    "setup_application_logging",
    "get_application_logger",
    "get_application_structured_logger",
    "get_logging_metrics",
    # Convenience functions
    "configure_logging",
    "get_comprehensive_logger",
    "get_json_logger",
]
