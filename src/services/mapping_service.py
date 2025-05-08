"""
Mapping service for linking student submissions to marking guide criteria.

This module provides a service that uses the LLM to map sections of student
submissions to specific marking guide criteria or questions.
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
import hashlib

from src.services.llm_service import LLMService, LLMServiceError
from utils.logger import logger

class MappingService:
    """
    Service for mapping student submissions to marking guide criteria.
    
    This service:
    - Analyzes marking guides to extract questions and criteria
    - Identifies relevant parts of student submissions that address each criterion
    - Provides a structured mapping for visualization and grading
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the mapping service.
        
        Args:
            llm_service: LLM service to use for mapping (will create new if None)
        """
        try:
            self.llm_service = llm_service or LLMService(model="deepseek-chat")
            logger.info("Mapping service initialized")
        except LLMServiceError as e:
            logger.error(f"Failed to initialize mapping service: {str(e)}")
            raise
    
    def _generate_cache_key(self, guide_content: str, submission_content: str) -> str:
        """Generate a unique key for caching mapping results."""
        combined = f"{guide_content[:1000]}:::{submission_content[:1000]}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def map_submission_to_guide(
        self, 
        marking_guide_content: str, 
        student_submission_content: str,
        cached_results: Optional[Dict] = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Map sections of a student submission to marking guide criteria.
        
        Args:
            marking_guide_content: Raw text of the marking guide
            student_submission_content: Raw text of the student submission
            cached_results: Optional cached mapping results
            
        Returns:
            Tuple containing:
            - Dict with mapping results
            - Error message if any, None otherwise
        """
        try:
            logger.info("Mapping submission to guide criteria...")
            
            # Check if we already have a cached result
            if cached_results:
                logger.info("Using cached mapping results")
                return cached_results, None
            
            # Validate inputs
            if not marking_guide_content or not marking_guide_content.strip():
                return {}, "Marking guide content is empty"
                
            if not student_submission_content or not student_submission_content.strip():
                return {}, "Student submission is empty"
            
            # Construct the system prompt
            system_prompt = (
                "You are an expert at mapping student answers to marking guide criteria. "
                "Your task is to identify which parts of a student submission correspond to each "
                "criterion or question in a marking guide. Be precise in your analysis and extraction. "
                "Return your output in JSON format with the following structure:\n"
                "{\n"
                "  \"criteria_mappings\": [\n"
                "    {\n"
                "      \"criterion_id\": 1,\n"
                "      \"criterion_text\": \"<text of the criterion/question from the guide>\",\n"
                "      \"mapped_text\": \"<text from the submission that addresses this criterion>\",\n"
                "      \"confidence\": <a score from 0.0 to 1.0 indicating confidence in this mapping>,\n"
                "      \"comments\": \"<brief notes on the quality of the match>\"\n"
                "    },\n"
                "    ...\n"
                "  ],\n"
                "  \"unmapped_guide_sections\": [\"<criterion that wasn't addressed in the submission>\", ...],\n"
                "  \"unmapped_submission_sections\": [\"<submission text that doesn't map to any criterion>\", ...]\n"
                "}\n"
            )
            
            # Construct the user prompt
            user_prompt = (
                "Please analyze the following marking guide and student submission, "
                "then create a mapping that shows which parts of the submission address "
                "each criterion or question in the guide.\n\n"
                "# MARKING GUIDE\n"
                f"{marking_guide_content}\n\n"
                "# STUDENT SUBMISSION\n"
                f"{student_submission_content}\n\n"
                "Provide your mapping analysis in the required JSON format. Focus on finding "
                "the most relevant sections of the submission for each criterion in the guide."
            )
            
            # Call the LLM to generate the mapping
            response = self.llm_service._call_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2048
            )
            
            # Process the response
            mapping_result = self.llm_service._process_response(response)
            
            # Validate the mapping result structure
            required_keys = ['criteria_mappings']
            for key in required_keys:
                if key not in mapping_result:
                    logger.warning(f"Missing key in mapping response: {key}")
                    mapping_result[key] = []
            
            # Add additional optional fields if missing
            if 'unmapped_guide_sections' not in mapping_result:
                mapping_result['unmapped_guide_sections'] = []
            if 'unmapped_submission_sections' not in mapping_result:
                mapping_result['unmapped_submission_sections'] = []
            
            # Add metadata
            mapping_result['metadata'] = {
                'guide_length': len(marking_guide_content),
                'submission_length': len(student_submission_content),
                'mapping_count': len(mapping_result.get('criteria_mappings', [])),
                'unmapped_guide_count': len(mapping_result.get('unmapped_guide_sections', [])),
                'unmapped_submission_count': len(mapping_result.get('unmapped_submission_sections', []))
            }
            
            logger.info(f"Mapping completed with {mapping_result['metadata']['mapping_count']} criteria mapped")
            return mapping_result, None
            
        except LLMServiceError as e:
            error_msg = f"LLM service error during mapping: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg
        except Exception as e:
            error_msg = f"Error mapping submission to guide: {str(e)}"
            logger.error(error_msg)
            return {}, error_msg 