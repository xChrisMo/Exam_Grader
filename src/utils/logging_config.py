"""Enhanced Logging Configuration for Exam Grader Application.

This module provides simplified, user-friendly logging configuration
with different verbosity levels for development and production.
Now integrates with the comprehensive logging system.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# Import comprehensive logging system
try:
    from ..logging import (
        configure_logging as setup_comprehensive_logging,
        get_comprehensive_logger,
        get_json_logger,
        LoggingConfiguration
    )
    COMPREHENSIVE_LOGGING_AVAILABLE = True
except ImportError:
    COMPREHENSIVE_LOGGING_AVAILABLE = False
    setup_comprehensive_logging = None
    get_comprehensive_logger = None
    get_json_logger = None
    LoggingConfiguration = None

class LoggingConfig:
    """
    Centralized logging configuration with simplified output.
    
    Features:
    - Clean, readable log format
    - Configurable verbosity levels
    - Separate loggers for different components
    - Production-friendly output
    """

    def __init__(self, log_level: str = "INFO", log_dir: Optional[str] = None):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_dir: Directory for log files (optional)
        """
        self.log_level = log_level.upper()
        self.log_dir = Path(log_dir) if log_dir else None
        self.loggers = {}
        
        if self.log_dir:
            self.log_dir.mkdir(exist_ok=True)

    def setup_logging(self, simplified: bool = True) -> None:
        """
        Setup application logging with simplified or detailed format.
        
        Args:
            simplified: If True, use simplified format for better readability
        """
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        
        if simplified:
            console_format = logging.Formatter(
                '%(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
        
        if self.log_dir:
            file_handler = logging.FileHandler(
                self.log_dir / 'exam_grader.log',
                mode='a',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always detailed in files
            
            file_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            root_logger.addHandler(file_handler)

    def configure_third_party_loggers(self, quiet_mode: bool = True) -> None:
        """
        Configure third-party library loggers to reduce noise.
        
        Args:
            quiet_mode: If True, suppress verbose third-party logging
        """
        if quiet_mode:
            # Reduce SQLAlchemy verbosity
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
            logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
            logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
            logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
            
            # Reduce Flask verbosity
            logging.getLogger('werkzeug').setLevel(logging.WARNING)
            
            # Reduce requests verbosity
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('requests').setLevel(logging.WARNING)
            
            # Reduce other common libraries
            logging.getLogger('PIL').setLevel(logging.WARNING)
            logging.getLogger('matplotlib').setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a configured logger for a specific component.
        
        Args:
            name: Logger name (usually module name)
            
        Returns:
            Configured logger instance
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]

    def set_component_level(self, component: str, level: str) -> None:
        """
        Set logging level for a specific component.
        
        Args:
            component: Component name (e.g., 'ocr_service', 'llm_service')
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        logger = logging.getLogger(component)
        logger.setLevel(getattr(logging, level.upper()))

    def create_startup_summary(self, host: str = "127.0.0.1", port: int = 5000) -> str:
        """
        Create a clean startup summary message.
        
        Args:
            host: The host address of the server.
            port: The port number of the server.
            
        Returns:
            Formatted startup summary
        """
        return f"""
🎓 EXAM GRADER - AI-POWERED ASSESSMENT PLATFORM
================================================
🌐 Dashboard: http://{host}:{port}
🔧 Debug mode: ON
📁 Storage: temp/ & output/
📊 Max file size: 20MB
🔑 API Services: ✅ READY
================================================
Press Ctrl+C to stop the server
================================================"""

    @staticmethod
    def get_environment_config() -> Dict[str, str]:
        """
        Get logging configuration from environment variables.
        
        Returns:
            Dictionary of logging configuration
        """
        return {
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_dir': os.getenv('LOG_DIR', None),
            'simplified_logging': os.getenv('SIMPLIFIED_LOGGING', 'True').lower() == 'true',
            'quiet_third_party': os.getenv('QUIET_THIRD_PARTY', 'True').lower() == 'true',
            'database_echo': os.getenv('DATABASE_ECHO', 'False').lower() == 'true',
        }

# Global logging configuration instance
_logging_config = None

def setup_application_logging(
    log_level: str = None,
    log_dir: str = None,
    simplified: bool = None,
    quiet_third_party: bool = None,
    use_comprehensive: bool = True
) -> LoggingConfig:
    """Setup application-wide logging configuration.
    
    Args:
        log_level: Logging level (defaults to environment variable)
        log_dir: Log directory (defaults to environment variable)
        simplified: Use simplified format (defaults to environment variable)
        quiet_third_party: Quiet third-party loggers (defaults to environment variable)
        use_comprehensive: Use comprehensive logging system if available
        
    Returns:
        Configured LoggingConfig instance or LoggingConfiguration
    """
    global _logging_config
    
    env_config = LoggingConfig.get_environment_config()
    
    log_level = log_level or env_config['log_level']
    log_dir = log_dir or env_config['log_dir']
    simplified = simplified if simplified is not None else env_config['simplified_logging']
    quiet_third_party = quiet_third_party if quiet_third_party is not None else env_config['quiet_third_party']
    
    if use_comprehensive and COMPREHENSIVE_LOGGING_AVAILABLE and setup_comprehensive_logging:
        try:
            comprehensive_config = setup_comprehensive_logging(
                app_name='exam_grader',
                log_level=log_level,
                log_dir=log_dir or 'logs'
            )
            
            # Configure third-party loggers
            if quiet_third_party:
                _configure_third_party_loggers_quiet()
            
            return comprehensive_config
        except Exception as e:
            import logging
            logging.warning(f"Comprehensive logging failed, falling back to traditional: {e}")
    
    # Create and configure traditional logging
    _logging_config = LoggingConfig(log_level, log_dir)
    _logging_config.setup_logging(simplified)
    _logging_config.configure_third_party_loggers(quiet_third_party)
    
    return _logging_config

def get_logger(name: str, use_comprehensive: bool = True) -> logging.Logger:
    """Get a logger for the specified component.
    
    Args:
        name: Component name
        use_comprehensive: Use comprehensive logging if available
        
    Returns:
        Configured logger instance
    """
    global _logging_config
    
    # Try comprehensive logging first
    if use_comprehensive and COMPREHENSIVE_LOGGING_AVAILABLE:
        try:
            comprehensive_logger = get_comprehensive_logger(name)
            if comprehensive_logger:
                return comprehensive_logger.logger  # Return the underlying logger
        except Exception:
            pass  # Fall back to traditional logging
    
    # Fall back to traditional logging
    if _logging_config is None:
        _logging_config = setup_application_logging(use_comprehensive=False)
    
    return _logging_config.get_logger(name)

def log_startup_summary(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    """
    Log a clean startup summary.
    
    Args:
        host: Server host
        port: Server port
        debug: Debug mode status
    """
    logger = get_logger('startup')
    
    summary = f"""
🎓 EXAM GRADER - AI-POWERED ASSESSMENT PLATFORM
================================================
🌐 Dashboard: http://{host}:{port}
🔧 Debug mode: {'ON' if debug else 'OFF'}
📁 Storage: temp/ & output/
📊 Max file size: 20MB
🔑 API Services: ✅ READY
================================================
Press Ctrl+C to stop the server
================================================"""
    
    logger.info(summary)

def _configure_third_party_loggers_quiet():
    """Configure third-party loggers to reduce noise."""
    # Reduce SQLAlchemy verbosity
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Reduce Flask verbosity
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # Reduce requests verbosity
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Reduce other common libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

def get_structured_logger(name: str):
    """Get a structured JSON logger if available.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance or None
    """
    if COMPREHENSIVE_LOGGING_AVAILABLE and get_json_logger:
        try:
            return get_json_logger(name)
        except Exception:
            pass
    return None

def create_startup_summary(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> str:
    """Create a clean startup summary message.
    
    Args:
        host: The host address of the server.
        port: The port number of the server.
        debug: Debug mode status
        
    Returns:
        Formatted startup summary
    """
    return f"""
🎓 EXAM GRADER - AI-POWERED ASSESSMENT PLATFORM
================================================
🌐 Dashboard: http://{host}:{port}
🔧 Debug mode: {'ON' if debug else 'OFF'}
📁 Storage: temp/ & output/
📊 Max file size: 20MB
🔑 API Services: ✅ READY
================================================
Press Ctrl+C to stop the server
================================================"""
