"""
Logging configuration for the application.
"""
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with proper configuration.
    
    Args:
        name: Name of the logger (usually __name__)
        log_file: Optional log file path. If not provided, logs to logs/app.log
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Only configure if it hasn't been configured before
    if not logger.handlers:
        # Set log level from environment or default to INFO
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Create file handler
        if log_file is None:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / 'app.log'
            
        file_handler = RotatingFileHandler(
            str(log_file),  # Convert Path to string
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Don't propagate to root logger
        logger.propagate = False
        
    return logger

class Logger:
    """Enhanced logger with additional features."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the logger with configuration."""
        if getattr(self, '_initialized', False):
            return
            
        # Let setup_logger handle directory creation by passing None
        self.logger = setup_logger('exam_grader', None)
        
        # Performance metrics
        self.metrics = {
            'start_time': datetime.now(),
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'grading_operations': 0,
            'errors': 0,
            'warnings': 0,
            'file_operations': 0,
            'ocr_operations': 0
        }
        
        self._initialized = True
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self.logger
    
    # Standard logging methods that match Python's logging interface
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self.log_metric('warnings')
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self.log_metric('errors')
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self.log_metric('errors')
        self.logger.critical(message, *args, **kwargs)
    
    # Original enhanced logging methods
    def log_metric(self, metric_name: str, value: Any = 1) -> None:
        """Log a metric value."""
        if metric_name in self.metrics:
            if isinstance(self.metrics[metric_name], (int, float)):
                self.metrics[metric_name] += value
            else:
                self.metrics[metric_name] = value
    
    def log_performance(self) -> None:
        """Log performance metrics."""
        duration = (datetime.now() - self.metrics['start_time']).total_seconds()
        self.info("Performance Metrics:")
        self.info(f"  Duration: {duration:.2f} seconds")
        self.info(f"  API Calls: {self.metrics['api_calls']}")
        self.info(f"  Cache Hits: {self.metrics['cache_hits']}")
        self.info(f"  Cache Misses: {self.metrics['cache_misses']}")
        self.info(f"  Grading Operations: {self.metrics['grading_operations']}")
        self.info(f"  File Operations: {self.metrics['file_operations']}")
        self.info(f"  OCR Operations: {self.metrics['ocr_operations']}")
        self.info(f"  Errors: {self.metrics['errors']}")
        self.info(f"  Warnings: {self.metrics['warnings']}")
        
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            cache_hit_rate = (self.metrics['cache_hits'] / 
                            (self.metrics['cache_hits'] + self.metrics['cache_misses'])) * 100
            self.info(f"  Cache Hit Rate: {cache_hit_rate:.2f}%")
    
    # Keep existing specialized logging methods for backward compatibility
    def log_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with context."""
        self.log_metric('errors')
        error_msg = f"{error_type}: {message}"
        if context:
            error_msg += f" - Context: {context}"
        self.logger.error(error_msg)
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning with context."""
        self.log_metric('warnings')
        warning_msg = message
        if context:
            warning_msg += f" - Context: {context}"
        self.logger.warning(warning_msg)
    
    def log_info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info with context."""
        info_msg = message
        if context:
            info_msg += f" - Context: {context}"
        self.logger.info(info_msg)
    
    def log_debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug with context."""
        debug_msg = message
        if context:
            debug_msg += f" - Context: {context}"
        self.logger.debug(debug_msg)
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, duration: float) -> None:
        """Log API call details.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            duration: Call duration in seconds
        """
        self.log_metric('api_calls')
        self.logger.info(f"API Call: {method} {endpoint} - Status: {status_code} - Duration: {duration:.2f}s")
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = False) -> None:
        """Log cache operation details.
        
        Args:
            operation: Cache operation type
            key: Cache key
            hit: Whether it was a cache hit
        """
        if operation == 'get':
            if hit:
                self.log_metric('cache_hits')
                self.logger.debug(f"Cache hit for key: {key}")
            else:
                self.log_metric('cache_misses')
                self.logger.debug(f"Cache miss for key: {key}")
        elif operation == 'set':
            self.logger.debug(f"Cache set for key: {key}")
    
    def log_file_operation(self, operation: str, file_path: str, success: bool = True) -> None:
        """Log file operation details.
        
        Args:
            operation: File operation type
            file_path: Path to the file
            success: Whether the operation was successful
        """
        self.log_metric('file_operations')
        if success:
            self.logger.debug(f"File {operation}: {file_path}")
        else:
            self.log_metric('errors')
            self.logger.error(f"Failed to {operation} file: {file_path}")
    
    def log_ocr_operation(self, file_path: str, success: bool = True, confidence: Optional[float] = None) -> None:
        """Log OCR operation details.
        
        Args:
            file_path: Path to the image file
            success: Whether OCR was successful
            confidence: OCR confidence score if available
        """
        self.log_metric('ocr_operations')
        if success:
            if confidence is not None:
                self.logger.info(f"OCR successful on {file_path} - Confidence: {confidence:.2f}")
            else:
                self.logger.info(f"OCR successful on {file_path}")
        else:
            self.log_metric('errors')
            self.logger.error(f"OCR failed on {file_path}")

# Create default logger instance
logger = Logger() 