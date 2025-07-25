"""Comprehensive Logging Configuration.

This module provides centralized configuration for the comprehensive logging system,
integrating all logging components and providing easy setup for applications.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from .log_aggregator import LogAggregator
    from .flask_integration import FlaskLoggingIntegration
except ImportError:
    # Fallback for standalone usage
    ComprehensiveLogger = None
    LogLevel = None
    setup_comprehensive_logging = None
    StructuredLogger = None
    setup_structured_logging = None
    LogAggregator = None
    FlaskLoggingIntegration = None


class LoggingConfiguration:
    """Centralized logging configuration manager."""
    
    def __init__(
        self,
        app_name: str = 'exam_grader',
        log_level: str = 'INFO',
        log_dir: Optional[str] = None,
        enable_structured_logging: bool = True,
        enable_performance_logging: bool = True,
        enable_security_logging: bool = True,
        enable_audit_logging: bool = True,
        enable_aggregation: bool = True,
        max_log_files: int = 10,
        max_file_size_mb: int = 100
    ):
        """Initialize logging configuration.
        
        Args:
            app_name: Application name for logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (defaults to logs/)
            enable_structured_logging: Enable structured JSON logging
            enable_performance_logging: Enable performance monitoring
            enable_security_logging: Enable security event logging
            enable_audit_logging: Enable audit trail logging
            enable_aggregation: Enable log aggregation and analytics
            max_log_files: Maximum number of log files to keep
            max_file_size_mb: Maximum size of each log file in MB
        """
        self.app_name = app_name
        self.log_level = log_level.upper()
        self.log_dir = Path(log_dir) if log_dir else Path('logs')
        self.enable_structured_logging = enable_structured_logging
        self.enable_performance_logging = enable_performance_logging
        self.enable_security_logging = enable_security_logging
        self.enable_audit_logging = enable_audit_logging
        self.enable_aggregation = enable_aggregation
        self.max_log_files = max_log_files
        self.max_file_size_mb = max_file_size_mb
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.comprehensive_logger: Optional[ComprehensiveLogger] = None
        self.structured_logger: Optional[StructuredLogger] = None
        self.log_aggregator: Optional[LogAggregator] = None
        self.flask_integration: Optional[FlaskLoggingIntegration] = None
        
        # Configuration state
        self._configured = False
    
    def configure(self) -> Dict[str, Any]:
        """Configure all logging components.
        
        Returns:
            Configuration status dictionary
        """
        if self._configured:
            return {'status': 'already_configured'}
        
        status = {
            'comprehensive_logger': False,
            'structured_logger': False,
            'log_aggregator': False,
            'errors': []
        }
        
        try:
            # Configure comprehensive logging
            if ComprehensiveLogger and setup_comprehensive_logging:
                setup_comprehensive_logging(
                    log_level=self.log_level,
                    log_dir=str(self.log_dir),
                    app_name=self.app_name,
                    enable_performance=self.enable_performance_logging,
                    enable_security=self.enable_security_logging,
                    enable_audit=self.enable_audit_logging,
                    max_files=self.max_log_files,
                    max_file_size_mb=self.max_file_size_mb
                )
                
                self.comprehensive_logger = ComprehensiveLogger(self.app_name)
                status['comprehensive_logger'] = True
            
            # Configure structured logging
            if self.enable_structured_logging and StructuredLogger and setup_structured_logging:
                setup_structured_logging(
                    log_level=self.log_level,
                    log_dir=str(self.log_dir),
                    app_name=self.app_name,
                    max_files=self.max_log_files,
                    max_file_size_mb=self.max_file_size_mb
                )
                
                self.structured_logger = StructuredLogger(f"{self.app_name}_structured")
                status['structured_logger'] = True
            
            # Configure log aggregation
            if self.enable_aggregation and LogAggregator:
                self.log_aggregator = LogAggregator(
                    log_directory=str(self.log_dir),
                    app_name=self.app_name
                )
                status['log_aggregator'] = True
            
            self._configured = True
            status['status'] = 'success'
            
        except Exception as e:
            status['errors'].append(f"Configuration error: {str(e)}")
            status['status'] = 'partial_failure'
        
        return status
    
    def setup_flask_integration(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_performance: bool = True,
        exclude_paths: Optional[List[str]] = None
    ) -> Optional[FlaskLoggingIntegration]:
        """Setup Flask logging integration.
        
        Args:
            app: Flask application instance
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses
            log_performance: Whether to log performance metrics
            exclude_paths: Paths to exclude from logging
        
        Returns:
            FlaskLoggingIntegration instance or None
        """
        if not FlaskLoggingIntegration:
            return None
        
        try:
            self.flask_integration = FlaskLoggingIntegration(
                app=app,
                logger_name=f"{self.app_name}_flask",
                log_requests=log_requests,
                log_responses=log_responses,
                log_performance=log_performance,
                exclude_paths=exclude_paths or ['/health', '/favicon.ico', '/static']
            )
            
            return self.flask_integration
            
        except Exception as e:
            if self.comprehensive_logger:
                self.comprehensive_logger.error(f"Failed to setup Flask integration: {str(e)}")
            return None
    
    def get_logger(self, name: Optional[str] = None) -> Optional[ComprehensiveLogger]:
        """Get a comprehensive logger instance.
        
        Args:
            name: Logger name (defaults to app name)
        
        Returns:
            ComprehensiveLogger instance or None
        """
        if not self._configured:
            self.configure()
        
        if not ComprehensiveLogger:
            return None
        
        logger_name = name or self.app_name
        return ComprehensiveLogger(logger_name)
    
    def get_structured_logger(self, name: Optional[str] = None) -> Optional[StructuredLogger]:
        """Get a structured logger instance.
        
        Args:
            name: Logger name (defaults to app name)
        
        Returns:
            StructuredLogger instance or None
        """
        if not self._configured:
            self.configure()
        
        if not StructuredLogger:
            return None
        
        logger_name = name or f"{self.app_name}_structured"
        return StructuredLogger(logger_name)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics and statistics.
        
        Returns:
            Metrics dictionary
        """
        metrics = {
            'configured': self._configured,
            'log_directory': str(self.log_dir),
            'log_level': self.log_level,
            'components': {
                'comprehensive_logger': self.comprehensive_logger is not None,
                'structured_logger': self.structured_logger is not None,
                'log_aggregator': self.log_aggregator is not None,
                'flask_integration': self.flask_integration is not None
            }
        }
        
        # Add aggregator metrics if available
        if self.log_aggregator:
            try:
                aggregator_metrics = self.log_aggregator.get_metrics()
                metrics['aggregator_metrics'] = aggregator_metrics
            except Exception as e:
                metrics['aggregator_error'] = str(e)
        
        # Add Flask metrics if available
        if self.flask_integration:
            try:
                flask_metrics = self.flask_integration.get_request_metrics()
                metrics['flask_metrics'] = flask_metrics
            except Exception as e:
                metrics['flask_error'] = str(e)
        
        return metrics
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            'app_name': self.app_name,
            'log_level': self.log_level,
            'log_dir': str(self.log_dir),
            'enable_structured_logging': self.enable_structured_logging,
            'enable_performance_logging': self.enable_performance_logging,
            'enable_security_logging': self.enable_security_logging,
            'enable_audit_logging': self.enable_audit_logging,
            'enable_aggregation': self.enable_aggregation,
            'max_log_files': self.max_log_files,
            'max_file_size_mb': self.max_file_size_mb,
            'configured': self._configured
        }


# Global configuration instance
_global_config: Optional[LoggingConfiguration] = None


def setup_application_logging(
    app_name: str = 'exam_grader',
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    **kwargs
) -> LoggingConfiguration:
    """Setup application-wide logging configuration.
    
    Args:
        app_name: Application name
        log_level: Logging level (from environment or config)
        log_dir: Log directory (from environment or config)
        **kwargs: Additional configuration options
    
    Returns:
        LoggingConfiguration instance
    """
    global _global_config
    
    # Get configuration from environment if not provided
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    if log_dir is None:
        log_dir = os.getenv('LOG_DIR', 'logs')
    
    # Create configuration
    _global_config = LoggingConfiguration(
        app_name=app_name,
        log_level=log_level,
        log_dir=log_dir,
        **kwargs
    )
    
    # Configure logging
    status = _global_config.configure()
    
    # Log configuration status
    if _global_config.comprehensive_logger:
        _global_config.comprehensive_logger.info(
            f"Logging configuration completed: {status['status']}",
            extra={'configuration_status': status}
        )
    
    return _global_config


def get_application_logger(name: Optional[str] = None) -> Optional[ComprehensiveLogger]:
    """Get application logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        ComprehensiveLogger instance or None
    """
    if _global_config:
        return _global_config.get_logger(name)
    return None


def get_application_structured_logger(name: Optional[str] = None) -> Optional[StructuredLogger]:
    """Get application structured logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        StructuredLogger instance or None
    """
    if _global_config:
        return _global_config.get_structured_logger(name)
    return None


def get_logging_metrics() -> Dict[str, Any]:
    """Get application logging metrics.
    
    Returns:
        Metrics dictionary
    """
    if _global_config:
        return _global_config.get_metrics()
    return {'error': 'Logging not configured'}