"""
Retry Manager - Implements exponential backoff retry logic for transient failures.

This module provides sophisticated retry mechanisms with exponential backoff,
jitter, and circuit breaker patterns for handling transient failures in processing operations.
"""

import time
from datetime import datetime, timedelta, timezone
import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from src.config.processing_config import ProcessingConfigManager
from utils.logger import logger

@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_multiplier: float = 1.5

class RetryStrategy(Enum):
    """Available retry strategies."""

    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"

class RetryDecision(Enum):
    """Retry decision outcomes."""

    RETRY = "retry"
    STOP = "stop"
    FALLBACK = "fallback"

@dataclass
class RetryAttempt:
    """Information about a retry attempt."""

    attempt_number: int
    delay: float
    timestamp: datetime
    error: Optional[str] = None
    success: bool = False
    execution_time: float = 0.0

@dataclass
class RetryResult:
    """Result of a retry operation."""

    success: bool
    data: Any = None
    total_attempts: int = 0
    total_time: float = 0.0
    attempts: List[RetryAttempt] = None
    final_error: Optional[str] = None
    strategy_used: Optional[RetryStrategy] = None

class RetryManager:
    """
    Manages retry logic with exponential backoff for transient failures.
    """

    def __init__(self):
        self.retry_configs: Dict[str, RetryConfig] = {}
        self.retry_statistics: Dict[str, Dict[str, Any]] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # Initialize processing configuration manager
        self._config_manager = ProcessingConfigManager()

        self._setup_configs_from_manager()

    def _setup_configs_from_manager(self):
        """Set up retry configurations from ProcessingConfigManager."""
        try:
            services = [
                "ocr_processing",
                "llm_processing",
                "file_processing",
                "mapping_service",
                "grading_service",
            ]

            for service in services:
                config_data = self._config_manager.get_retry_policy(service)
                self.retry_configs[service] = RetryConfig(
                    max_attempts=config_data.max_attempts,
                    base_delay=config_data.base_delay,
                    max_delay=config_data.max_delay,
                    exponential_base=config_data.exponential_base,
                    jitter=config_data.jitter,
                    backoff_multiplier=config_data.backoff_multiplier,
                )

            # Set up additional common operations
            default_config = self._config_manager.get_retry_policy("default")
            self.retry_configs.update(
                {
                    "database_operations": RetryConfig(
                        max_attempts=5,
                        base_delay=0.1,
                        max_delay=10.0,
                        exponential_base=2.0,
                        jitter=True,
                        backoff_multiplier=2.0,
                    ),
                    "api_calls": RetryConfig(
                        max_attempts=4,
                        base_delay=1.0,
                        max_delay=30.0,
                        exponential_base=2.0,
                        jitter=True,
                        backoff_multiplier=2.0,
                    ),
                    "default": RetryConfig(
                        max_attempts=default_config.max_attempts,
                        base_delay=default_config.base_delay,
                        max_delay=default_config.max_delay,
                        exponential_base=default_config.exponential_base,
                        jitter=default_config.jitter,
                        backoff_multiplier=default_config.backoff_multiplier,
                    ),
                }
            )

            logger.info("Retry configurations loaded from ProcessingConfigManager")

        except Exception as e:
            logger.error(
                f"Failed to load retry configurations from config manager: {e}"
            )
            # Fallback to default configurations
            self._setup_default_configs()

    def _setup_default_configs(self):
        """Set up default retry configurations for common operations."""

        self.retry_configs.update(
            {
                "ocr_processing": RetryConfig(
                    max_attempts=3,
                    base_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=1.5,
                ),
                "llm_processing": RetryConfig(
                    max_attempts=5,
                    base_delay=0.5,
                    max_delay=60.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=2.0,
                ),
                "file_processing": RetryConfig(
                    max_attempts=2,
                    base_delay=2.0,
                    max_delay=20.0,
                    exponential_base=1.5,
                    jitter=False,
                    backoff_multiplier=1.2,
                ),
                "mapping_service": RetryConfig(
                    max_attempts=3,
                    base_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=1.5,
                ),
                "grading_service": RetryConfig(
                    max_attempts=3,
                    base_delay=1.5,
                    max_delay=45.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=1.8,
                ),
                "database_operations": RetryConfig(
                    max_attempts=5,
                    base_delay=0.1,
                    max_delay=10.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=2.0,
                ),
                "api_calls": RetryConfig(
                    max_attempts=4,
                    base_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=2.0,
                ),
                "default": RetryConfig(
                    max_attempts=3,
                    base_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
                    jitter=True,
                    backoff_multiplier=1.5,
                ),
            }
        )

    def register_retry_config(self, operation: str, config: RetryConfig):
        """Register retry configuration for an operation."""
        self.retry_configs[operation] = config
        logger.info(f"Registered retry config for '{operation}': {config}")

    def retry_with_backoff(
        self,
        operation: str,
        func: Callable,
        *args,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        **kwargs,
    ) -> RetryResult:
        """
        Execute function with retry and exponential backoff.

        Args:
            operation: Name of the operation for configuration lookup
            func: Function to execute
            *args: Arguments for the function
            strategy: Retry strategy to use
            **kwargs: Keyword arguments for the function

        Returns:
            RetryResult with execution results
        """
        config = self.retry_configs.get(operation, self.retry_configs["default"])
        start_time = time.time()
        attempts = []
        last_error = None

        # Check circuit breaker
        if self._is_circuit_breaker_open(operation):
            logger.warning(f"Circuit breaker open for operation: {operation}")
            return RetryResult(
                success=False,
                total_attempts=0,
                total_time=0.0,
                attempts=[],
                final_error="Circuit breaker is open",
                strategy_used=strategy,
            )

        for attempt_num in range(1, config.max_attempts + 1):
            attempt_start = time.time()

            try:
                logger.debug(
                    f"Attempt {attempt_num}/{config.max_attempts} for operation: {operation}"
                )

                result = func(*args, **kwargs)
                execution_time = time.time() - attempt_start

                # Record successful attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                    execution_time=execution_time,
                )
                attempts.append(attempt)

                # Update statistics
                self._update_retry_statistics(
                    operation, attempt_num, True, time.time() - start_time
                )

                # Close circuit breaker on success
                self._close_circuit_breaker(operation)

                logger.info(
                    f"Operation '{operation}' succeeded on attempt {attempt_num}"
                )

                return RetryResult(
                    success=True,
                    data=result,
                    total_attempts=attempt_num,
                    total_time=time.time() - start_time,
                    attempts=attempts,
                    strategy_used=strategy,
                )

            except Exception as e:
                execution_time = time.time() - attempt_start
                last_error = e

                logger.warning(
                    f"Attempt {attempt_num}/{config.max_attempts} failed for operation '{operation}': {e}"
                )

                if not self._is_retryable_error(e):
                    logger.info(f"Non-retryable error for operation '{operation}': {e}")

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

                    break

                if attempt_num < config.max_attempts:
                    delay = self._calculate_delay(attempt_num, config, strategy)

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=delay,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

                    logger.info(
                        f"Retrying operation '{operation}' in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

        # All attempts failed
        total_time = time.time() - start_time

        # Update statistics
        self._update_retry_statistics(operation, config.max_attempts, False, total_time)

        # Update circuit breaker
        self._update_circuit_breaker(operation, False)

        logger.error(
            f"Operation '{operation}' failed after {config.max_attempts} attempts"
        )

        return RetryResult(
            success=False,
            total_attempts=config.max_attempts,
            total_time=total_time,
            attempts=attempts,
            final_error=str(last_error) if last_error else "Unknown error",
            strategy_used=strategy,
        )

    async def retry_with_backoff_async(
        self,
        operation: str,
        func: Callable,
        *args,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        **kwargs,
    ) -> RetryResult:
        """
        Execute async function with retry and exponential backoff.
        """
        config = self.retry_configs.get(operation, self.retry_configs["default"])
        start_time = time.time()
        attempts = []
        last_error = None

        # Check circuit breaker
        if self._is_circuit_breaker_open(operation):
            logger.warning(f"Circuit breaker open for operation: {operation}")
            return RetryResult(
                success=False,
                total_attempts=0,
                total_time=0.0,
                attempts=[],
                final_error="Circuit breaker is open",
                strategy_used=strategy,
            )

        for attempt_num in range(1, config.max_attempts + 1):
            attempt_start = time.time()

            try:
                logger.debug(
                    f"Async attempt {attempt_num}/{config.max_attempts} for operation: {operation}"
                )

                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                execution_time = time.time() - attempt_start

                # Record successful attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                    execution_time=execution_time,
                )
                attempts.append(attempt)

                # Update statistics
                self._update_retry_statistics(
                    operation, attempt_num, True, time.time() - start_time
                )

                # Close circuit breaker on success
                self._close_circuit_breaker(operation)

                logger.info(
                    f"Async operation '{operation}' succeeded on attempt {attempt_num}"
                )

                return RetryResult(
                    success=True,
                    data=result,
                    total_attempts=attempt_num,
                    total_time=time.time() - start_time,
                    attempts=attempts,
                    strategy_used=strategy,
                )

            except Exception as e:
                execution_time = time.time() - attempt_start
                last_error = e

                logger.warning(
                    f"Async attempt {attempt_num}/{config.max_attempts} failed for operation '{operation}': {e}"
                )

                if not self._is_retryable_error(e):
                    logger.info(
                        f"Non-retryable error for async operation '{operation}': {e}"
                    )

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

                    break

                if attempt_num < config.max_attempts:
                    delay = self._calculate_delay(attempt_num, config, strategy)

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=delay,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

                    logger.info(
                        f"Retrying async operation '{operation}' in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        success=False,
                        execution_time=execution_time,
                    )
                    attempts.append(attempt)

        # All attempts failed
        total_time = time.time() - start_time

        # Update statistics
        self._update_retry_statistics(operation, config.max_attempts, False, total_time)

        # Update circuit breaker
        self._update_circuit_breaker(operation, False)

        logger.error(
            f"Async operation '{operation}' failed after {config.max_attempts} attempts"
        )

        return RetryResult(
            success=False,
            total_attempts=config.max_attempts,
            total_time=total_time,
            attempts=attempts,
            final_error=str(last_error) if last_error else "Unknown error",
            strategy_used=strategy,
        )

    def _calculate_delay(
        self, attempt_num: int, config: RetryConfig, strategy: RetryStrategy
    ) -> float:
        """Calculate delay for next retry attempt."""

        if strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.exponential_base ** (attempt_num - 1))
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt_num
        elif strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = config.base_delay * self._fibonacci(attempt_num)
        else:
            # Default to exponential backoff
            delay = config.base_delay * (config.exponential_base ** (attempt_num - 1))

        # Apply backoff multiplier
        delay *= config.backoff_multiplier

        # Cap at maximum delay
        delay = min(delay, config.max_delay)

        if config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)  # Minimum 0.1 second delay

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return n

        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b

        return b

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Network and temporary errors are retryable
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "rate limit",
            "server error",
            "429",
            "500",
            "502",
            "503",
            "504",
            "unavailable",
            "busy",
            "overloaded",
        ]

        # Authentication and client errors are not retryable
        non_retryable_patterns = [
            "authentication",
            "unauthorized",
            "401",
            "403",
            "invalid_request_error",
            "permission",
            "not found",
            "404",
            "bad request",
            "400",
            "validation",
            "malformed",
        ]

        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False

        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Check specific exception types
        retryable_types = [
            "ConnectionError",
            "TimeoutError",
            "ServiceUnavailableError",
            "TemporaryFailure",
            "RateLimitError",
        ]

        if error_type in retryable_types:
            return True

        return True

    def _is_circuit_breaker_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for an operation."""
        if operation not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[operation]

        if (
            breaker["state"] == "open"
            and datetime.now(timezone.utc) > breaker["reset_time"]
        ):
            breaker["state"] = "half_open"
            logger.info(f"Circuit breaker for '{operation}' moved to half-open state")

        return breaker["state"] == "open"

    def _update_circuit_breaker(self, operation: str, success: bool):
        """Update circuit breaker state."""
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = {
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
                "reset_time": None,
                "failure_threshold": 5,
                "reset_timeout_minutes": 5,
            }

        breaker = self.circuit_breakers[operation]

        if success:
            breaker["success_count"] += 1
            breaker["failure_count"] = 0  # Reset failure count on success
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                logger.info(
                    f"Circuit breaker for '{operation}' closed after successful execution"
                )
        else:
            breaker["failure_count"] += 1
            breaker["last_failure_time"] = datetime.now(timezone.utc)

            if breaker["failure_count"] >= breaker["failure_threshold"]:
                breaker["state"] = "open"
                breaker["reset_time"] = datetime.now(timezone.utc) + timedelta(
                    minutes=breaker["reset_timeout_minutes"]
                )
                logger.warning(
                    f"Circuit breaker for '{operation}' opened due to {breaker['failure_count']} consecutive failures"
                )

    def _close_circuit_breaker(self, operation: str):
        """Close circuit breaker on successful execution."""
        if operation in self.circuit_breakers:
            self.circuit_breakers[operation]["state"] = "closed"
            self.circuit_breakers[operation]["failure_count"] = 0

    def _update_retry_statistics(
        self, operation: str, attempts: int, success: bool, total_time: float
    ):
        """Update retry statistics for an operation."""
        if operation not in self.retry_statistics:
            self.retry_statistics[operation] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_attempts": 0,
                "total_time": 0.0,
                "average_attempts": 0.0,
                "average_time": 0.0,
                "success_rate": 0.0,
            }

        stats = self.retry_statistics[operation]
        stats["total_operations"] += 1
        stats["total_attempts"] += attempts
        stats["total_time"] += total_time

        if success:
            stats["successful_operations"] += 1
        else:
            stats["failed_operations"] += 1

        # Update averages
        stats["average_attempts"] = stats["total_attempts"] / stats["total_operations"]
        stats["average_time"] = stats["total_time"] / stats["total_operations"]
        stats["success_rate"] = (
            stats["successful_operations"] / stats["total_operations"]
        )

    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics for all operations."""
        return self.retry_statistics.copy()

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for all operations."""
        status = {}

        for operation, breaker in self.circuit_breakers.items():
            status[operation] = {
                "state": breaker["state"],
                "failure_count": breaker["failure_count"],
                "success_count": breaker["success_count"],
                "last_failure_time": (
                    breaker["last_failure_time"].isoformat()
                    if breaker["last_failure_time"]
                    else None
                ),
                "reset_time": (
                    breaker["reset_time"].isoformat() if breaker["reset_time"] else None
                ),
                "failure_threshold": breaker["failure_threshold"],
            }

        return status

    def reset_circuit_breaker(self, operation: str):
        """Manually reset circuit breaker for an operation."""
        if operation in self.circuit_breakers:
            self.circuit_breakers[operation]["state"] = "closed"
            self.circuit_breakers[operation]["failure_count"] = 0
            self.circuit_breakers[operation]["reset_time"] = None
            logger.info(f"Circuit breaker for '{operation}' manually reset")
        else:
            logger.warning(f"No circuit breaker found for operation: {operation}")

    def clear_statistics(self):
        """Clear all retry statistics."""
        self.retry_statistics.clear()
        logger.info("Retry statistics cleared")

    def with_retry(
        self,
        operation: str,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    ):
        """Decorator for adding retry logic to functions."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = self.retry_with_backoff(
                    operation, func, *args, strategy=strategy, **kwargs
                )
                if result.success:
                    return result.data
                else:
                    raise Exception(result.final_error)

            return wrapper

        return decorator

    def with_retry_async(
        self,
        operation: str,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    ):
        """Decorator for adding retry logic to async functions."""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = await self.retry_with_backoff_async(
                    operation, func, *args, strategy=strategy, **kwargs
                )
                if result.success:
                    return result.data
                else:
                    raise Exception(result.final_error)

            return wrapper

        return decorator

# Global instance
retry_manager = RetryManager()
