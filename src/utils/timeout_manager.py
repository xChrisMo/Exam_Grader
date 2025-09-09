"""
Timeout Manager - Centralized timeout configuration and management.

This module provides utilities for managing timeouts across the application,
with dynamic adjustment based on service performance and error patterns.
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class TimeoutConfig:
    """Configuration for timeout settings."""
    
    # API timeouts
    api_timeout: int = 60
    llm_processing_timeout: int = 600
    llm_json_timeout: float = 30.0
    
    # Service timeouts
    ocr_processing_timeout: int = 180
    file_processing_timeout: int = 90
    mapping_service_timeout: int = 180
    grading_service_timeout: int = 600
    
    # System timeouts
    health_check_timeout: int = 30
    service_init_timeout: int = 60
    default_timeout: int = 60
    
    # Retry configuration
    max_retries: int = 5
    retry_delay: float = 2.0
    max_backoff_delay: float = 60.0

class TimeoutManager:
    """Manages timeout configurations and provides dynamic adjustment."""
    
    def __init__(self):
        self.config = self._load_config()
        self.performance_history: Dict[str, list] = {}
        self.error_patterns: Dict[str, int] = {}
        self.last_adjustment = datetime.now(timezone.utc)
        
    def _load_config(self) -> TimeoutConfig:
        """Load timeout configuration from environment variables."""
        return TimeoutConfig(
            api_timeout=int(os.getenv("API_TIMEOUT", "60")),
            llm_processing_timeout=int(os.getenv("TIMEOUT_LLM_PROCESSING", "600")),
            llm_json_timeout=float(os.getenv("LLM_JSON_TIMEOUT", "30.0")),
            ocr_processing_timeout=int(os.getenv("TIMEOUT_OCR_PROCESSING", "180")),
            file_processing_timeout=int(os.getenv("TIMEOUT_FILE_PROCESSING", "90")),
            mapping_service_timeout=int(os.getenv("TIMEOUT_MAPPING_SERVICE", "180")),
            grading_service_timeout=int(os.getenv("TIMEOUT_GRADING_SERVICE", "600")),
            health_check_timeout=int(os.getenv("TIMEOUT_HEALTH_CHECK", "30")),
            service_init_timeout=int(os.getenv("TIMEOUT_SERVICE_INIT", "60")),
            default_timeout=int(os.getenv("TIMEOUT_DEFAULT", "60")),
            max_retries=int(os.getenv("API_RETRY_ATTEMPTS", "5")),
            retry_delay=float(os.getenv("API_RETRY_DELAY", "2.0")),
            max_backoff_delay=float(os.getenv("API_MAX_BACKOFF_DELAY", "60.0"))
        )
    
    def get_timeout(self, service: str, operation: str = "default") -> int:
        """Get timeout for a specific service and operation."""
        timeout_key = f"{service}_{operation}"
        
        # Check for specific timeout configuration
        if service == "llm" and operation == "processing":
            return self.config.llm_processing_timeout
        elif service == "llm" and operation == "json":
            return int(self.config.llm_json_timeout)
        elif service == "api":
            return self.config.api_timeout
        elif service == "ocr":
            return self.config.ocr_processing_timeout
        elif service == "file":
            return self.config.file_processing_timeout
        elif service == "mapping":
            return self.config.mapping_service_timeout
        elif service == "grading":
            return self.config.grading_service_timeout
        elif service == "health":
            return self.config.health_check_timeout
        elif service == "init":
            return self.config.service_init_timeout
        else:
            return self.config.default_timeout
    
    def record_performance(self, service: str, operation: str, duration: float, success: bool):
        """Record performance metrics for timeout adjustment."""
        key = f"{service}_{operation}"
        
        if key not in self.performance_history:
            self.performance_history[key] = []
        
        self.performance_history[key].append({
            "timestamp": datetime.now(timezone.utc),
            "duration": duration,
            "success": success
        })
        
        # Keep only last 100 records
        if len(self.performance_history[key]) > 100:
            self.performance_history[key] = self.performance_history[key][-100:]
        
        # Record error patterns
        if not success:
            error_key = f"{service}_{operation}_error"
            self.error_patterns[error_key] = self.error_patterns.get(error_key, 0) + 1
    
    def adjust_timeout(self, service: str, operation: str, reason: str = "performance"):
        """Dynamically adjust timeout based on performance and error patterns."""
        current_timeout = self.get_timeout(service, operation)
        key = f"{service}_{operation}"
        
        if key not in self.performance_history:
            return current_timeout
        
        recent_performance = self.performance_history[key][-20:]  # Last 20 operations
        
        if not recent_performance:
            return current_timeout
        
        # Calculate success rate and average duration
        success_count = sum(1 for p in recent_performance if p["success"])
        success_rate = success_count / len(recent_performance)
        avg_duration = sum(p["duration"] for p in recent_performance) / len(recent_performance)
        
        new_timeout = current_timeout
        
        # Adjust based on success rate
        if success_rate < 0.7:  # Less than 70% success rate
            # Increase timeout by 50% but cap at 2x original
            new_timeout = min(current_timeout * 1.5, current_timeout * 2)
            logger.info(f"Increasing timeout for {service}_{operation} from {current_timeout}s to {new_timeout}s due to low success rate ({success_rate:.2%})")
        
        elif success_rate > 0.95 and avg_duration < current_timeout * 0.5:
            # High success rate and fast execution - can reduce timeout
            new_timeout = max(current_timeout * 0.8, current_timeout * 0.5)
            logger.info(f"Decreasing timeout for {service}_{operation} from {current_timeout}s to {new_timeout}s due to high performance")
        
        # Update configuration
        if new_timeout != current_timeout:
            if service == "llm" and operation == "processing":
                self.config.llm_processing_timeout = int(new_timeout)
            elif service == "llm" and operation == "json":
                self.config.llm_json_timeout = new_timeout
            elif service == "api":
                self.config.api_timeout = int(new_timeout)
            elif service == "ocr":
                self.config.ocr_processing_timeout = int(new_timeout)
            elif service == "file":
                self.config.file_processing_timeout = int(new_timeout)
            elif service == "mapping":
                self.config.mapping_service_timeout = int(new_timeout)
            elif service == "grading":
                self.config.grading_service_timeout = int(new_timeout)
            else:
                self.config.default_timeout = int(new_timeout)
            
            self.last_adjustment = datetime.now(timezone.utc)
        
        return int(new_timeout)
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return {
            "max_retries": self.config.max_retries,
            "retry_delay": self.config.retry_delay,
            "max_backoff_delay": self.config.max_backoff_delay
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current timeout manager status."""
        return {
            "config": {
                "api_timeout": self.config.api_timeout,
                "llm_processing_timeout": self.config.llm_processing_timeout,
                "llm_json_timeout": self.config.llm_json_timeout,
                "ocr_processing_timeout": self.config.ocr_processing_timeout,
                "file_processing_timeout": self.config.file_processing_timeout,
                "mapping_service_timeout": self.config.mapping_service_timeout,
                "grading_service_timeout": self.config.grading_service_timeout,
                "health_check_timeout": self.config.health_check_timeout,
                "service_init_timeout": self.config.service_init_timeout,
                "default_timeout": self.config.default_timeout
            },
            "performance_history": {
                key: len(records) for key, records in self.performance_history.items()
            },
            "error_patterns": self.error_patterns,
            "last_adjustment": self.last_adjustment.isoformat()
        }

# Global instance
timeout_manager = TimeoutManager()
