"""
LLM Service for grading exam submissions using DeepSeek Reasoner API.

This module provides a service for integrating with the DeepSeek API to grade
student exam submissions against marking guides.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import json
import time

from openai import OpenAI
from dotenv import load_dotenv

from utils.logger import logger

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
        base_url: str = "https://api.deepseek.com",
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
            # Initialize OpenAI client with DeepSeek configuration
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"LLM service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")
    
    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            LLMServiceError: If all retries fail
        """
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                logger.info(f"Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        # If we get here, all retries failed
        error_msg = f"All {self.max_retries} retries failed: {str(last_exception)}"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)
    
    def grade_submission(
        self, 
        marking_guide_text: str, 
        student_submission_text: str,
        max_tokens: int = 2048
    ) -> Dict:
        """
        Grade a student submission against a marking guide.
        
        Args:
            marking_guide_text: Raw text of the marking guide
            student_submission_text: Raw text of the student submission
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            Dict containing the grading results
            
        Raises:
            LLMServiceError: If the API call fails
        """
        try:
            logger.info("Preparing to grade submission...")
            
            # Construct the prompt
            system_prompt = self._construct_system_prompt()
            user_prompt = self._construct_user_prompt(marking_guide_text, student_submission_text)
            
            # Log prompt for debugging (without full submission/guide text for brevity)
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug("User prompt: <truncated for log brevity>")
            
            # Make API call with retry
            response = self._retry_with_backoff(
                self._call_api,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens
            )
            
            # Process and validate the response
            processed_response = self._process_response(response)
            logger.info("Successfully graded submission")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error grading submission: {str(e)}")
            raise LLMServiceError(f"Failed to grade submission: {str(e)}")
    
    def _call_api(
        self, 
        system_prompt: str, 
        user_prompt: str,
        max_tokens: int
    ) -> Dict:
        """
        Make an API call to DeepSeek.
        
        Args:
            system_prompt: System prompt for the API call
            user_prompt: User prompt for the API call
            max_tokens: Maximum number of tokens in the response
            
        Returns:
            Dict containing the API response
            
        Raises:
            Exception: If the API call fails
        """
        try:
            logger.info(f"Calling DeepSeek API with model: {self.model}")
            
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            elapsed_time = time.time() - start_time
            
            logger.info(f"API call completed in {elapsed_time:.2f}s")
            logger.debug(f"Raw API response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
    
    def _construct_system_prompt(self) -> str:
        """
        Construct the system prompt for the grading task.
        
        Returns:
            str: The system prompt
        """
        return (
            "You are an expert engineering exam grader. Your task is to grade student submissions against marking guides.\n"
            "Be objective, thorough, and consistent in your assessment. Provide clear justification for your scoring.\n"
            "Output your assessment in JSON format with the following structure:\n"
            "{\n"
            "  \"overall_score\": <numeric score>,\n"
            "  \"max_possible_score\": <maximum possible score>,\n"
            "  \"percent_score\": <score as a percentage>,\n"
            "  \"detailed_feedback\": {\n"
            "    \"strengths\": [<list of submission strengths>],\n"
            "    \"weaknesses\": [<list of submission weaknesses>],\n"
            "    \"improvement_suggestions\": [<list of improvement suggestions>]\n"
            "  },\n"
            "  \"assessment_confidence\": <high/medium/low>,\n"
            "  \"grading_notes\": \"<any notes on the grading process>\"\n"
            "}\n"
        )
    
    def _construct_user_prompt(self, marking_guide: str, submission: str) -> str:
        """
        Construct the user prompt containing the marking guide and submission.
        
        Args:
            marking_guide: Raw text of the marking guide
            submission: Raw text of the student submission
            
        Returns:
            str: The user prompt
        """
        return (
            "Please grade the following student submission against the provided marking guide.\n\n"
            "# MARKING GUIDE\n"
            f"{marking_guide}\n\n"
            "# STUDENT SUBMISSION\n"
            f"{submission}\n\n"
            "Analyze how well the student submission addresses the requirements in the marking guide. "
            "Provide a fair and objective assessment in the required JSON format."
        )
    
    def _process_response(self, response) -> Dict:
        """
        Process and validate the API response.
        
        Args:
            response: Raw API response
            
        Returns:
            Dict: Processed response
            
        Raises:
            LLMServiceError: If response processing fails
        """
        try:
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Parse the JSON content
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {content}")
                # Attempt to extract JSON if it's embedded in a larger text
                import re
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                    except:
                        raise LLMServiceError("Invalid JSON response format")
                else:
                    raise LLMServiceError("Invalid JSON response format")
            
            # Validate the result structure
            required_keys = ['overall_score', 'max_possible_score', 'detailed_feedback']
            for key in required_keys:
                if key not in result:
                    logger.warning(f"Missing key in response: {key}")
                    # If missing key, add placeholder to prevent downstream errors
                    if key == 'overall_score':
                        result[key] = 0
                    elif key == 'max_possible_score':
                        result[key] = 100
                    elif key == 'detailed_feedback':
                        result[key] = {
                            'strengths': ['No strengths identified'],
                            'weaknesses': ['No weaknesses identified'],
                            'improvement_suggestions': ['No improvement suggestions provided']
                        }
            
            # Ensure percent_score is present and calculated correctly
            if 'percent_score' not in result:
                if result['max_possible_score'] > 0:
                    result['percent_score'] = round(
                        (result['overall_score'] / result['max_possible_score']) * 100, 2
                    )
                else:
                    result['percent_score'] = 0
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process response: {str(e)}")
            raise LLMServiceError(f"Failed to process response: {str(e)}") 