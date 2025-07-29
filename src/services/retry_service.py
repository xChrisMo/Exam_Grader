"""
Retry Service with Circuit Breaker Pattern

This module provides retry functionality with exponential backoff and circuit breaker
pattern for handling transient failures in external service calls.
"""
from typing import Any, Dict, Optional

import functools
import time
from datetime import datetime, timedelta

from utils.logger import logger

@dataclass
class ServiceStats:
    """Statistics for a service."""
    service_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    circuit_breaker_trips: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    current_state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # for half-open state

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass

class RetryService:
    """Service for handling retries with circuit breaker pattern."""
    
    def __init__(self):
        self.services: Dict[str, ServiceStats] = {}
        self.circuit_configs: Dict[str, CircuitBreakerConfig] = {}
    
    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get statistics for a service."""
        if service_name not in self.services:
            self.services[service_name] = ServiceStats(service_name=service_name)
        
        stats = self.services[service_name]
        return {
            "service_name": stats.service_name,
            "total_attempts": stats.total_attempts,
            "successful_attempts": stats.successful_attempts,
            "failed_attempts": stats.failed_attempts,
            "circuit_breaker_trips": stats.circuit_breaker_trips,
            "success_rate": (
                stats.successful_attempts / stats.total_attempts 
                if stats.total_attempts > 0 else 0
            ),
            "last_success": stats.last_success.isoformat() if stats.last_success else None,
            "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
            "current_state": stats.current_state
        }
    
    def configure_circuit_breaker(
        self, 
        service_name: str, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        """Configure circuit breaker for a service."""
        self.circuit_configs[service_name] = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold
        )
    
    def _get_circuit_state(self, service_name: str) -> str:
        """Get current circuit breaker state."""
        if service_name not in self.services:
            return "CLOSED"
        
        stats = self.services[service_name]
        config = self.circuit_configs.get(service_name, CircuitBreakerConfig())
        
        if (stats.failed_attempts >= config.failure_threshold and 
            stats.current_state == "CLOSED"):
            stats.current_state = "OPEN"
            stats.circuit_breaker_trips += 1
            logger.warning(f"Circuit breaker opened for service: {service_name}")
        
        elif (stats.current_state == "OPEN" and 
              stats.last_failure and
              datetime.now() - stats.last_failure > timedelta(seconds=config.recovery_timeout)):
            stats.current_state = "HALF_OPEN"
            logger.info(f"Circuit breaker moved to half-open for service: {service_name}")
        
        return stats.current_state
    
    def _record_success(self, service_name: str):
        """Record a successful operation."""
        if service_name not in self.services:
            self.services[service_name] = ServiceStats(service_name=service_name)
        
        stats = self.services[service_name]
        stats.total_attempts += 1
        stats.successful_attempts += 1
        stats.last_success = datetime.now()
        
        # Reset failure count on success
        if stats.current_state in ["HALF_OPEN", "OPEN"]:
            config = self.circuit_configs.get(service_name, CircuitBreakerConfig())
            if stats.successful_attempts >= config.success_threshold:
                stats.current_state = "CLOSED"
                stats.failed_attempts = 0
                logger.info(f"Circuit breaker closed for service: {service_name}")
    
    def _record_failure(self, service_name: str):
        """Record a failed operation."""
        if service_name not in self.services:
            self.services[service_name] = ServiceStats(service_name=service_name)
        
        stats = self.services[service_name]
        stats.total_attempts += 1
        stats.failed_attempts += 1
        stats.last_failure = datetime.now()
    
    def execute_with_retry(
        self,
        func: Callable,
        service_name: str,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic and circuit breaker."""
        
        # Check circuit breaker state
        circuit_state = self._get_circuit_state(service_name)
        if circuit_state == "OPEN":
            raise CircuitBreakerError(f"Circuit breaker is open for service: {service_name}")
        
        last_exception = None
        delay = base_delay
        
        for attempt in range(max_attempts):
            try:
                result = func(*args, **kwargs)
                self._record_success(service_name)
                return result
                
            except Exception as e:
                last_exception = e
                self._record_failure(service_name)
                
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed for {service_name}: {str(e)}"
                )
                
                # Don't delay on the last attempt
                if attempt < max_attempts - 1:
                    time.sleep(min(delay, max_delay))
                    delay *= backoff_multiplier
        
        # All attempts failed
        logger.error(f"All {max_attempts} attempts failed for {service_name}")
        raise last_exception

# Global retry service instance
retry_service = RetryService()

def retry_with_backoff(
    service_name: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0
):
    """Decorator for adding retry logic with exponential backoff."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_service.execute_with_retry(
                func=func,
                service_name=service_name,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_multiplier=backoff_multiplier,
                *args,
                **kwargs
            )
        return wrapper
    return decorator

def configure_service_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 3
):
    """Configure circuit breaker for a service."""
    retry_service.configure_circuit_breaker(
        service_name=service_name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold
    )

configure_service_circuit_breaker("ocr_service", failure_threshold=3, recovery_timeout=30)
configure_service_circuit_breaker("llm_service", failure_threshold=3, recovery_timeout=30)
configure_service_circuit_breaker("mapping_service", failure_threshold=5, recovery_timeout=60)
configure_service_circuit_breaker("grading_service", failure_threshold=5, recovery_timeout=60)
