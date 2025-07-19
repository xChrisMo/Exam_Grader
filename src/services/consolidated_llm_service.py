"""Consolidated LLM Service merging LLMService and EnhancedLLMService.

This module provides a unified LLM service that combines the functionality of both
LLMService and EnhancedLLMService with integration to the base service architecture.
"""

import importlib.metadata
import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from packaging import version
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.unified_config import config
from src.services.base_service import BaseService, ServiceStatus
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


class ConsolidatedLLMService(BaseService):
    """Consolidated LLM service with enhanced functionality and base service integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = None,
        temperature: float = 0.0,
        max_retries: int = 10,  # Increased retries
        retry_delay: float = 0.5,  # Reduced delay
        seed: Optional[int] = 42,
        deterministic: bool = True,
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
        
        # Configuration
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.model = model or (config.api.deepseek_model if hasattr(config, 'api') else "deepseek-reasoner")
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
        
        # Client initialization
        self.client = None
        self.supports_json = False
        
        # Set initial status based on API key availability
        if not self.api_key:
            self.status = ServiceStatus.DEGRADED
            logger.warning("LLM service initialized without API key - degraded mode")
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
                openai_version_str = importlib.metadata.version("openai")
                logger.info(f"Using OpenAI library version: {openai_version_str}")
            except (importlib.metadata.PackageNotFoundError, version.InvalidVersion):
                logger.warning("Could not determine OpenAI library version")
            
            # Initialize client
            client_params = {"api_key": self.api_key, "base_url": self.base_url}
            self.client = OpenAI(**client_params)
            
            # Test basic connectivity (synchronous)
            try:
                # Simple test to verify client works
                params = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "temperature": 0.0
                    # No token limits for unrestricted responses
                }
                
                if self.deterministic and self.seed is not None:
                    params["seed"] = self.seed
                
                response = self.client.chat.completions.create(**params)
                
                if hasattr(response, "choices") and len(response.choices) > 0:
                    self.status = ServiceStatus.HEALTHY
                    logger.info(f"LLM service initialized successfully with model: {self.model}")
                    return True
                else:
                    self.status = ServiceStatus.UNHEALTHY
                    logger.error("LLM service connectivity test failed - no response choices")
                    return False
                    
            except Exception as e:
                logger.warning(f"LLM connectivity test failed during initialization: {str(e)}")
                # Still mark as available since client was created successfully
                self.status = ServiceStatus.DEGRADED
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
                    openai_version_str = importlib.metadata.version("openai")
                    openai_version = version.parse(openai_version_str)
                    logger.info(f"Using OpenAI library version: {openai_version_str}")
                except (importlib.metadata.PackageNotFoundError, version.InvalidVersion):
                    openai_version = version.parse("0.0.0")
                    logger.warning("Could not determine OpenAI library version")
                
                # Initialize client
                client_params = {"api_key": self.api_key, "base_url": self.base_url}
                self.client = OpenAI(**client_params)
                
                # Test connectivity
                if await self._test_connectivity():
                    self.status = ServiceStatus.HEALTHY
                    logger.info(f"LLM service initialized successfully with model: {self.model}")
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
            
            # Close client if needed
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
        """Check if the LLM service is available."""
        return self.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return str(hash(str(args)))

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
            # Remove oldest entries if cache is full
            if len(self._response_cache) >= self.cache_size:
                oldest_key = min(self._cache_timestamps.keys(), 
                               key=lambda k: self._cache_timestamps[k])
                del self._response_cache[oldest_key]
                del self._cache_timestamps[oldest_key]
            
            self._response_cache[cache_key] = response
            self._cache_timestamps[cache_key] = time.time()

    def _cleanup_cache(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        with self._cache_lock:
            expired_keys = [
                key for key, timestamp in self._cache_timestamps.items()
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
        use_cache: bool = True
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
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature if temperature is not None else self.temperature,
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
        """Make API call with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(**params)
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"API call attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                
        raise LLMServiceError(
            f"API call failed after {self.max_retries} attempts", 
            original_error=last_error
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "cache_size": len(self._response_cache),
                "max_cache_size": self.cache_size,
                "cache_ttl": self.cache_ttl,
                "cache_hits": self.metrics.custom_metrics.get("cache_hits", 0),
                "cache_misses": self.metrics.custom_metrics.get("cache_misses", 0)
            }

    def clear_cache(self) -> None:
        """Clear the response cache."""
        with self._cache_lock:
            self._response_cache.clear()
            self._cache_timestamps.clear()
        logger.info("LLM service cache cleared")

    def preprocess_ocr_text(self, text: str) -> str:
        """Preprocess OCR text to improve understanding."""
        if not text:
            return ""
        
        try:
            with self.track_request("preprocess_ocr"):
                if self.client and self.is_available():
                    # Use LLM to preprocess OCR text
                    system_prompt = """
You are an OCR text preprocessing expert. Clean and improve the provided OCR text by:
1. Fixing common OCR artifacts and character recognition errors
2. Normalizing whitespace and line breaks
3. Removing headers, footers, page numbers, and watermarks
4. Fixing punctuation and quote normalization
5. Preserving all meaningful content and structure
6. Return only the cleaned text without any explanations

Common OCR fixes:
- | → I (vertical bar to letter I)
- 0 → O (zero to letter O when appropriate)
- 1 → l (one to lowercase L when appropriate)
- 5 → S (five to letter S when appropriate)
- 8 → B (eight to letter B when appropriate)
"""
                    
                    user_prompt = f"Clean and preprocess this OCR text:\n\n{text}"  # No text truncation
                    
                    response = self.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.1
                    )
                    
                    return response.strip() if response else text
                else:
                    # Basic fallback preprocessing
                    lines = text.split('\n')
                    cleaned_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if line and not line.isdigit():  # Skip page numbers
                            # Basic character fixes
                            line = line.replace('|', 'I')
                            line = line.replace('0', 'O')  # Context-dependent
                            cleaned_lines.append(line)
                    
                    return '\n'.join(cleaned_lines)
                    
        except Exception as e:
            logger.error(f"OCR preprocessing failed: {str(e)}")
            return text  # Return original text on error

    def get_standardized_grading_prompt(self, question: str, model_answer: str, student_answer: str) -> str:
        """Generate standardized grading prompt."""
        return f"""
You are an expert exam grader. Grade the student's answer against the model answer for the given question.

**CRITICAL INSTRUCTIONS:**
1. You MUST return a valid JSON object with the exact structure shown below
2. Do NOT include any text before or after the JSON
3. Use double quotes for all strings in JSON
4. Ensure all numeric scores are integers between 0-100

**QUESTION:**
{question}

**MODEL ANSWER:**
{model_answer}

**STUDENT ANSWER:**
{student_answer}

**GRADING CRITERIA:**
- Accuracy: How correct is the student's answer?
- Completeness: Does the answer address all parts of the question?
- Understanding: Does the student demonstrate understanding of concepts?
- Clarity: Is the answer well-organized and clearly expressed?

**REQUIRED JSON OUTPUT FORMAT:**
{{
    "overall_grade": {{
        "score": <integer 0-100>,
        "feedback": "<detailed feedback explaining the grade>"
    }},
    "criteria_scores": {{
        "accuracy": <integer 0-100>,
        "completeness": <integer 0-100>,
        "understanding": <integer 0-100>,
        "clarity": <integer 0-100>
    }},
    "strengths": ["<strength 1>", "<strength 2>"],
    "areas_for_improvement": ["<improvement 1>", "<improvement 2>"]
}}
"""

    def compare_answers(self, question: str, model_answer: str, student_answer: str) -> Dict[str, Any]:
        """Compare student answer with model answer and return grading results."""
        try:
            with self.track_request("compare_answers"):
                if not self.is_available():
                    raise LLMServiceError("LLM service not available for grading")
                
                # Check cache
                cache_key = self._get_cache_key(question, model_answer, student_answer)
                cached_result = self._get_cached_response(cache_key)
                if cached_result:
                    return cached_result
                
                # Generate grading prompt
                prompt = self.get_standardized_grading_prompt(question, model_answer, student_answer)
                
                # Make API call
                params = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                }
                
                if self.deterministic and self.seed is not None:
                    params["seed"] = self.seed
                
                response = self._make_api_call_with_retry(params)
                response_text = response.choices[0].message.content.strip()
                
                # Parse and validate response
                result = self._parse_grading_response(response_text)
                
                # Cache result
                self._cache_response(cache_key, result)
                
                return result
                
        except Exception as e:
            logger.error(f"Answer comparison failed: {str(e)}")
            # Return fallback result
            return {
                "overall_grade": {"score": 0, "feedback": f"Grading failed: {str(e)}"},
                "criteria_scores": {"accuracy": 0, "completeness": 0, "understanding": 0, "clarity": 0},
                "strengths": [],
                "areas_for_improvement": ["Unable to grade due to system error"]
            }

    def _parse_grading_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate grading response."""
        # Try direct JSON parsing first
        try:
            result = json.loads(response_text)
            return self._validate_grading_result(result)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return self._validate_grading_result(result)
            except json.JSONDecodeError:
                pass
        
        # Fallback: create basic result
        logger.warning("Could not parse grading response, using fallback")
        return {
            "overall_grade": {"score": 50, "feedback": "Unable to parse detailed grading"},
            "criteria_scores": {"accuracy": 50, "completeness": 50, "understanding": 50, "clarity": 50},
            "strengths": [],
            "areas_for_improvement": ["Response parsing failed"]
        }

    def _validate_grading_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize grading result."""
        # Ensure required structure
        if "overall_grade" not in result:
            result["overall_grade"] = {"score": 0, "feedback": "Missing overall grade"}
        
        if "criteria_scores" not in result:
            result["criteria_scores"] = {"accuracy": 0, "completeness": 0, "understanding": 0, "clarity": 0}
        
        if "strengths" not in result:
            result["strengths"] = []
        
        if "areas_for_improvement" not in result:
            result["areas_for_improvement"] = []
        
        # Validate score ranges
        if isinstance(result["overall_grade"], dict) and "score" in result["overall_grade"]:
            score = result["overall_grade"]["score"]
            if not isinstance(score, int) or score < 0 or score > 100:
                result["overall_grade"]["score"] = max(0, min(100, int(score) if isinstance(score, (int, float)) else 0))
        
        # Validate criteria scores
        for criterion in ["accuracy", "completeness", "understanding", "clarity"]:
            if criterion in result["criteria_scores"]:
                score = result["criteria_scores"][criterion]
                if not isinstance(score, int) or score < 0 or score > 100:
                    result["criteria_scores"][criterion] = max(0, min(100, int(score) if isinstance(score, (int, float)) else 0))
        
        return result

    def _get_structured_response(self, text: str) -> str:
        """Use LLM to convert free-form response to valid JSON format."""
        try:
            system_prompt = """You are a JSON formatting expert. Convert the provided unstructured response to valid JSON format.
            
Rules:
1. Return ONLY valid JSON, no explanations
2. Preserve all meaningful data from the input
3. Use appropriate JSON structure based on content
4. For grading responses, use keys like 'score', 'feedback', 'confidence', etc.
5. Ensure all strings are properly quoted
6. Ensure all numbers are valid JSON numbers"""
            
            user_prompt = f"Convert this unstructured response to valid JSON format:\n\n{text}"
            
            response = self.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            return response.strip() if response else text
            
        except Exception as e:
            logger.error(f"Error in _get_structured_response: {str(e)}")
            # Fallback: try to extract JSON-like content
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json_match.group()
            return text


    def create_chat_completion_batch(self, *args, **kwargs):
        """
        Compatibility method for batch processing.
        This method exists to handle legacy calls that might reference it.
        """
        # Remove max_tokens if present as it's not supported in newer versions
        if 'max_tokens' in kwargs:
            logger.warning("Removing unsupported 'max_tokens' parameter from batch completion call")
            del kwargs['max_tokens']
        
        # Delegate to the standard completion method
        return self.client.chat.completions.create(*args, **kwargs)


# Backward compatibility aliases
LLMService = ConsolidatedLLMService
EnhancedLLMService = ConsolidatedLLMService