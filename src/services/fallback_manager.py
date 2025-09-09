"""
Fallback Manager - Manages graceful degradation when services fail.

This module provides comprehensive fallback mechanisms for processing operations,
allowing the system to continue functioning even when primary services are unavailable.
"""

import time
from datetime import datetime, timedelta, timezone
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import logger

class FallbackPriority(Enum):
    """Priority levels for fallback methods."""

    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3
    EMERGENCY = 4

@dataclass
class FallbackMethod:
    """Definition of a fallback method."""

    name: str
    function: Callable
    priority: FallbackPriority
    timeout: Optional[float] = None
    enabled: bool = True
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0

@dataclass
class FallbackResult:
    """Result of a fallback operation."""

    success: bool
    data: Any = None
    method_used: Optional[str] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FallbackManager:
    """
    Manages fallback strategies and graceful degradation for processing operations.
    """

    def __init__(self):
        self.fallback_methods: Dict[str, List[FallbackMethod]] = {}
        self.cached_results: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)  # Default cache TTL
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}

        # Initialize default fallback methods
        self._setup_default_fallbacks()

    def _setup_default_fallbacks(self):
        """Set up default fallback methods for common operations."""

        # OCR processing fallbacks
        # Note: HandwritingOCR API is handled directly in ConsolidatedOCRService
        # These are true fallback methods when the API fails
        self.register_fallback(
            "ocr_processing",
            "tesseract_ocr",
            self._tesseract_fallback,
            FallbackPriority.SECONDARY,  # Changed from PRIMARY to SECONDARY
        )
        self.register_fallback(
            "ocr_processing",
            "easyocr_fallback",
            self._easyocr_fallback,
            FallbackPriority.TERTIARY,  # Changed from SECONDARY to TERTIARY
        )
        self.register_fallback(
            "ocr_processing",
            "basic_text_extraction",
            self._basic_text_extraction,
            FallbackPriority.EMERGENCY,  # Changed from TERTIARY to EMERGENCY
        )

        # LLM processing fallbacks - REMOVED: Only LLM extraction should be used
        # No fallbacks for LLM processing to ensure quality

        # File processing fallbacks
        self.register_fallback(
            "file_processing",
            "alternative_library",
            self._alternative_file_processing,
            FallbackPriority.PRIMARY,
        )
        self.register_fallback(
            "file_processing",
            "basic_text_read",
            self._basic_file_read,
            FallbackPriority.SECONDARY,
        )

        # Mapping service fallbacks
        self.register_fallback(
            "mapping_service",
            "keyword_matching",
            self._keyword_mapping,
            FallbackPriority.PRIMARY,
        )
        self.register_fallback(
            "mapping_service",
            "simple_mapping",
            self._simple_mapping,
            FallbackPriority.SECONDARY,
        )

        # Grading service fallbacks
        self.register_fallback(
            "grading_service",
            "cached_grading",
            self._cached_grading,
            FallbackPriority.PRIMARY,
        )
        self.register_fallback(
            "grading_service",
            "rule_based_grading",
            self._rule_based_grading,
            FallbackPriority.SECONDARY,
        )
        self.register_fallback(
            "grading_service",
            "length_based_grading",
            self._length_based_grading,
            FallbackPriority.TERTIARY,
        )

    def register_fallback(
        self,
        operation: str,
        name: str,
        function: Callable,
        priority: FallbackPriority,
        timeout: Optional[float] = None,
        enabled: bool = True,
    ):
        """Register a fallback method for an operation."""

        if operation not in self.fallback_methods:
            self.fallback_methods[operation] = []

        fallback_method = FallbackMethod(
            name=name,
            function=function,
            priority=priority,
            timeout=timeout,
            enabled=enabled,
        )

        self.fallback_methods[operation].append(fallback_method)

        # Sort by priority
        self.fallback_methods[operation].sort(key=lambda x: x.priority.value)

        logger.info(
            f"Registered fallback method '{name}' for operation '{operation}' with priority {priority.value}"
        )

    def execute_with_fallback(
        self, operation: str, primary_func: Callable, *args, **kwargs
    ) -> FallbackResult:
        """
        Execute operation with fallback support.

        Args:
            operation: Name of the operation
            primary_func: Primary function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            FallbackResult with execution results
        """
        start_time = time.time()

        # Try primary function first
        try:
            logger.debug(f"Executing primary function for operation: {operation}")
            result = primary_func(*args, **kwargs)

            execution_time = time.time() - start_time

            return FallbackResult(
                success=True,
                data=result,
                method_used="primary",
                execution_time=execution_time,
            )

        except Exception as primary_error:
            logger.warning(f"Primary function failed for {operation}: {primary_error}")

            # Try fallback methods
            return self._execute_fallbacks(operation, primary_error, *args, **kwargs)

    async def execute_with_fallback_async(
        self, operation: str, primary_func: Callable, *args, **kwargs
    ) -> FallbackResult:
        """
        Execute operation with fallback support (async version).
        """
        start_time = time.time()

        # Try primary function first
        try:
            logger.debug(f"Executing primary async function for operation: {operation}")

            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = primary_func(*args, **kwargs)

            execution_time = time.time() - start_time

            return FallbackResult(
                success=True,
                data=result,
                method_used="primary",
                execution_time=execution_time,
            )

        except Exception as primary_error:
            logger.warning(
                f"Primary async function failed for {operation}: {primary_error}"
            )

            # Try fallback methods
            return await self._execute_fallbacks_async(
                operation, primary_error, *args, **kwargs
            )

    def _execute_fallbacks(
        self, operation: str, primary_error: Exception, *args, **kwargs
    ) -> FallbackResult:
        """Execute fallback methods in priority order."""

        fallback_methods = self.fallback_methods.get(operation, [])

        if not fallback_methods:
            logger.error(f"No fallback methods registered for operation: {operation}")
            return FallbackResult(
                success=False,
                error=f"No fallback methods available for {operation}: {str(primary_error)}",
            )

        last_error = primary_error

        for method in fallback_methods:
            if not method.enabled:
                continue

            # Check circuit breaker
            if self._is_circuit_breaker_open(operation, method.name):
                logger.debug(
                    f"Circuit breaker open for {operation}.{method.name}, skipping"
                )
                continue

            try:
                logger.info(
                    f"Trying fallback method '{method.name}' for operation '{operation}'"
                )

                start_time = time.time()

                if method.timeout:
                    result = self._execute_with_timeout(
                        method.function, method.timeout, *args, **kwargs
                    )
                else:
                    result = method.function(*args, **kwargs)

                execution_time = time.time() - start_time

                # Update method statistics
                method.success_count += 1
                method.last_used = datetime.now(timezone.utc)
                method.success_rate = method.success_count / (
                    method.success_count + method.failure_count
                )

                # Close circuit breaker on success
                self._close_circuit_breaker(operation, method.name)

                logger.info(
                    f"Fallback method '{method.name}' succeeded for operation '{operation}'"
                )

                return FallbackResult(
                    success=True,
                    data=result,
                    method_used=method.name,
                    execution_time=execution_time,
                    metadata={
                        "fallback_priority": method.priority.value,
                        "method_success_rate": method.success_rate,
                    },
                )

            except Exception as fallback_error:
                logger.warning(
                    f"Fallback method '{method.name}' failed: {fallback_error}"
                )

                # Update method statistics
                method.failure_count += 1
                method.success_rate = method.success_count / (
                    method.success_count + method.failure_count
                )

                # Update circuit breaker
                self._update_circuit_breaker(operation, method.name, False)

                last_error = fallback_error
                continue

        # All fallback methods failed
        logger.error(f"All fallback methods failed for operation: {operation}")
        return FallbackResult(
            success=False,
            error=f"All fallback methods failed. Last error: {str(last_error)}",
        )

    async def _execute_fallbacks_async(
        self, operation: str, primary_error: Exception, *args, **kwargs
    ) -> FallbackResult:
        """Execute fallback methods in priority order (async version)."""

        fallback_methods = self.fallback_methods.get(operation, [])

        if not fallback_methods:
            logger.error(f"No fallback methods registered for operation: {operation}")
            return FallbackResult(
                success=False,
                error=f"No fallback methods available for {operation}: {str(primary_error)}",
            )

        last_error = primary_error

        for method in fallback_methods:
            if not method.enabled:
                continue

            # Check circuit breaker
            if self._is_circuit_breaker_open(operation, method.name):
                logger.debug(
                    f"Circuit breaker open for {operation}.{method.name}, skipping"
                )
                continue

            try:
                logger.info(
                    f"Trying async fallback method '{method.name}' for operation '{operation}'"
                )

                start_time = time.time()

                if method.timeout:
                    if asyncio.iscoroutinefunction(method.function):
                        result = await asyncio.wait_for(
                            method.function(*args, **kwargs), timeout=method.timeout
                        )
                    else:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, method.function, *args, **kwargs
                            ),
                            timeout=method.timeout,
                        )
                else:
                    if asyncio.iscoroutinefunction(method.function):
                        result = await method.function(*args, **kwargs)
                    else:
                        result = method.function(*args, **kwargs)

                execution_time = time.time() - start_time

                # Update method statistics
                method.success_count += 1
                method.last_used = datetime.now(timezone.utc)
                method.success_rate = method.success_count / (
                    method.success_count + method.failure_count
                )

                # Close circuit breaker on success
                self._close_circuit_breaker(operation, method.name)

                logger.info(
                    f"Async fallback method '{method.name}' succeeded for operation '{operation}'"
                )

                return FallbackResult(
                    success=True,
                    data=result,
                    method_used=method.name,
                    execution_time=execution_time,
                    metadata={
                        "fallback_priority": method.priority.value,
                        "method_success_rate": method.success_rate,
                    },
                )

            except Exception as fallback_error:
                logger.warning(
                    f"Async fallback method '{method.name}' failed: {fallback_error}"
                )

                # Update method statistics
                method.failure_count += 1
                method.success_rate = method.success_count / (
                    method.success_count + method.failure_count
                )

                # Update circuit breaker
                self._update_circuit_breaker(operation, method.name, False)

                last_error = fallback_error
                continue

        # All fallback methods failed
        logger.error(f"All async fallback methods failed for operation: {operation}")
        return FallbackResult(
            success=False,
            error=f"All fallback methods failed. Last error: {str(last_error)}",
        )

    def _execute_with_timeout(
        self, func: Callable, timeout: float, *args, **kwargs
    ) -> Any:
        """Execute function with timeout."""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Function execution timed out after {timeout} seconds")

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel timeout
            return result
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    def _is_circuit_breaker_open(self, operation: str, method_name: str) -> bool:
        """Check if circuit breaker is open for a method."""
        key = f"{operation}.{method_name}"

        if key not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[key]

        if (
            breaker["state"] == "open"
            and datetime.now(timezone.utc) > breaker["reset_time"]
        ):
            breaker["state"] = "half_open"
            logger.info(f"Circuit breaker for {key} moved to half-open state")

        return breaker["state"] == "open"

    def _update_circuit_breaker(self, operation: str, method_name: str, success: bool):
        """Update circuit breaker state."""
        key = f"{operation}.{method_name}"

        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
                "reset_time": None,
            }

        breaker = self.circuit_breakers[key]

        if success:
            breaker["success_count"] += 1
            breaker["failure_count"] = 0  # Reset failure count on success
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                logger.info(
                    f"Circuit breaker for {key} closed after successful execution"
                )
        else:
            breaker["failure_count"] += 1
            breaker["last_failure_time"] = datetime.now(timezone.utc)

            if breaker["failure_count"] >= 5:  # Configurable threshold
                breaker["state"] = "open"
                breaker["reset_time"] = datetime.now(timezone.utc) + timedelta(
                    minutes=5
                )  # Configurable reset time
                logger.warning(
                    f"Circuit breaker for {key} opened due to repeated failures"
                )

    def _close_circuit_breaker(self, operation: str, method_name: str):
        """Close circuit breaker on successful execution."""
        key = f"{operation}.{method_name}"

        if key in self.circuit_breakers:
            self.circuit_breakers[key]["state"] = "closed"
            self.circuit_breakers[key]["failure_count"] = 0

    # Default fallback method implementations

    def _tesseract_fallback(self, file_path: str, **kwargs) -> str:
        """Tesseract OCR fallback method."""
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except ImportError:
            raise Exception("Tesseract not available")
        except Exception as e:
            raise Exception(f"Tesseract OCR failed: {e}")

    def _easyocr_fallback(self, file_path: str, **kwargs) -> str:
        """EasyOCR fallback method."""
        try:
            import easyocr

            reader = easyocr.Reader(["en"])
            results = reader.readtext(file_path)
            text = " ".join([result[1] for result in results])
            return text.strip()
        except ImportError:
            raise Exception("EasyOCR not available")
        except Exception as e:
            raise Exception(f"EasyOCR failed: {e}")

    def _basic_text_extraction(self, file_path: str, **kwargs) -> str:
        """Basic text extraction fallback."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
        except Exception as e:
            raise Exception(f"Basic text extraction failed: {e}")

    # LLM fallback methods removed - only LLM extraction should be used

    def _alternative_file_processing(self, file_path: str, **kwargs) -> str:
        """Alternative file processing method."""
        try:
            # Try different file reading approaches
            encodings = ["utf-8", "latin-1", "cp1252"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue

            raise Exception("Could not read file with any encoding")
        except Exception as e:
            raise Exception(f"Alternative file processing failed: {e}")

    def _basic_file_read(self, file_path: str, **kwargs) -> str:
        """Basic file reading fallback."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise Exception(f"Basic file read failed: {e}")

    def _keyword_mapping(
        self, guide_text: str, submission_text: str, **kwargs
    ) -> List[Dict]:
        """Keyword-based mapping fallback."""
        # Simple keyword matching
        import re

        questions = re.findall(
            r"(?:Question|Q)\s*\d+[:.]\s*([^?]+\?)", guide_text, re.IGNORECASE
        )

        mappings = []
        for i, question in enumerate(questions):
            # Simple keyword matching
            keywords = question.lower().split()[:3]  # First 3 words as keywords

            mapping = {
                "question_number": i + 1,
                "question_text": question,
                "student_answer": submission_text[:200],  # First 200 chars
                "confidence": 0.6,
                "method": "keyword_matching",
            }
            mappings.append(mapping)

        return mappings

    def _simple_mapping(
        self, guide_text: str, submission_text: str, **kwargs
    ) -> List[Dict]:
        """Simple mapping fallback."""
        # Very basic mapping - split submission into equal parts
        words = submission_text.split()
        questions_count = min(5, len(words) // 20)  # Assume 1 question per 20 words

        mappings = []
        for i in range(questions_count):
            start_idx = i * (len(words) // questions_count)
            end_idx = (i + 1) * (len(words) // questions_count)
            answer_text = " ".join(words[start_idx:end_idx])

            mapping = {
                "question_number": i + 1,
                "question_text": f"Question {i + 1}",
                "student_answer": answer_text,
                "confidence": 0.4,
                "method": "simple_mapping",
            }
            mappings.append(mapping)

        return mappings

    def _cached_grading(self, submission_content: str, **kwargs) -> Dict[str, Any]:
        """Cached grading fallback."""
        cache_key = f"grading_{hash(submission_content)}"

        if cache_key in self.cached_results:
            cached_data, timestamp = self.cached_results[cache_key]
            if datetime.now(timezone.utc) - timestamp < self.cache_ttl:
                logger.info("Using cached grading result")
                return cached_data

        raise Exception("No cached grading result available")

    def _rule_based_grading(self, submission_content: str, **kwargs) -> Dict[str, Any]:
        """Rule-based grading fallback."""
        word_count = len(submission_content.split())
        len(submission_content)

        # Simple scoring based on content length and structure
        base_score = min(80, word_count * 2)  # 2 points per word, max 80

        if "." in submission_content:
            base_score += 5
        if any(
            word in submission_content.lower()
            for word in ["because", "therefore", "however"]
        ):
            base_score += 5

        score = min(100, base_score)

        return {
            "total_score": score,
            "max_score": 100,
            "feedback": f"Rule-based grading: {word_count} words analyzed. Score based on content length and structure.",
            "grading_method": "rule_based",
        }

    def _length_based_grading(
        self, submission_content: str, **kwargs
    ) -> Dict[str, Any]:
        """Length-based grading fallback."""
        word_count = len(submission_content.split())

        # Very simple length-based scoring
        if word_count > 100:
            score = 85
        elif word_count > 50:
            score = 70
        elif word_count > 20:
            score = 55
        else:
            score = 40

        return {
            "total_score": score,
            "max_score": 100,
            "feedback": f"Length-based grading: {word_count} words. Basic scoring applied.",
            "grading_method": "length_based",
        }

    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get statistics about fallback method usage."""
        stats = {}

        for operation, methods in self.fallback_methods.items():
            operation_stats = {
                "total_methods": len(methods),
                "enabled_methods": len([m for m in methods if m.enabled]),
                "methods": [],
            }

            for method in methods:
                method_stats = {
                    "name": method.name,
                    "priority": method.priority.value,
                    "enabled": method.enabled,
                    "success_rate": method.success_rate,
                    "success_count": method.success_count,
                    "failure_count": method.failure_count,
                    "last_used": (
                        method.last_used.isoformat() if method.last_used else None
                    ),
                }
                operation_stats["methods"].append(method_stats)

            stats[operation] = operation_stats

        return stats

    def enable_fallback_method(self, operation: str, method_name: str):
        """Enable a specific fallback method."""
        methods = self.fallback_methods.get(operation, [])
        for method in methods:
            if method.name == method_name:
                method.enabled = True
                logger.info(
                    f"Enabled fallback method '{method_name}' for operation '{operation}'"
                )
                return

        logger.warning(
            f"Fallback method '{method_name}' not found for operation '{operation}'"
        )

    def disable_fallback_method(self, operation: str, method_name: str):
        """Disable a specific fallback method."""
        methods = self.fallback_methods.get(operation, [])
        for method in methods:
            if method.name == method_name:
                method.enabled = False
                logger.info(
                    f"Disabled fallback method '{method_name}' for operation '{operation}'"
                )
                return

        logger.warning(
            f"Fallback method '{method_name}' not found for operation '{operation}'"
        )

    def clear_cache(self):
        """Clear cached results."""
        self.cached_results.clear()
        logger.info("Fallback manager cache cleared")

    def cache_result(self, key: str, result: Any, ttl: Optional[timedelta] = None):
        """Cache a result for future use."""
        if ttl is None:
            ttl = self.cache_ttl

        self.cached_results[key] = (result, datetime.now(timezone.utc))
        logger.debug(f"Cached result with key: {key}")

# Global instance
fallback_manager = FallbackManager()
