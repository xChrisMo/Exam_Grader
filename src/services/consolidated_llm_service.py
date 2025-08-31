"""Consolidated LLM Service merging LLMService and EnhancedLLMService.

This module provides a unified LLM service that combines the functionality of both
LLMService and EnhancedLLMService with integration to the base service architecture.
"""

import json
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from packaging import version

from src.config.unified_config import config
from src.services.base_service import BaseService, ServiceStatus
from src.services.enhanced_logging_service import LogCategory, enhanced_logging_service
from src.services.fallback_manager import fallback_manager
from src.services.monitoring.monitoring_service import monitoring_service
from src.services.core.error_service import error_service, ErrorContext
from utils.logger import logger

# Load environment variables
load_dotenv()


class LLMServiceError(Exception):
    """Exception raised for errors in the LLM service."""

    def __init__(
        self, message: str, error_code: str = None, original_error: Exception = None
    ):
        """Initialize LLM service error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error

    def __str__(self):
        """Return string representation of the error."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class RateLimitManager:
    """Manages rate limiting for API calls"""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 3600):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = []
        self.hour_requests = []
        self.lock = threading.Lock()

    def can_make_request(self) -> bool:
        """Check if a request can be made within rate limits"""
        current_time = time.time()

        with self.lock:
            # Clean old requests
            self.minute_requests = [
                t for t in self.minute_requests if current_time - t < 60
            ]
            self.hour_requests = [
                t for t in self.hour_requests if current_time - t < 3600
            ]

            # Check limits
            if len(self.minute_requests) >= self.requests_per_minute:
                return False
            if len(self.hour_requests) >= self.requests_per_hour:
                return False

            return True

    def record_request(self):
        """Record a successful request"""
        current_time = time.time()
        with self.lock:
            self.minute_requests.append(current_time)
            self.hour_requests.append(current_time)

    def get_wait_time(self) -> float:
        """Get time to wait before next request"""
        current_time = time.time()

        with self.lock:
            # Clean old requests
            self.minute_requests = [
                t for t in self.minute_requests if current_time - t < 60
            ]
            self.hour_requests = [
                t for t in self.hour_requests if current_time - t < 3600
            ]

            wait_times = []

            # Check minute limit
            if len(self.minute_requests) >= self.requests_per_minute:
                oldest_minute = min(self.minute_requests)
                wait_times.append(60 - (current_time - oldest_minute))

            # Check hour limit
            if len(self.hour_requests) >= self.requests_per_hour:
                oldest_hour = min(self.hour_requests)
                wait_times.append(3600 - (current_time - oldest_hour))

            return max(wait_times) if wait_times else 0


class ConnectionPool:
    """Connection pool for managing multiple API clients"""

    def __init__(self, pool_size: int = 5, api_key: str = None, base_url: str = None):
        self.pool_size = pool_size
        self.api_key = api_key
        self.base_url = base_url
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.created_connections = 0

        # Pre-populate pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool"""
        from openai import OpenAI

        for _ in range(self.pool_size):
            try:
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self.pool.put(client, block=False)
                self.created_connections += 1
            except Exception as e:
                logger.error(f"Failed to create connection for pool: {e}")
                break

    def get_connection(self, timeout: float = 5.0):
        """Get a connection from the pool"""
        try:
            return self.pool.get(timeout=timeout)
        except Empty:
            with self.lock:
                if self.created_connections < self.pool_size * 2:  # Allow some overflow
                    from openai import OpenAI

                    client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                    self.created_connections += 1
                    return client
            raise LLMServiceError(
                "Connection pool exhausted", error_code="POOL_EXHAUSTED"
            )

    def return_connection(self, connection):
        """Return a connection to the pool"""
        try:
            self.pool.put(connection, block=False)
        except:
            # Pool is full, connection will be garbage collected
            pass


@dataclass
class ResponseParsingStrategy:
    """Strategy for parsing LLM responses"""

    name: str
    parser_func: callable
    priority: int = 0  # Higher priority tried first


class ResponseParser:
    """Enhanced response parser with multiple fallback strategies"""

    def __init__(self):
        self.strategies = []
        self._setup_default_strategies()

    def _setup_default_strategies(self):
        """Setup default parsing strategies"""
        # JSON parsing strategies
        self.add_strategy(
            ResponseParsingStrategy(
                "direct_json", self._parse_direct_json, priority=100
            )
        )

        self.add_strategy(
            ResponseParsingStrategy(
                "extract_json", self._parse_extract_json, priority=90
            )
        )

        self.add_strategy(
            ResponseParsingStrategy(
                "clean_and_parse", self._parse_clean_json, priority=80
            )
        )

        # Fallback strategies
        self.add_strategy(
            ResponseParsingStrategy(
                "regex_extraction", self._parse_regex_extraction, priority=70
            )
        )

        self.add_strategy(
            ResponseParsingStrategy(
                "pattern_matching", self._parse_pattern_matching, priority=60
            )
        )

        self.add_strategy(
            ResponseParsingStrategy(
                "llm_restructure", self._parse_llm_restructure, priority=50
            )
        )

    def add_strategy(self, strategy: ResponseParsingStrategy):
        """Add a parsing strategy"""
        self.strategies.append(strategy)
        self.strategies.sort(key=lambda s: s.priority, reverse=True)

    def parse_response(
        self, response_text: str, expected_format: str = "json"
    ) -> Dict[str, Any]:
        """Parse response using multiple fallback strategies"""
        for strategy in self.strategies:
            try:
                result = strategy.parser_func(response_text, expected_format)
                if result:
                    logger.debug(
                        f"Successfully parsed response using strategy: {strategy.name}"
                    )
                    return result
            except Exception as e:
                logger.debug(f"Strategy {strategy.name} failed: {e}")
                continue

        # All strategies failed
        logger.error("All parsing strategies failed")
        return self._create_error_response(response_text)

    def _parse_direct_json(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Try direct JSON parsing"""
        if expected_format == "json":
            return json.loads(text.strip())
        return None

    def _parse_extract_json(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Extract JSON from text using regex"""
        import re

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match and expected_format == "json":
            return json.loads(json_match.group())
        return None

    def _parse_clean_json(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Clean text and try JSON parsing"""
        if expected_format != "json":
            return None

        # Remove common prefixes/suffixes
        cleaned = text.strip()
        prefixes = ["```json", "```", "JSON:", "Response:", "Result:"]
        suffixes = ["```"]

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()

        for suffix in suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()

        return json.loads(cleaned)

    def _parse_regex_extraction(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Extract structured data using regex patterns"""
        if expected_format == "grading":
            return self._extract_grading_data(text)
        return None

    def _parse_pattern_matching(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Use pattern matching for known formats"""
        if expected_format == "grading":
            return self._pattern_match_grading(text)
        return None

    def _parse_llm_restructure(
        self, text: str, expected_format: str
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to restructure response (placeholder)"""
        # This would use the LLM service itself to restructure
        # For now, return None to avoid circular dependency
        return None

    def _extract_grading_data(self, text: str) -> Dict[str, Any]:
        """Extract grading data using regex patterns"""
        import re

        # Score extraction patterns
        score_patterns = [
            r"score[:\s]*(\d+)",
            r"grade[:\s]*(\d+)",
            r"(\d+)\s*(?:points?|%|/100)",
        ]

        extracted_score = None
        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = int(match.group(1))
                    if 0 <= score <= 100:
                        extracted_score = score
                        break
                except ValueError:
                    continue

        if extracted_score is not None:
            return {
                "overall_grade": {
                    "score": extracted_score,
                    "feedback": "Extracted from text",
                },
                "criteria_scores": {
                    "accuracy": extracted_score,
                    "completeness": extracted_score,
                    "understanding": extracted_score,
                    "clarity": extracted_score,
                },
                "strengths": [],
                "areas_for_improvement": ["Manual review recommended"],
            }

        return None

    def _pattern_match_grading(self, text: str) -> Dict[str, Any]:
        """Pattern match for grading responses"""
        lines = text.split("\n")
        result = {
            "overall_grade": {"score": 0, "feedback": "Pattern matched"},
            "criteria_scores": {
                "accuracy": 0,
                "completeness": 0,
                "understanding": 0,
                "clarity": 0,
            },
            "strengths": [],
            "areas_for_improvement": [],
        }

        for line in lines:
            line = line.strip()
            if any(word in line.lower() for word in ["score", "grade", "points"]):
                # Try to extract numeric value
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    score = int(numbers[0])
                    if 0 <= score <= 100:
                        result["overall_grade"]["score"] = score
                        for key in result["criteria_scores"]:
                            result["criteria_scores"][key] = score
                        break

        return result if result["overall_grade"]["score"] > 0 else None

    def _create_error_response(self, original_text: str) -> Dict[str, Any]:
        """Create error response when all parsing fails"""
        return {
            "overall_grade": {
                "score": 0,
                "feedback": "PARSING FAILED - REQUIRES MANUAL REVIEW",
            },
            "criteria_scores": {
                "accuracy": 0,
                "completeness": 0,
                "understanding": 0,
                "clarity": 0,
            },
            "strengths": [],
            "areas_for_improvement": ["SYSTEM ERROR: Response parsing failed"],
            "requires_manual_review": True,
            "error_type": "parsing_error",
            "original_response": original_text[:500],  # Truncate for logging
        }


class ConsolidatedLLMService(BaseService):
    """Consolidated LLM service with enhanced functionality and base service integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = None,
        temperature: float = 0.0,  # Fully deterministic by default
        max_retries: int = 10,  # Increased retries
        retry_delay: float = 0.5,  # Reduced delay
        seed: Optional[int] = 42,  # Fixed seed for consistency
        deterministic: bool = True,  # Always use deterministic mode
        cache_size: int = 10000,  # Increased cache size
        cache_ttl: int = 86400,  # 24 hours cache
    ):
        """Initialize the consolidated LLM service.

        Args:
            api_key: DeepSeek API key (from environment if not provided)
            base_url: DeepSeek API base URL
            model: DeepSeek model name to use
            temperature: Sampling temperature (0.0 for most deterministic output)
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Delay between retry attempts in seconds
            seed: Random seed for deterministic outputs
            deterministic: Whether to use deterministic mode
            cache_size: Maximum number of cached responses
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__("consolidated_llm_service")

        # Configuration with proper fallback chain
        self.api_key = (api_key or 
                       os.getenv("LLM_API_KEY") or 
                       os.getenv("DEEPSEEK_API_KEY"))
        self.base_url = base_url
        self.model = (model or 
                     os.getenv("LLM_MODEL_NAME") or
                     (config.api.deepseek_model if hasattr(config, "api") else "deepseek-chat"))
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.seed = seed
        self.deterministic = deterministic

        # Cache configuration
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self._response_cache = {}
        self._cache_timestamps = {}
        self._cache_lock = threading.Lock()

        # Advanced retry configuration
        self.exponential_backoff = True
        self.max_backoff_delay = 60.0  # Maximum delay between retries
        self.jitter = True  # Add randomness to retry delays

        # Prompt optimization settings
        self.prompt_templates = {}
        self.response_validators = {}

        # MCP protocol support
        self.mcp_enabled = os.getenv("MCP_ENABLED", "False").lower() == "true"
        self.mcp_tools = []

        # Performance tracking
        self.request_count = 0
        self.total_tokens_used = 0
        self.average_response_time = 0.0

        # Enhanced features
        self.rate_limiter = RateLimitManager(
            requests_per_minute=int(os.getenv("LLM_REQUESTS_PER_MINUTE", "60")),
            requests_per_hour=int(os.getenv("LLM_REQUESTS_PER_HOUR", "3600")),
        )
        self.connection_pool = None
        self.response_parser = ResponseParser()

        # Client initialization
        self.client = None
        self.supports_json = False

        if self.api_key:
            try:
                pool_size = int(os.getenv("LLM_CONNECTION_POOL_SIZE", "3"))
                self.connection_pool = ConnectionPool(
                    pool_size=pool_size, api_key=self.api_key, base_url=self.base_url
                )
                logger.info(
                    f"Initialized LLM connection pool with {pool_size} connections"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize connection pool: {e}")

        # Set initial status based on API key availability - strict mode
        if not self.api_key:
            self.status = ServiceStatus.UNHEALTHY
            logger.error("LLM service requires API key - service unavailable")
        else:
            self.status = ServiceStatus.UNKNOWN
            # Initialize client synchronously
            self._initialize_client_sync()

    def _initialize_client_sync(self) -> bool:
        """Initialize the OpenAI client synchronously."""
        try:
            if not self.api_key:
                logger.warning("No API key available for LLM client initialization")
                return False

            # Initialize OpenAI client
            from openai import OpenAI

            # Get OpenAI version
            try:
                import openai

                openai_version_str = openai.__version__
                logger.info(f"Using OpenAI library version: {openai_version_str}")
            except Exception:
                logger.warning("Could not determine OpenAI library version")

            # Initialize client
            client_params = {"api_key": self.api_key, "base_url": self.base_url}
            self.client = OpenAI(**client_params)

            # Test basic connectivity (synchronous) - skip during fast startup
            skip_test = (
                os.getenv("SKIP_LLM_INIT_TEST", "False").lower() == "true"
                or os.getenv("FAST_STARTUP", "False").lower() == "true"
            )

            if not skip_test:
                try:
                    # Simple test to verify client works
                    params = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": "test"}],
                        "temperature": 0.0,
                    }

                    if self.deterministic and self.seed is not None:
                        params["seed"] = self.seed

                    response = self.client.chat.completions.create(**params)

                    if hasattr(response, "choices") and len(response.choices) > 0:
                        self.status = ServiceStatus.HEALTHY
                        logger.info(
                            f"LLM service initialized successfully with model: {self.model}"
                        )
                        return True
                    else:
                        self.status = ServiceStatus.UNHEALTHY
                        logger.error(
                            "LLM service connectivity test failed - no response choices"
                        )
                        return False

                except Exception as e:
                    logger.warning(
                        f"LLM connectivity test failed during initialization: {str(e)}"
                    )
                    # Still mark as available since client was created successfully
                    self.status = ServiceStatus.DEGRADED
                    return True
            else:
                # Skip test during fast startup
                self.status = ServiceStatus.HEALTHY
                logger.info(
                    f"LLM service initialized successfully with model: {self.model} (test skipped)"
                )
                return True

        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize LLM client: {str(e)}")
            return False

    async def initialize(self) -> bool:
        """Initialize the LLM service."""
        try:
            with self.track_request("initialize"):
                if not self.api_key:
                    self.status = ServiceStatus.DEGRADED
                    logger.warning("LLM service running in degraded mode - no API key")
                    return True

                # Initialize OpenAI client
                from openai import OpenAI

                # Get OpenAI version
                try:
                    import openai

                    openai_version_str = openai.__version__
                    version.parse(openai_version_str)
                    logger.info(f"Using OpenAI library version: {openai_version_str}")
                except Exception:
                    version.parse("0.0.0")
                    logger.warning("Could not determine OpenAI library version")

                # Initialize client
                client_params = {"api_key": self.api_key, "base_url": self.base_url}
                self.client = OpenAI(**client_params)

                # Test connectivity
                if await self._test_connectivity():
                    self.status = ServiceStatus.HEALTHY
                    logger.info(
                        f"LLM service initialized successfully with model: {self.model}"
                    )
                    return True
                else:
                    self.status = ServiceStatus.UNHEALTHY
                    logger.error("LLM service connectivity test failed")
                    return False

        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if not self.api_key or not self.client:
                return self.status == ServiceStatus.DEGRADED

            return await self._test_connectivity()

        except Exception as e:
            logger.error(f"LLM service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clear cache
            with self._cache_lock:
                self._response_cache.clear()
                self._cache_timestamps.clear()

            self.client = None

            logger.info("LLM service cleanup completed")

        except Exception as e:
            logger.error(f"Error during LLM service cleanup: {str(e)}")

    async def _test_connectivity(self) -> bool:
        """Test API connectivity."""
        try:
            if not self.client:
                return False

            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "temperature": 0.0,
            }

            if self.deterministic and self.seed is not None:
                params["seed"] = self.seed

            response = self.client.chat.completions.create(**params)

            if hasattr(response, "choices") and len(response.choices) > 0:
                return True

            return False

        except Exception as e:
            logger.debug(f"LLM connectivity test failed: {str(e)}")
            return False

    def is_available(self) -> bool:
        """Check if the LLM service is available - strict mode, only HEALTHY is acceptable."""
        return self.status == ServiceStatus.HEALTHY

    def _get_cache_key(self, *args) -> str:
        """Generate deterministic cache key from arguments."""
        import hashlib

        # Create a deterministic string representation
        normalized_args = []
        for arg in args:
            if isinstance(arg, str):
                # Normalize whitespace and case for consistency
                normalized = " ".join(str(arg).strip().split())
                normalized_args.append(normalized)
            else:
                normalized_args.append(str(arg))

        # Create consistent cache key using SHA-256
        cache_content = "|".join(normalized_args)
        return hashlib.sha256(cache_content.encode("utf-8")).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if valid."""
        with self._cache_lock:
            if cache_key in self._response_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self.cache_ttl:
                    self.metrics.add_custom_metric("cache_hits", 1)
                    return self._response_cache[cache_key]
                else:
                    # Remove expired entry
                    del self._response_cache[cache_key]
                    del self._cache_timestamps[cache_key]

            self.metrics.add_custom_metric("cache_misses", 1)
            return None

    def _cache_response(self, cache_key: str, response: Any) -> None:
        """Cache response with size limit."""
        with self._cache_lock:
            if len(self._response_cache) >= self.cache_size:
                oldest_key = min(
                    self._cache_timestamps.keys(),
                    key=lambda k: self._cache_timestamps[k],
                )
                del self._response_cache[oldest_key]
                del self._cache_timestamps[oldest_key]

            self._response_cache[cache_key] = response
            self._cache_timestamps[cache_key] = time.time()

    def _cleanup_cache(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        with self._cache_lock:
            expired_keys = [
                key
                for key, timestamp in self._cache_timestamps.items()
                if current_time - timestamp >= self.cache_ttl
            ]
            for key in expired_keys:
                del self._response_cache[key]
                del self._cache_timestamps[key]

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        use_cache: bool = True,
    ) -> str:
        """Generate response from LLM."""
        try:
            with self.track_request("generate_response"):
                if not self.is_available():
                    raise LLMServiceError("LLM service not available")

                # Check cache
                cache_key = self._get_cache_key(system_prompt, user_prompt, temperature)
                if use_cache:
                    cached_response = self._get_cached_response(cache_key)
                    if cached_response:
                        return cached_response

                # Prepare parameters
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": (
                        temperature if temperature is not None else self.temperature
                    ),
                }

                if self.deterministic and self.seed is not None:
                    params["seed"] = self.seed

                # Make API call with retry
                response = self._make_api_call_with_retry(params)
                result = response.choices[0].message.content.strip()

                # Cache response
                if use_cache:
                    self._cache_response(cache_key, result)

                return result

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            raise LLMServiceError(f"Failed to generate response: {str(e)}")

    def _make_api_call_with_retry(self, params: Dict[str, Any]) -> Any:
        """Make API call with enhanced retry logic, rate limiting, and connection pooling."""
        last_error = None
        start_time = time.time()
        client_to_use = None

        for attempt in range(self.max_retries):
            try:
                # Check rate limiting
                if not self.rate_limiter.can_make_request():
                    wait_time = self.rate_limiter.get_wait_time()
                    if wait_time > 0:
                        logger.info(
                            f"Rate limit reached, waiting {wait_time:.2f} seconds"
                        )
                        time.sleep(wait_time)

                if self.connection_pool:
                    try:
                        client_to_use = self.connection_pool.get_connection(timeout=5.0)
                    except Exception as pool_error:
                        logger.warning(
                            f"Failed to get connection from pool: {pool_error}"
                        )
                        client_to_use = self.client
                else:
                    client_to_use = self.client

                if not client_to_use:
                    raise LLMServiceError("No client available", error_code="NO_CLIENT")

                # Make the API call with timeout handling
                try:
                    response = client_to_use.chat.completions.create(**params)

                    # Record successful request
                    self.rate_limiter.record_request()

                    # Return connection to pool
                    if self.connection_pool and client_to_use != self.client:
                        self.connection_pool.return_connection(client_to_use)

                    # Update performance metrics
                    duration = time.time() - start_time
                    monitoring_service.record_performance_metric(
                        "consolidated_llm_service",
                        "llm_api_call",
                        duration,
                        {
                            "attempt": attempt + 1,
                            "model": self.model,
                            "success": True,
                            "tokens_used": (
                                response.usage.total_tokens
                                if hasattr(response, "usage") and response.usage
                                else 0
                            ),
                        },
                    )

                    return response

                except Exception as api_error:
                    # Return connection to pool even on error
                    if self.connection_pool and client_to_use != self.client:
                        self.connection_pool.return_connection(client_to_use)
                    raise api_error

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Enhanced error categorization and handling
                context = ErrorContext(
                    operation="llm_api_call",
                    service="consolidated_llm_service",
                    timestamp=datetime.now(timezone.utc),
                    user_id=params.get("user_id"),
                    request_id=f"llm_{int(time.time())}_{attempt}",
                    additional_data={
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries,
                        "model": self.model,
                        "params_size": len(str(params)),
                    },
                )

                error_response = error_service.handle_error(e, context)

                should_retry = error_response.recoverable

                if any(
                    indicator in error_str
                    for indicator in ["rate limit", "429", "too many requests"]
                ):
                    # Rate limiting - wait longer
                    if attempt < self.max_retries - 1:
                        wait_time = min(
                            60, (2**attempt) * 5
                        )  # Exponential backoff up to 60s
                        logger.warning(
                            f"Rate limited, waiting {wait_time}s before retry {attempt + 1}"
                        )
                        time.sleep(wait_time)
                        continue

                elif any(
                    indicator in error_str
                    for indicator in ["timeout", "connection", "network"]
                ):
                    # Network issues - retry with exponential backoff
                    if attempt < self.max_retries - 1 and should_retry:
                        wait_time = min(30, (1.5**attempt) * self.retry_delay)
                        if self.jitter:
                            wait_time += random.uniform(0, wait_time * 0.1)
                        logger.warning(
                            f"Network error, retrying in {wait_time:.2f}s: {e}"
                        )
                        time.sleep(wait_time)
                        continue

                elif any(
                    indicator in error_str
                    for indicator in ["server error", "500", "502", "503", "504"]
                ):
                    # Server errors - retry with backoff
                    if attempt < self.max_retries - 1 and should_retry:
                        wait_time = min(45, (2**attempt) * 2)
                        logger.warning(f"Server error, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue

                elif any(
                    indicator in error_str
                    for indicator in ["authentication", "unauthorized", "401"]
                ):
                    # Auth errors - don't retry
                    logger.error(f"Authentication error, not retrying: {e}")
                    break

                elif any(
                    indicator in error_str
                    for indicator in ["invalid", "bad request", "400"]
                ):
                    # Bad request - don't retry
                    logger.error(f"Bad request error, not retrying: {e}")
                    break

                else:
                    # Generic retry logic
                    if attempt < self.max_retries - 1 and should_retry:
                        wait_time = min(
                            self.max_backoff_delay, self.retry_delay * (2**attempt)
                        )
                        if self.jitter:
                            wait_time += random.uniform(0, wait_time * 0.1)
                        logger.warning(
                            f"API call failed, retrying in {wait_time:.2f}s: {e}"
                        )
                        time.sleep(wait_time)
                        continue

                # Log the error with enhanced context
                enhanced_logging_service.log_error(
                    f"LLM API call failed on attempt {attempt + 1}",
                    LogCategory.API,
                    {
                        "error": str(e),
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries,
                        "model": self.model,
                        "error_response": error_response,
                    },
                )

        # All retries exhausted
        duration = time.time() - start_time
        monitoring_service.record_performance_metric(
            "consolidated_llm_service",
            "llm_api_call",
            duration,
            {
                "attempts": self.max_retries,
                "final_error": str(last_error),
                "model": self.model,
                "success": False,
            },
        )

        fallback_context = ErrorContext(
            operation="llm_api_call",
            service="consolidated_llm_service",
            timestamp=datetime.now(timezone.utc),
            user_id=params.get("user_id"),
            request_id=f"llm_fallback_{int(time.time())}",
            additional_data={"final_error": str(last_error)},
        )

        fallback_result = fallback_manager.execute_with_fallback(
            primary_func=lambda: None,  # Already failed
            fallback_func=self._get_fallback_response,
            operation="llm_processing",
            context=fallback_context,
            params=params,
            error=last_error,
        )

        if fallback_result:
            logger.info("Using fallback response for LLM API call")
            return fallback_result

        raise LLMServiceError(
            f"LLM API call failed after {self.max_retries} attempts: {last_error}",
            error_code="API_CALL_FAILED",
            original_error=last_error,
        )

    def _get_fallback_response(self, params: Dict[str, Any], error: Exception) -> Any:
        """Generate fallback response when API calls fail"""
        try:
            # Try to get cached response first
            messages = params.get("messages", [])
            if len(messages) >= 2:
                messages[0].get("content", "")
                messages[1].get("content", "")

                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    logger.info("Using cached response as fallback")

                    # Create mock response object
                    class MockChoice:
                        def __init__(self, content):
                            self.message = type("obj", (object,), {"content": content})

                    class MockResponse:
                        def __init__(self, content):
                            self.choices = [MockChoice(content)]

                    return MockResponse(cached_response)

            # Generate basic fallback response based on context
            fallback_content = self._generate_basic_fallback(params)

            class MockChoice:
                def __init__(self, content):
                    self.message = type("obj", (object,), {"content": content})

            class MockResponse:
                def __init__(self, content):
                    self.choices = [MockChoice(content)]

            return MockResponse(fallback_content)

        except Exception as fallback_error:
            logger.error(f"Fallback response generation failed: {fallback_error}")
            return None

    def _generate_basic_fallback(self, params: Dict[str, Any]) -> str:
        """Generate basic fallback response based on request context"""
        messages = params.get("messages", [])

        # Analyze the request to determine appropriate fallback
        if len(messages) >= 2:
            user_content = messages[1].get("content", "").lower()

            # Grading-related fallback
            if any(
                keyword in user_content
                for keyword in ["grade", "score", "evaluate", "assess"]
            ):
                return json.dumps(
                    {
                        "overall_grade": {
                            "score": 0,
                            "feedback": "Unable to process request due to service unavailability. Please try again later.",
                        },
                        "criteria_scores": {
                            "accuracy": 0,
                            "completeness": 0,
                            "understanding": 0,
                            "clarity": 0,
                        },
                        "strengths": [],
                        "areas_for_improvement": [
                            "Service temporarily unavailable - manual review required"
                        ],
                        "requires_manual_review": True,
                        "fallback_response": True,
                    }
                )

            # Analysis-related fallback
            elif any(
                keyword in user_content for keyword in ["analyze", "review", "examine"]
            ):
                return "I apologize, but I'm currently unable to process your request due to service unavailability. Please try again in a few moments. If the issue persists, please contact support."

            # Question-answering fallback
            elif "?" in user_content:
                return "I'm sorry, but I'm currently experiencing technical difficulties and cannot provide a response to your question. Please try again later."

        # Generic fallback
        return "Service temporarily unavailable. Please try again later."

    def _generate_basic_fallback_content(self, messages: List[Dict[str, str]]) -> str:
        """Generate basic fallback content based on message context"""
        try:
            # Analyze the request type
            if len(messages) > 1:
                user_content = messages[-1].get("content", "").lower()

                # Grading-related fallback
                if any(
                    keyword in user_content
                    for keyword in ["grade", "score", "evaluate", "assess"]
                ):
                    return json.dumps(
                        {
                            "overall_grade": {
                                "score": 0,
                                "percentage": 0,
                                "letter_grade": "N/A",
                            },
                            "detailed_scores": {
                                "accuracy": 0,
                                "completeness": 0,
                                "understanding": 0,
                                "clarity": 0,
                            },
                            "strengths": [],
                            "areas_for_improvement": [
                                "Service temporarily unavailable - manual review required"
                            ],
                            "requires_manual_review": True,
                            "fallback_response": True,
                        }
                    )

                # Analysis-related fallback
                elif any(
                    keyword in user_content
                    for keyword in ["analyze", "review", "examine"]
                ):
                    return "I apologize, but I'm currently unable to process your request due to service unavailability. Please try again in a few moments."

                # Question-answering fallback
                elif "?" in user_content:
                    return "I'm sorry, but I'm currently experiencing technical difficulties and cannot provide a response to your question. Please try again later."

            # Generic fallback
            return "Service temporarily unavailable. Please try again later."

        except Exception as e:
            logger.error(f"Error generating fallback content: {e}")

    def cleanup(self) -> None:
        """Clean up service resources."""
        try:
            with self._cache_lock:
                self._response_cache.clear()
            logger.info("ConsolidatedLLMService cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            return {
                "status": "healthy",
                "service": "consolidated_llm_service",
                "cache_size": len(self._response_cache),
                "available": self.is_available(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "consolidated_llm_service",
                "error": str(e),
            }


def get_llm_service_for_user(user_id: str = None) -> ConsolidatedLLMService:
    """Get LLM service configured with user-specific settings.
    
    Args:
        user_id: User ID to get settings for. If None, uses default settings.
        
    Returns:
        ConsolidatedLLMService configured with user settings
    """
    try:
        # Import here to avoid circular imports
        from src.database.models import UserSettings
        
        # Get user settings
        if user_id:
            user_settings = UserSettings.get_or_create_for_user(user_id)
            settings_dict = user_settings.to_dict()
        else:
            settings_dict = UserSettings.get_default_settings()
        
        # Extract LLM configuration with proper fallback chain
        api_key = (settings_dict.get('llm_api_key') or 
                  os.getenv("LLM_API_KEY") or 
                  os.getenv("DEEPSEEK_API_KEY"))
        base_url = (settings_dict.get('llm_base_url') or 
                   os.getenv("LLM_API_URL") or 
                   os.getenv("DEEPSEEK_API_URL") or 
                   "https://api.deepseek.com/v1")
        
        # Set appropriate default model based on base URL
        if "deepseek" in base_url.lower():
            default_model = "deepseek-chat"
        else:
            default_model = "gpt-3.5-turbo"
            
        model = settings_dict.get('llm_model', default_model)
        
        # Create service with user settings
        return ConsolidatedLLMService(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        
    except Exception as e:
        logger.warning(f"Failed to get user-specific LLM service: {e}")
        # Fallback to default service
        return ConsolidatedLLMService()


def get_llm_service_for_current_user() -> ConsolidatedLLMService:
    """Get LLM service configured for the current Flask user.
    
    Returns:
        ConsolidatedLLMService configured with current user's settings
    """
    try:
        from flask_login import current_user
        
        if current_user and current_user.is_authenticated:
            return get_llm_service_for_user(current_user.id)
        else:
            return get_llm_service_for_user()
            
    except Exception as e:
        logger.warning(f"Failed to get LLM service for current user: {e}")
        return ConsolidatedLLMService()