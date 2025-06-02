"""
LLM Service for grading exam submissions using DeepSeek Reasoner API.

This module provides a service for integrating with the DeepSeek API to grade
student exam submissions against marking guides.

This is an updated version that works with the latest OpenAI library.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import json
import time
import re
import threading
import importlib.metadata
from packaging import version

from dotenv import load_dotenv

from utils.logger import logger

# Load environment variables
load_dotenv()

class LLMServiceError(Exception):
    """Exception raised for errors in the LLM service."""

    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
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
        model: str = "deepseek-reasoner",
        temperature: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        seed: Optional[int] = 42,
        deterministic: bool = True
    ):
        """
        Initialize the LLM service.

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
            raise LLMServiceError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env")

        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.seed = seed
        self.deterministic = deterministic

        # Log the deterministic mode setting
        if self.deterministic:
            logger.info(f"LLM service initialized in deterministic mode with seed: {self.seed}")
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
            client_params = {
                "api_key": self.api_key,
                "base_url": self.base_url
            }

            # Create the client with appropriate parameters
            self.client = OpenAI(**client_params)
            logger.info(f"LLM service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")

    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        try:
            # Simple availability check - verify API key and client are configured
            if not self.api_key:
                return False
            if not self.client:
                return False
            # Could add a ping test here, but for now just check configuration
            return True
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
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 20
            }

            # Add seed parameter if in deterministic mode
            if self.deterministic and self.seed is not None:
                params["seed"] = self.seed

            response = self.client.chat.completions.create(**params)

            # Check if we got a response
            if hasattr(response, 'choices') and len(response.choices) > 0:
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
        max_score: int = 10
    ) -> Tuple[float, str]:
        """
        Compare a student's submission answer with the model answer from the marking guide.

        Args:
            question: The question being answered
            guide_answer: The model answer from the marking guide
            submission_answer: The student's submission answer
            max_score: The maximum possible score for this question

        Returns:
            Tuple[float, str]: (Score, Feedback)

        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            # Log the start of answer comparison
            logger.info("Preparing to compare answers...")

            # Construct a prompt for the LLM to compare the answers
            system_prompt = """
            You are an educational grading assistant. Your task is to compare a student's answer
            to a model answer from a marking guide and assign a score based on how well the student's
            answer matches the key points and understanding demonstrated in the model answer.

            Follow these guidelines:
            - Assign a score from 0 to the maximum score
            - Consider how well the student's answer addresses the key points in the model answer
            - Be objective and consistent in your evaluation
            - Focus on content accuracy rather than writing style or formatting
            - Provide a brief explanation for your score

            Your response should be in this JSON format:
            {
                "score": <numeric_score>,
                "feedback": "<brief_explanation>",
                "key_points_matched": ["<point1>", "<point2>", ...],
                "key_points_missed": ["<point1>", "<point2>", ...]
            }
            """

            user_prompt = f"""
            Question: {question}

            Model Answer from Marking Guide: {guide_answer}

            Student's Answer: {submission_answer}

            Maximum Possible Score: {max_score}

            Please evaluate the student's answer and provide a score and feedback.
            """

            # Log sending request
            logger.info("Sending request to LLM service...")

            # Make the API call
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 500
            }

            # Add seed parameter if in deterministic mode
            if self.deterministic and self.seed is not None:
                params["seed"] = self.seed

            response = self.client.chat.completions.create(**params)

            # Log processing response
            logger.info("Processing LLM response...")

            # Parse the response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                response_text = response.choices[0].message.content.strip()

                # Log extracting results
                logger.info("Extracting score and feedback...")

                try:
                    # Attempt to parse as JSON
                    result = json.loads(response_text)

                    # Extract score and feedback
                    score = float(result.get("score", 0))
                    feedback = result.get("feedback", "No feedback provided")

                    # Ensure score is within bounds
                    score = max(0, min(score, max_score))

                    # Log completion
                    logger.info("Answer comparison completed successfully")

                    return score, feedback

                except json.JSONDecodeError:
                    # If not valid JSON, extract score and feedback manually
                    logger.warning("Response not in valid JSON format. Extracting manually.")

                    # Try to find a numeric score in the response
                    score_match = re.search(r'score[:\s]+(\d+(?:\.\d+)?)', response_text, re.IGNORECASE)
                    score = float(score_match.group(1)) if score_match else 0

                    # Ensure score is within bounds
                    score = max(0, min(score, max_score))

                    # Log completion with manual extraction
                    logger.info("Answer comparison completed with manual extraction")

                    return score, response_text
            else:
                # Log error
                logger.error("No valid response received from API")
                raise LLMServiceError("No valid response received from API")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            return 0, f"Error parsing response: {str(e)}"
        except (AttributeError, IndexError) as e:
            logger.error(f"Invalid response structure from LLM API: {str(e)}")
            return 0, f"Error processing response: {str(e)}"
        except Exception as e:
            logger.error(f"Answer comparison failed: {str(e)}")
            # Return a default score and error message
            return 0, f"Error: {str(e)}"

    def grade_submission(
        self,
        marking_guide_text: str,
        student_submission_text: str,
        max_tokens: int = 2048
    ) -> Dict:
        """
        Grade a student submission against a marking guide.
        This method works with the mapping service to:
        1. Identify questions and answers in both documents
        2. Score each answer based on similarity to the expected answer

        Args:
            marking_guide_text: Full text of the marking guide
            student_submission_text: Full text of the student submission
            max_tokens: Maximum tokens for the response

        Returns:
            Dict: Grading result with scores and feedback
        """
        # Import here to avoid circular imports
        from src.services.mapping_service import MappingService

        # Create mapping service if needed
        mapping_service = MappingService(llm_service=self)

        # Map the submission to the guide
        mapping_result, mapping_error = mapping_service.map_submission_to_guide(
            marking_guide_text,
            student_submission_text
        )

        if mapping_error:
            return {"status": "error", "message": f"Mapping error: {mapping_error}"}

        # Create grading service
        from src.services.grading_service import GradingService
        grading_service = GradingService(llm_service=self, mapping_service=mapping_service)

        # Grade the submission
        grading_result, grading_error = grading_service.grade_submission(
            marking_guide_text,
            student_submission_text
        )

        if grading_error:
            return {"status": "error", "message": f"Grading error: {grading_error}"}

        return grading_result

    def map_submission_to_guide(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = None
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
                num_questions=num_questions
            )
        else:
            return mapping_service.map_submission_to_guide(
                marking_guide_content,
                student_submission_content
            )
