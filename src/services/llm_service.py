"""
LLM Service for grading exam submissions using DeepSeek Reasoner API.

This module provides a service for integrating with the DeepSeek API to grade
student exam submissions against marking guides.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import json
import time
import re
import threading

from openai import OpenAI
from dotenv import load_dotenv

from utils.logger import logger
from src.services.progress_tracker import progress_tracker

# Load environment variables
load_dotenv()

class LLMServiceError(Exception):
    """Exception raised for errors in the LLM service."""
    pass

class LLMService:
    """
    A service for interacting with the DeepSeek LLM to grade exam submissions.

    This class handles:
    - API key management
    - Prompt construction
    - Response handling
    - Rate limiting and retries

    The primary use case is to compare student answers with model answers
    and provide grading with justification.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-reasoner",
        temperature: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 2.0
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

        try:
            # Initialize OpenAI client with DeepSeek configuration - simplified initialization
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"LLM service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=20
            )

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
        max_score: int = 10,
        tracker_id: Optional[str] = None
    ) -> Tuple[float, str, str]:
        """
        Compare a student's submission answer with the model answer from the marking guide.

        Args:
            question: The question being answered
            guide_answer: The model answer from the marking guide
            submission_answer: The student's submission answer
            max_score: The maximum possible score for this question
            tracker_id: Optional progress tracker ID for monitoring progress

        Returns:
            Tuple[float, str, str]: (Score, Feedback, Tracker ID)

        Raises:
            LLMServiceError: If the API call fails
        """
        # Create a progress tracker if not provided
        if not tracker_id:
            tracker_id = progress_tracker.create_tracker(
                operation_type="llm",
                task_name="Answer Comparison",
                total_steps=5
            )

        try:
            # Update progress - Step 1: Starting
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=1,
                status="preparing",
                message="Preparing to compare answers..."
            )

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

            # Update progress - Step 2: Sending request
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=2,
                status="processing",
                message="Sending request to LLM service..."
            )

            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=500
            )

            # Update progress - Step 3: Processing response
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=3,
                status="analyzing",
                message="Processing LLM response..."
            )

            # Parse the response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                response_text = response.choices[0].message.content.strip()

                # Update progress - Step 4: Extracting results
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=4,
                    status="extracting",
                    message="Extracting score and feedback..."
                )

                try:
                    # Attempt to parse as JSON
                    result = json.loads(response_text)

                    # Extract score and feedback
                    score = float(result.get("score", 0))
                    feedback = result.get("feedback", "No feedback provided")

                    # Ensure score is within bounds
                    score = max(0, min(score, max_score))

                    # Update progress - Step 5: Complete
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=5,
                        status="completed",
                        message="Answer comparison completed successfully",
                        completed=True,
                        success=True,
                        result={"score": score, "feedback": feedback}
                    )

                    return score, feedback, tracker_id

                except json.JSONDecodeError:
                    # If not valid JSON, extract score and feedback manually
                    logger.warning("Response not in valid JSON format. Extracting manually.")

                    # Try to find a numeric score in the response
                    score_match = re.search(r'score[:\s]+(\d+(?:\.\d+)?)', response_text, re.IGNORECASE)
                    score = float(score_match.group(1)) if score_match else 0

                    # Ensure score is within bounds
                    score = max(0, min(score, max_score))

                    # Update progress - Step 5: Complete (with manual extraction)
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=5,
                        status="completed",
                        message="Answer comparison completed with manual extraction",
                        completed=True,
                        success=True,
                        result={"score": score, "feedback": response_text}
                    )

                    return score, response_text, tracker_id
            else:
                # Update progress - Error
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    status="failed",
                    message="No valid response received from API",
                    completed=True,
                    success=False,
                    error="No valid response received from API"
                )

                raise LLMServiceError("No valid response received from API")

        except Exception as e:
            logger.error(f"Answer comparison failed: {str(e)}")

            # Update progress - Error
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                status="failed",
                message=f"Answer comparison failed: {str(e)}",
                completed=True,
                success=False,
                error=str(e)
            )

            # Return a default score, error message, and tracker ID
            return 0, f"Error: {str(e)}", tracker_id

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
        student_submission_content: str
    ) -> Tuple[Dict, Optional[str]]:
        """
        Map a student submission to a marking guide.
        This is a wrapper around the mapping service functionality.

        Args:
            marking_guide_content: Full text of the marking guide
            student_submission_content: Full text of the student submission

        Returns:
            Tuple[Dict, Optional[str]]: (Mapping result, Error message if any)
        """
        # Import here to avoid circular imports
        from src.services.mapping_service import MappingService

        # Create mapping service
        mapping_service = MappingService(llm_service=self)

        # Map the submission to the guide
        return mapping_service.map_submission_to_guide(
            marking_guide_content,
            student_submission_content
        )