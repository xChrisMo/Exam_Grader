"""
Circuit Breaker Pattern Implementation for External API Calls.

This module provides a circuit breaker to prevent cascading failures
when external services (LLM, OCR) are unavailable or slow.
"""

import time
import threading
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Features:
    - Automatic failure detection
    - Fast-fail when service is down
    - Automatic recovery testing
    - Thread-safe operation
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit breaker (for logging)
            config: Configuration settings
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.info(f"Circuit breaker '{name}' initialized")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original function exceptions
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable for {time.time() - self.last_failure_time:.1f}s"
                    )

            # Execute the function
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Record success
                self._record_success(execution_time)
                return result

            except Exception as e:
                # Record failure
                self._record_failure(e)
                raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout

    def _record_success(self, execution_time: float):
        """Record successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

        logger.debug(
            f"Circuit breaker '{self.name}' success (took {execution_time:.2f}s)"
        )

    def _record_failure(self, exception: Exception):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery, go back to open
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' failed during recovery, back to OPEN"
            )
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures. "
                    f"Last error: {str(exception)}"
                )

        logger.debug(
            f"Circuit breaker '{self.name}' failure #{self.failure_count}: {str(exception)}"
        )

    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "time_since_last_failure": (
                    time.time() - self.last_failure_time
                    if self.last_failure_time
                    else 0
                ),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                },
            }

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")

def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """
    Decorator for applying circuit breaker to functions.

    Args:
        name: Circuit breaker name
        config: Configuration settings

    Returns:
        Decorated function
    """
    breaker = CircuitBreaker(name, config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator

llm_circuit_breaker = CircuitBreaker(
    "llm_service",
    CircuitBreakerConfig(
        failure_threshold=3, recovery_timeout=30, success_threshold=2, timeout=30.0
    ),
)

ocr_circuit_breaker = CircuitBreaker(
    "ocr_service",
    CircuitBreakerConfig(
        failure_threshold=5, recovery_timeout=60, success_threshold=3, timeout=60.0
    ),
)

def get_all_circuit_breakers() -> dict:
    """Get status of all circuit breakers."""
    return {
        "llm": llm_circuit_breaker.get_state(),
        "ocr": ocr_circuit_breaker.get_state(),
    }
