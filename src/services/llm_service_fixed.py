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

    def grade_submission(
        self, 
        marking_guide_text: str, 
        student_submission_text: str,
        max_tokens: int = 2048
    ) -> Dict:
        """Simplified grading function for testing"""
        return {"status": "success", "message": "Grading service is working"}

    def map_submission_to_guide(
        self,
        marking_guide_content: str,
        student_submission_content: str
    ) -> Tuple[Dict, Optional[str]]:
        """Simplified mapping function for testing"""
        return {"status": "success", "message": "Mapping service is working"}, None 