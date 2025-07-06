"""
LLM Service for grading exam submissions using DeepSeek Reasoner API.

This module provides a service for integrating with the DeepSeek API to grade
student exam submissions against marking guides.

This is an updated version that works with the latest OpenAI library.
"""

import importlib.metadata
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from packaging import version

from src.config.unified_config import config
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


class LLMService:
    """
    LLM service for grading exam submissions using DeepSeek Reasoner API.

    This service provides methods for:
    - Comparing student answers to expected answers
    - Grading submissions based on marking guides
    - Generating feedback for student submissions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = config.api.deepseek_model,
        temperature: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        seed: Optional[int] = 42,
        deterministic: bool = True,

    ):
        """Initialize the LLM service.

        Args:
            api_key: DeepSeek API key (from environment if not provided)
            base_url: DeepSeek API base URL
            model: DeepSeek model name to use
            temperature: Sampling temperature (0.0 for most deterministic output)
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Delay between retry attempts in seconds
            seed: Random seed for deterministic outputs (default: 42)
            deterministic: Whether to use deterministic mode (default: True)


        Raises:
            LLMServiceError: If API key is not available
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise LLMServiceError(
                "DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env"
            )

        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.seed = seed
        self.deterministic = deterministic


        # Initialize response cache
        self._response_cache = {}
        self._cache_lock = threading.Lock()

        # Log the deterministic mode setting
        if self.deterministic:
            logger.info(
                f"LLM service initialized in deterministic mode with seed: {self.seed}"
            )
        else:
            logger.info("LLM service initialized in non-deterministic mode")

        try:
            # Import OpenAI in a way that handles different versions
            from openai import OpenAI

            # Get the OpenAI version
            try:
                openai_version_str = importlib.metadata.version("openai")
                openai_version = version.parse(openai_version_str)
                logger.info(f"Using OpenAI library version: {openai_version_str}")
            except (importlib.metadata.PackageNotFoundError, version.InvalidVersion):
                openai_version = version.parse("0.0.0")
                logger.warning("Could not determine OpenAI library version")

            # Initialize OpenAI client with parameters based on version
            client_params = {"api_key": self.api_key, "base_url": self.base_url}

            # Create the client with appropriate parameters
            self.client = OpenAI(**client_params)
            logger.info(f"LLM service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")

    def is_available(self) -> bool:
        """Check if the LLM service is available by testing API connectivity."""
        try:
            # Basic configuration check
            if not self.api_key:
                logger.debug("LLM service unavailable: No API key configured")
                return False
            if not self.client:
                logger.debug("LLM service unavailable: No client configured")
                return False

            # Test API connectivity with a minimal request
            try:
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "test"}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 1,
                }

                # Add seed parameter if in deterministic mode
                if self.deterministic and self.seed is not None:
                    params["seed"] = self.seed

                response = self.client.chat.completions.create(**params)

                # Check if we got a valid response
                if hasattr(response, "choices") and len(response.choices) > 0:
                    logger.debug("LLM service connectivity confirmed")
                    return True
                else:
                    logger.debug("LLM service test failed: No valid response")
                    return False

            except Exception as api_error:
                logger.debug(f"LLM service API test failed: {str(api_error)}")
                return False

        except Exception as e:
            logger.error(f"LLM service availability check failed: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to the DeepSeek API.

        Returns:
            bool: True if connection is successful

        Raises:
            LLMServiceError: If connection test fails
        """
        try:
            logger.info("Testing connection to DeepSeek API...")

            # Simple test prompt
            system_prompt = "You are a helpful assistant."
            user_prompt = "Please respond with a simple 'Connection successful' if you receive this message."

            # Make a minimal API call
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 20,
            }

            # Add seed parameter if in deterministic mode
            if self.deterministic and self.seed is not None:
                params["seed"] = self.seed

            response = self.client.chat.completions.create(**params)

            # Check if we got a response
            if hasattr(response, "choices") and len(response.choices) > 0:
                logger.info("Connection test successful")
                return True
            else:
                logger.error("Connection test failed: No valid response received")
                raise LLMServiceError("No valid response received from API")

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise LLMServiceError(f"Failed to connect to DeepSeek API: {str(e)}")

    def compare_answers(
        self,
        question: str,
        guide_answer: str,
        submission_answer: str,
        max_score: int = 10,
    ) -> Tuple[float, str]:
        """
        Compare a student's submission answer with the model answer from the marking guide.
        Enhanced with caching, retry logic, and better error handling.

        Args:
            question: The question being answered
            guide_answer: The model answer from the marking guide
            submission_answer: The student's submission answer
            max_score: The maximum possible score for this question

        Returns:
            Tuple[float, str]: (Score, Feedback)

        Raises:
            LLMServiceError: If the API call fails after all retries
        """
        try:  # Added proper error handling for API operations
            # Log the start of answer comparison
            logger.info("Preparing to compare answers...")

            # Optimize prompt length for performance
            max_content_length = int(os.getenv("MAX_CONTENT_LENGTH", 10000))  # Configurable content length

            # Truncate long content while preserving key information
            question_truncated = question[:max_content_length] if len(question) > max_content_length else question
            guide_answer_truncated = guide_answer[:max_content_length] if len(guide_answer) > max_content_length else guide_answer
            submission_answer_truncated = submission_answer[:max_content_length] if len(submission_answer) > max_content_length else submission_answer

            # Construct optimized prompt for faster processing
            system_prompt = """You are an educational grading assistant. Compare a student's answer to a model answer and assign a score.

            Guidelines:
            - Score: 0 to maximum score
            - Focus on content accuracy and key points
            - Be objective and consistent

            Response format (JSON only). Your response MUST be a valid JSON object with 'score' (numeric) and 'feedback' (string) keys. Example: {"score": 8.5, "feedback": "Good answer, but missing a key detail."}"""

            user_prompt = f"""Question: {question_truncated}

            Model Answer: {guide_answer_truncated}

            Student Answer: {submission_answer_truncated}

            Max Score: {max_score}

            Evaluate and provide score with feedback."""

            # Create messages for caching
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Check cache first
            cache_key = self._generate_cache_key(messages)
            cached_response = self._get_cached_response(cache_key)

            if cached_response:
                logger.info("Using cached response for answer comparison")
                response_text = cached_response
            else:
                logger.info("Making API call for answer comparison...")

                # Prepare optimized API parameters
                params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.0,  # Deterministic for consistency
    
                }

                # Ensure JSON format for Deepseek-Reasoner
                if self.model == "deepseek-ai/deepseek-reasoner":
                    params["response_format"] = {"type": "json_object"}

                # Add seed parameter if in deterministic mode
                if self.deterministic and self.seed is not None:
                    params["seed"] = self.seed

                # Make API call with retry logic
                response = self._make_api_call_with_retry(params)
                response_text = response.choices[0].message.content.strip()

                # Cache the response
                self._cache_response(cache_key, response_text)

            # Parse and validate the response
            logger.info("Processing LLM response...")

            # Enhanced JSON parsing with multiple fallback strategies
            result, extraction_method = self.parse_llm_response(response_text)
            
            # Validate required fields
            if not all(key in result for key in ['score', 'feedback']):
                logger.error("Missing required keys in LLM response")
                raise LLMServiceError("Invalid response format from LLM")

            # Extract and validate score
            try:
                score = float(result['score'])
                score = max(0, min(score, max_score))
                feedback = str(result['feedback'])
                
                logger.info(f"Answer comparison completed. Score: {score}/{max_score}")
                return score, f"[{extraction_method}] {feedback}"
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid score value: {str(e)}")
                return 0, f"Error: Invalid scoring format - {str(e)}"
            except LLMServiceError as e:
                logger.error(f"LLM service error during comparison: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during answer comparison: {str(e)}")
                return 0, f"System error: {str(e)}"

        # Add proper error handling for the main try block
        except ConnectionError as ce:
            logger.error(f"API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"Invalid JSON response: {str(je)}")
            raise LLMServiceError("Malformed API response") from je
        except Exception as e:
            logger.error(f"Unexpected error during comparison: {str(e)}")
            raise LLMServiceError("Comparison process failed") from e

        # Add proper error handling for the main try block
        except ConnectionError as ce:
            logger.error(f"API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"Invalid JSON response: {str(je)}")
            raise LLMServiceError("Malformed API response") from je
        except Exception as e:
            logger.error(f"Unexpected error during comparison: {str(e)}")
            raise LLMServiceError("Comparison process failed") from e

        except ConnectionError as ce:
            logger.error(f"LLM API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}")
            raise LLMServiceError("Invalid response format from API") from je
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}") from e
        
        # Add proper error handling for the outer try block
        except ConnectionError as ce:
            logger.error(f"API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"Invalid JSON response: {str(je)}")
            raise LLMServiceError("Malformed API response") from je
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise LLMServiceError("Failed to process API response") from e

        except ConnectionError as ce:
            logger.error(f"LLM API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}")
            raise LLMServiceError("Invalid response format from API") from je
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}") from e

        except ConnectionError as ce:
            logger.error(f"LLM API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}")
            raise LLMServiceError("Invalid response format from API") from je
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}") from e
        
        except ConnectionError as ce:
            logger.error(f"LLM API connection failed: {str(ce)}")
            raise LLMServiceError(f"Connection error: {str(ce)}") from ce
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}")
            raise LLMServiceError("Invalid response format from API") from je
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}") from e

    def parse_llm_response(self, response_text: str) -> Tuple[Dict, str]:
        """
        Parse LLM response using structured JSON parsing with LLM assistance.
        """
        try:
            # Use LLM to fix and structure the response
            sanitized_response = self._get_structured_response(response_text)
            return json.loads(sanitized_response), "structured"
        except Exception as e:
            logger.error(f"Structured parsing failed: {str(e)}")
            raise LLMServiceError("Failed to parse LLM response")

    def _get_structured_response(self, text: str) -> str:
        """Use LLM to convert free-form response to valid JSON"""
        prompt = """Convert this unstructured response to valid JSON format:
        
        {response}
        
        Return ONLY the JSON object with 'score' and 'feedback' keys.""".format(response=text)

        return self._get_llm_response(prompt)
        
    def _get_llm_response(self, prompt: str) -> str:
        """Send a prompt to the LLM and get a response"""
        try:
            # Prepare API parameters
            params = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,  # Deterministic for consistency

            }
            
            # Add seed parameter if in deterministic mode
            if self.deterministic and self.seed is not None:
                params["seed"] = self.seed

            # Make API call
            response = self.client.chat.completions.create(**params)
            response_text = response.choices[0].message.content.strip()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            raise LLMServiceError(f"Failed to get LLM response: {str(e)}") from e

    def process_marking_guide(self, guide_text: str) -> Dict:
        """
        Analyze marking guide and extract structured Q&A using LLM.
        Returns either question-based or answer-based format.
        """
        prompt = """Analyze this marking guide and extract either:
        1. Questions with model answers (if questions exist)
        2. Model answers with sections (if no explicit questions)
        
        Guide:
        {guide}
        
        Return JSON format:
        {{
            "type": "question|answer",
            "items": [
                {{"question": "...", "answer": "..."}} OR {{"section": "...", "answer": "..."}}
            ]
        }}""".format(guide=guide_text[:5000])

        response = self._get_llm_response(prompt)
        return json.loads(response)

    def grade_submission(
        self,
        marking_guide_text: str,
        student_submission_text: str,

    ) -> Dict:
        """
        Grade a student submission against a marking guide.
        This method works with the mapping service to:
        1. Identify questions and answers in both documents
        2. Score each answer based on similarity to the expected answer

        Args:
            marking_guide_text: Full text of the marking guide
            student_submission_text: Full text of the student submission

        Returns:
            Dict: Grading result with scores and feedback
        """
        # Import here to avoid circular imports
        from src.services.mapping_service import MappingService

        # Create mapping service if needed
        mapping_service = MappingService(llm_service=self)

        # Map the submission to the guide
        mapping_result, mapping_error = mapping_service.map_submission_to_guide(
            marking_guide_text, student_submission_text
        )

        if mapping_error:
            return {"status": "error", "message": f"Mapping error: {mapping_error}"}

        # Create grading service
        from src.services.grading_service import GradingService

        grading_service = GradingService(
            llm_service=self, mapping_service=mapping_service
        )

        # Grade the submission
        grading_result, grading_error = grading_service.grade_submission(
            marking_guide_text, student_submission_text
        )

        if grading_error:
            return {"status": "error", "message": f"Grading error: {grading_error}"}

        return grading_result

    def map_submission_to_guide(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = None,
    ) -> Tuple[Dict, Optional[str]]:
        """
        Map a student submission to a marking guide.
        This is a wrapper around the mapping service functionality.

        Args:
            marking_guide_content: Full text of the marking guide
            student_submission_content: Full text of the student submission
            num_questions: Optional number of questions to map (for best N answers)

        Returns:
            Tuple[Dict, Optional[str]]: (Mapping result, Error message if any)
        """
        # Import here to avoid circular imports
        from src.services.mapping_service import MappingService

        # Create mapping service
        mapping_service = MappingService(llm_service=self)

        # Map the submission to the guide
        if num_questions is not None:
            return mapping_service.map_submission_to_guide(
                marking_guide_content,
                student_submission_content,
                num_questions=num_questions,
            )
        else:
            return mapping_service.map_submission_to_guide(
                marking_guide_content, student_submission_content
            )
       

    def _generate_cache_key(self, messages: List[Dict[str, str]]) -> str:
        """Generate a cache key from messages and parameters"""
        # Create a string representation of the messages and parameters
        key_parts = [
            self.model,
            str(self.temperature),

            str(self.seed) if self.deterministic else "non-deterministic",
        ]
        
        # Add message content to the key
        for msg in messages:
            key_parts.append(f"{msg['role']}:{msg['content']}")
            
        # Join all parts and create a hash
        key_str = "|".join(key_parts)
        import hashlib
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get a cached response if available"""
        with self._cache_lock:
            return self._response_cache.get(cache_key)
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a response for future use"""
        with self._cache_lock:
            self._response_cache[cache_key] = response
            
    def _make_api_call_with_retry(self, params: Dict[str, Any]):
        """Make an API call with retry logic"""
        attempts = 0
        last_error = None
        
        while attempts < self.max_retries:
            try:
                return self.client.chat.completions.create(**params)
            except Exception as e:
                last_error = e
                logger.warning(f"API call attempt {attempts+1} failed: {str(e)}")
                
                # Exponential backoff with jitter
                backoff_time = self.retry_delay * (2 ** attempts) * (0.5 + random.random())
                logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
                
                attempts += 1
        
        # If we get here, all retries failed
        logger.error(f"API call failed after {self.max_retries} attempts")
        raise LLMServiceError(f"API call failed after {self.max_retries} attempts", original_error=last_error)
       
