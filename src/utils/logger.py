import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from src.config.config_manager import ConfigManager

class Logger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        config = ConfigManager().config
        self.logger = logging.getLogger('grading_app')
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # File handler with daily rotation
        log_file = os.path.join(log_dir, f'grading_app_{datetime.now().strftime("%Y%m%d")}.log')
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(getattr(logging, config.log_level))
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, config.log_level))
        
        # Formatter with detailed information
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Performance metrics
        self.metrics: Dict[str, Any] = {
            'start_time': datetime.now(),
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'grading_operations': 0,
            'errors': 0
        }
    
    def get_logger(self):
        return self.logger
    
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
        self.logger.info("Performance Metrics:")
        self.logger.info(f"  Duration: {duration:.2f} seconds")
        self.logger.info(f"  API Calls: {self.metrics['api_calls']}")
        self.logger.info(f"  Cache Hits: {self.metrics['cache_hits']}")
        self.logger.info(f"  Cache Misses: {self.metrics['cache_misses']}")
        self.logger.info(f"  Grading Operations: {self.metrics['grading_operations']}")
        self.logger.info(f"  Errors: {self.metrics['errors']}")
        
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            cache_hit_rate = (self.metrics['cache_hits'] / 
                            (self.metrics['cache_hits'] + self.metrics['cache_misses'])) * 100
            self.logger.info(f"  Cache Hit Rate: {cache_hit_rate:.2f}%")
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, duration: float) -> None:
        """Log API call details."""
        self.log_metric('api_calls')
        self.logger.info(f"API Call: {method} {endpoint} - Status: {status_code} - Duration: {duration:.2f}s")
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = False) -> None:
        """Log cache operation details."""
        if operation == 'get':
            if hit:
                self.log_metric('cache_hits')
                self.logger.debug(f"Cache hit for key: {key}")
            else:
                self.log_metric('cache_misses')
                self.logger.debug(f"Cache miss for key: {key}")
        elif operation == 'set':
            self.logger.debug(f"Cache set for key: {key}")
    
    def log_grading_operation(self, question_number: int, student_id: str, score: float, 
                            confidence: float, duration: float) -> None:
        """Log grading operation details."""
        self.log_metric('grading_operations')
        self.logger.info(
            f"Graded Question {question_number} for Student {student_id} - "
            f"Score: {score} - Confidence: {confidence:.2f} - Duration: {duration:.2f}s"
        )
    
    def log_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with context."""
        self.log_metric('errors')
        error_msg = f"Error ({error_type}): {message}"
        if context:
            error_msg += f" - Context: {context}"
        self.logger.error(error_msg)
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning with context."""
        warning_msg = f"Warning: {message}"
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