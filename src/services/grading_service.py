"""
Grading service for evaluating student submissions.

This module provides a service that uses the LLM service to grade
student submissions against marking guides.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from src.services.llm_service import LLMService, LLMServiceError
from src.parsing.parse_guide import MarkingGuide
from utils.logger import logger

class GradingService:
    """
    Service for grading student submissions against marking guides.
    
    This service:
    - Takes raw content from both marking guides and student submissions
    - Sends them to the LLM service for evaluation
    - Formats and returns the grading results
    
    The results include overall scores, detailed feedback, and improvement suggestions.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the grading service.
        
        Args:
            llm_service: LLM service to use for grading (will create new if None)
        """
        try:
            self.llm_service = llm_service or LLMService()
            logger.info("Grading service initialized")
        except LLMServiceError as e:
            logger.error(f"Failed to initialize grading service: {str(e)}")
            raise
    
    def grade_submission(
        self, 
        marking_guide_content: str, 
        student_submission_content: str
    ) -> Tuple[Dict, Optional[str]]:
        """
        Grade a student submission against a marking guide.
        
        Args:
            marking_guide_content: Raw text of the marking guide
            student_submission_content: Raw text of the student submission
            
        Returns:
            Tuple containing:
            - Dict with grading results
            - Error message if any, None otherwise
        """
        try:
            logger.info("Grading submission...")
            
            # Validate inputs
            if not marking_guide_content or not marking_guide_content.strip():
                return {}, "Marking guide content is empty"
                
            if not student_submission_content or not student_submission_content.strip():
                return {}, "Student submission is empty"
            
            # Call LLM service to grade submission
            grading_result = self.llm_service.grade_submission(
                marking_guide_text=marking_guide_content,
                student_submission_text=student_submission_content
            )
            
            logger.info(f"Grading completed with score: {grading_result.get('overall_score', 'N/A')}/{grading_result.get('max_possible_score', 'N/A')}")
            return grading_result, None
            
        except LLMServiceError as e:
            error_msg = f"LLM service error: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg
        except Exception as e:
            error_msg = f"Error grading submission: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg
    
    def save_grading_result(
        self, 
        grading_result: Dict, 
        output_path: str, 
        filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Save grading result to a file.
        
        Args:
            grading_result: Grading result dictionary
            output_path: Path to save the result
            filename: Name of the output file (without extension)
            
        Returns:
            Tuple containing:
            - bool indicating success
            - Error message if failed, None if successful
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Remove file extension if present and add JSON extension
            base_filename = Path(filename).stem
            json_path = os.path.join(output_path, f"{base_filename}_result.json")
            
            # Save as JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(grading_result, f, indent=2)
                
            logger.info(f"Grading result saved to {json_path}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to save grading result: {str(e)}"
            logger.error(error_msg)
            return False, error_msg 