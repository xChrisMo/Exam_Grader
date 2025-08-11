"""
Guide Processing Router

This module routes marking guides to appropriate processing pipelines based on
file type, user preferences, and system configuration.
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from src.config.unified_config import config
from utils.logger import logger


class ProcessingMethod(Enum):
    """Available processing methods for marking guides."""
    TRADITIONAL_OCR = "traditional_ocr"
    AUTO_SELECT = "auto_select"


@dataclass
class ProcessingResult:
    """Result of guide processing operation."""
    success: bool
    processing_method: str
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    fallback_used: bool = False
    metadata: Optional[Dict[str, Any]] = None


class GuideProcessingRouter:
    """Routes marking guides to appropriate processing pipeline."""
    
    def __init__(self):
        """Initialize the guide processing router."""
        self.direct_llm_enabled = False  # Disabled - using existing services
        self.default_method = ProcessingMethod(os.getenv("DEFAULT_GUIDE_PROCESSING_METHOD", "traditional_ocr"))
        self.allow_method_selection = os.getenv("ALLOW_GUIDE_PROCESSING_METHOD_SELECTION", "true").lower() == "true"
        
        # Supported formats for direct LLM processing
        self.llm_supported_formats = {
            '.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'
        }
        
        # File size limits removed - unlimited processing
        self.max_file_size_mb = float('inf')  # No limit
        
        logger.info(f"GuideProcessingRouter initialized - Using existing services, Default: {self.default_method.value}")
    
    def determine_processing_method(self, file_info: Dict[str, Any], user_preference: Optional[str] = None) -> ProcessingMethod:
        """
        Determine the best processing method for a guide file.
        
        Args:
            file_info: Dictionary containing file metadata (path, size, type, etc.)
            user_preference: Optional user-specified processing method
            
        Returns:
            ProcessingMethod enum indicating the chosen method
        """
        try:
            # Check if direct LLM processing is enabled
            if not self.direct_llm_enabled:
                logger.info("Direct LLM processing disabled, using traditional OCR")
                return ProcessingMethod.TRADITIONAL_OCR
            
            # Honor user preference if allowed and valid
            if user_preference and self.allow_method_selection:
                try:
                    preferred_method = ProcessingMethod(user_preference)
                    if self._is_method_viable(preferred_method, file_info):
                        logger.info(f"Using user-preferred method: {preferred_method.value}")
                        return preferred_method
                    else:
                        logger.warning(f"User preference {user_preference} not viable for file, using auto-selection")
                except ValueError:
                    logger.warning(f"Invalid user preference: {user_preference}, using auto-selection")
            
            # Auto-select based on file characteristics
            return self._auto_select_method(file_info)
            
        except Exception as e:
            logger.error(f"Error determining processing method: {e}")
            return ProcessingMethod.TRADITIONAL_OCR  # Safe fallback
    
    def _auto_select_method(self, file_info: Dict[str, Any]) -> ProcessingMethod:
        """
        Automatically select the best processing method based on file characteristics.
        
        Args:
            file_info: Dictionary containing file metadata
            
        Returns:
            ProcessingMethod enum
        """
        file_path = file_info.get('path', '')
        file_size = file_info.get('size', 0)
        
        # Get file extension
        file_ext = Path(file_path).suffix.lower()
        
        # File size limits removed - unlimited processing
        file_size_mb = file_size / (1024 * 1024) if file_size else 0
        logger.info(f"Processing file of size {file_size_mb:.1f}MB with unlimited processing")
        
        # Check if format is supported by LLM vision
        if file_ext not in self.llm_supported_formats:
            logger.info(f"File format {file_ext} not supported by LLM vision, using traditional OCR")
            return ProcessingMethod.TRADITIONAL_OCR
        
        # All files use traditional OCR with existing services
        logger.info(f"File detected: {file_ext}, using traditional OCR with existing services")
        
        # Default to configured default method
        logger.info(f"Using default processing method: {self.default_method.value}")
        return self.default_method
    
    def _is_method_viable(self, method: ProcessingMethod, file_info: Dict[str, Any]) -> bool:
        """
        Check if a processing method is viable for the given file.
        
        Args:
            method: Processing method to check
            file_info: File metadata
            
        Returns:
            True if method is viable, False otherwise
        """
        if method == ProcessingMethod.TRADITIONAL_OCR:
            return True  # Traditional OCR can handle any file
        
        # Direct LLM processing is no longer supported
        # All processing uses traditional OCR with existing services
        
        return False
    
    def route_guide_processing(self, guide_id: str, file_path: str, options: Dict[str, Any]) -> ProcessingResult:
        """
        Route guide processing to the appropriate pipeline.
        
        Args:
            guide_id: Unique identifier for the guide
            file_path: Path to the guide file
            options: Processing options including user preferences
            
        Returns:
            ProcessingResult with processing outcome
        """
        import time
        start_time = time.time()
        
        try:
            # Gather file information
            file_info = self._gather_file_info(file_path)
            file_info['guide_id'] = guide_id
            
            # Determine processing method
            user_preference = options.get('processing_method')
            processing_method = self.determine_processing_method(file_info, user_preference)
            
            logger.info(f"Routing guide {guide_id} to {processing_method.value} processing")
            
            # Route to appropriate processor (all processing now uses traditional OCR with existing services)
            result = self._process_with_traditional_ocr(file_path, file_info, options)
            
            # Update result with routing metadata
            result.processing_method = processing_method.value
            result.processing_time = time.time() - start_time
            
            if not result.metadata:
                result.metadata = {}
            result.metadata.update({
                'routing_method': processing_method.value,
                'file_info': file_info,
                'processing_options': options
            })
            
            logger.info(f"Guide {guide_id} processing completed in {result.processing_time:.2f}s using {processing_method.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error routing guide processing for {guide_id}: {e}")
            return ProcessingResult(
                success=False,
                processing_method="error",
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _gather_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Gather information about the file for processing decisions.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            path_obj = Path(file_path)
            
            file_info = {
                'path': file_path,
                'name': path_obj.name,
                'extension': path_obj.suffix.lower(),
                'exists': path_obj.exists()
            }
            
            if path_obj.exists():
                stat = path_obj.stat()
                file_info.update({
                    'size': stat.st_size,
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified_time': stat.st_mtime
                })
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error gathering file info for {file_path}: {e}")
            return {
                'path': file_path,
                'name': Path(file_path).name,
                'extension': Path(file_path).suffix.lower(),
                'exists': False,
                'error': str(e)
            }
    

    
    def _process_with_traditional_ocr(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process guide using traditional OCR method with existing services for criteria extraction.
        
        Args:
            file_path: Path to the guide file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult
        """
        try:
            # Import here to avoid circular dependencies
            from src.services.file_processing_service import FileProcessingService
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            from src.services.consolidated_mapping_service import ConsolidatedMappingService
            
            file_processor = FileProcessingService()
            llm_service = ConsolidatedLLMService()
            mapping_service = ConsolidatedMappingService(llm_service)
            
            # Step 1: Extract text content using traditional OCR
            traditional_file_info = {
                'path': file_path,
                'name': file_info.get('name', ''),
                'size': file_info.get('size', 0),
                'type': file_info.get('extension', ''),
                'user_id': options.get('user_id'),
                'request_id': options.get('request_id', f"guide_proc_{int(time.time())}")
            }
            
            extraction_result = file_processor.process_file_with_fallback(file_path, traditional_file_info)
            
            if not extraction_result.get('success', False):
                return ProcessingResult(
                    success=False,
                    processing_method="traditional_ocr_with_llm",
                    error_message=f"Failed to extract content: {extraction_result.get('error_message', 'Unknown error')}"
                )
            
            # Step 2: Extract text content from the result
            extracted_text = ""
            if 'extracted_text' in extraction_result:
                extracted_text = extraction_result['extracted_text']
            elif 'content' in extraction_result:
                extracted_text = extraction_result['content']
            elif 'text' in extraction_result:
                extracted_text = extraction_result['text']
            
            if not extracted_text or not extracted_text.strip():
                return ProcessingResult(
                    success=False,
                    processing_method="traditional_ocr_with_llm",
                    error_message="No text content extracted from file"
                )
            
            # Step 3: Analyze guide type using existing mapping service
            guide_type, confidence = mapping_service.determine_guide_type(extracted_text)
            
            # Step 4: Extract criteria using existing LLM service
            criteria_data = self._extract_criteria_with_existing_llm(
                extracted_text, 
                guide_type,
                options,
                llm_service
            )
            
            # Convert to ProcessingResult format with criteria extraction
            return ProcessingResult(
                success=True,
                processing_method="traditional_ocr_with_llm",
                data={
                    'extracted_criteria': criteria_data,
                    'extracted_text': extracted_text,
                    'guide_type': guide_type,
                    'guide_type_confidence': confidence,
                    'extraction_metadata': extraction_result
                },
                metadata={
                    'text_length': len(extracted_text),
                    'criteria_count': len(criteria_data),
                    'guide_type': guide_type,
                    'processing_steps': ['traditional_ocr', 'guide_type_analysis', 'criteria_extraction']
                }
            )
            
        except Exception as e:
            logger.error(f"Traditional OCR processing with LLM analysis failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="traditional_ocr_with_llm",
                error_message=f"Traditional OCR processing failed: {str(e)}"
            )
    
    def get_supported_formats(self, method: ProcessingMethod) -> set:
        """
        Get supported file formats for a processing method.
        
        Args:
            method: Processing method
            
        Returns:
            Set of supported file extensions
        """
        if method == ProcessingMethod.TRADITIONAL_OCR:
            # Traditional OCR supports more formats
            return {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.rtf', '.html'}
        else:
            return set()
    
    def get_processing_capabilities(self) -> Dict[str, Any]:
        """
        Get current processing capabilities and configuration.
        
        Returns:
            Dictionary with capability information
        """
        return {
            'existing_services_enabled': True,
            'default_method': self.default_method.value,
            'allow_method_selection': self.allow_method_selection,
            'max_file_size_mb': self.max_file_size_mb,
            'supported_formats': {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.rtf', '.html'},
            'available_methods': [method.value for method in ProcessingMethod]
        }
    
    def _extract_criteria_with_existing_llm(
        self, 
        text_content: str, 
        guide_type: str,
        options: Dict[str, Any],
        llm_service
    ) -> list:
        """
        Extract grading criteria from text using existing LLM service
        
        Args:
            text_content: Extracted text content
            guide_type: Type of guide (questions/answers)
            options: Processing options
            llm_service: LLM service instance
            
        Returns:
            List of extracted criteria dictionaries
        """
        try:
            import json
            
            # Create system prompt for criteria extraction based on guide type
            if guide_type == "questions":
                system_prompt = """You are an expert at analyzing marking guides that contain questions.
                
Your task is to analyze the provided marking guide text and extract individual questions with their grading criteria.

### JSON Output Format Required:

You MUST return your response as a valid JSON array with this exact structure:

```json
[
  {
    "question_text": "Complete question text here",
    "expected_answer": "Brief description of what the answer should contain",
    "point_value": 5,
    "marks_allocated": 5,
    "rubric_details": "Additional grading criteria or rubric details",
    "question_number": "1",
    "subquestions": [
      {
        "number": "1a",
        "text": "Sub-question text if applicable",
        "points": 2
      }
    ]
  }
]
```

### Field Specifications:
- `question_text`: Complete question or task description (string, required)
- `expected_answer`: What the answer should contain (string, optional)
- `point_value`: Numeric point value (integer, required - use 1 if not specified)
- `marks_allocated`: Same as point_value for compatibility (integer, required)
- `rubric_details`: Additional grading criteria (string, optional)
- `question_number`: Question identifier (string, optional)
- `subquestions`: Array of sub-questions if applicable (array, optional)

### Rules:
- Always return valid JSON array - no markdown code blocks or extra text
- Never invent content; only use what is in the source text
- If no clear questions found, return empty array []
- Ensure all point values are integers (use 1 as default if not specified)
- Preserve original question wording as much as possible"""
            else:
                system_prompt = """You are an expert at analyzing marking guides that contain model answers.
                
Your task is to analyze the provided marking guide text and extract individual answer criteria.

### JSON Output Format Required:

You MUST return your response as a valid JSON array with this exact structure:

```json
[
  {
    "question_text": "Question or topic being addressed",
    "expected_answer": "The model answer or expected response",
    "point_value": 5,
    "marks_allocated": 5,
    "rubric_details": "Additional grading criteria or rubric details",
    "answer_components": [
      {
        "component": "Key point or concept",
        "points": 2,
        "description": "Detailed explanation of what earns these points"
      }
    ]
  }
]
```

### Field Specifications:
- `question_text`: Question or topic being addressed (string, required)
- `expected_answer`: Model answer or expected response (string, required)
- `point_value`: Numeric point value (integer, required - use 1 if not specified)
- `marks_allocated`: Same as point_value for compatibility (integer, required)
- `rubric_details`: Additional grading criteria (string, optional)
- `answer_components`: Breakdown of answer components with points (array, optional)

### Rules:
- Always return valid JSON array - no markdown code blocks or extra text
- Never invent content; only use what is in the source text
- If no clear answers found, return empty array []
- Ensure all point values are integers (use 1 as default if not specified)
- Preserve original answer content as much as possible"""

            # Create user prompt with the text content
            user_prompt = f"""Please analyze this marking guide text and extract the grading criteria in the specified JSON format:

MARKING GUIDE TEXT:
{text_content}

PROCESSING PARAMETERS:
- Guide type: {guide_type}
- Max questions to extract: {options.get('max_questions', 'unlimited')}

IMPORTANT: Return ONLY valid JSON array as specified in the system prompt. No additional text, explanations, or markdown formatting.

If no clear criteria can be extracted, return: []"""

            # Use LLM service to extract criteria
            response = llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            if not response:
                logger.warning("LLM service returned empty response")
                return []
            
            # Parse the JSON response
            try:
                criteria_data = json.loads(response)
                if not isinstance(criteria_data, list):
                    logger.warning("LLM response is not a list, wrapping in array")
                    criteria_data = [criteria_data] if criteria_data else []
                
                # Validate and clean criteria data
                validated_criteria = []
                for i, criterion in enumerate(criteria_data):
                    if not isinstance(criterion, dict):
                        logger.debug(f"Skipping non-dict criterion at index {i}: {type(criterion)}")
                        continue
                    
                    try:
                        # Ensure required fields exist with safe extraction
                        point_value = self._extract_numeric_value(criterion, ['point_value', 'marks_allocated', 'points', 'marks'])
                        marks_allocated = self._extract_numeric_value(criterion, ['marks_allocated', 'point_value', 'points', 'marks'])
                        
                        # Use the higher value if they differ, or default to 1 if both are 0
                        final_points = max(point_value, marks_allocated) or 1
                        
                        validated_criterion = {
                            'question_text': str(criterion.get('question_text', f'Question {i+1}')).strip() or f'Question {i+1}',
                            'expected_answer': str(criterion.get('expected_answer', '')).strip(),
                            'point_value': final_points,
                            'marks_allocated': final_points,
                            'rubric_details': str(criterion.get('rubric_details', criterion.get('details', ''))).strip()
                        }
                    except Exception as e:
                        logger.warning(f"Error processing criterion {i}: {e}, using defaults")
                        validated_criterion = {
                            'question_text': f'Question {i+1}',
                            'expected_answer': '',
                            'point_value': 1,
                            'marks_allocated': 1,
                            'rubric_details': ''
                        }
                    
                    validated_criteria.append(validated_criterion)
                    
                    # Limit number of questions if specified
                    max_questions = options.get('max_questions')
                    if max_questions and len(validated_criteria) >= max_questions:
                        break
                
                logger.info(f"Extracted {len(validated_criteria)} criteria from text using existing LLM service")
                return validated_criteria
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Try to extract criteria using fallback method
                return self._extract_criteria_fallback(response, options)
            
        except Exception as e:
            logger.error(f"Failed to extract criteria with existing LLM service: {e}")
            return []
    
    def _extract_numeric_value(self, data: Dict[str, Any], keys: list) -> int:
        """
        Extract numeric value from dictionary using multiple possible keys
        
        Args:
            data: Dictionary to search
            keys: List of keys to try
            
        Returns:
            Extracted integer value or 0 if not found
        """
        if not isinstance(data, dict) or not keys:
            return 0
            
        for key in keys:
            if key in data:
                try:
                    value = data[key]
                    
                    # Handle None values
                    if value is None:
                        continue
                        
                    # Handle numeric values
                    if isinstance(value, (int, float)):
                        # Ensure the value is reasonable (0-1000 points)
                        int_value = int(value)
                        return max(0, min(int_value, 1000))
                        
                    elif isinstance(value, str) and value.strip():
                        # Try to extract number from string
                        import re
                        # Look for numbers in the string
                        match = re.search(r'\d+', value.strip())
                        if match:
                            int_value = int(match.group())
                            return max(0, min(int_value, 1000))
                            
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to extract numeric value from {key}={value}: {e}")
                    continue
                    
        return 0
    
    def _extract_criteria_fallback(self, llm_response: str, options: Dict[str, Any]) -> list:
        """
        Fallback method to extract criteria when JSON parsing fails
        
        Args:
            llm_response: Raw LLM response text
            options: Processing options
            
        Returns:
            List of extracted criteria
        """
        try:
            criteria = []
            lines = llm_response.split('\n')
            
            current_criterion = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for question patterns
                if any(keyword in line.lower() for keyword in ['question', 'q:', 'criterion', 'task']):
                    if current_criterion:
                        criteria.append(current_criterion)
                    current_criterion = {'question_text': line}
                
                # Look for answer patterns
                elif any(keyword in line.lower() for keyword in ['answer', 'solution', 'expected']):
                    if current_criterion:
                        current_criterion['expected_answer'] = line
                
                # Look for point patterns
                elif any(keyword in line.lower() for keyword in ['point', 'mark', 'score']):
                    if current_criterion:
                        import re
                        match = re.search(r'\d+', line)
                        if match:
                            current_criterion['point_value'] = int(match.group())
                            current_criterion['marks_allocated'] = int(match.group())
            
            # Add the last criterion
            if current_criterion:
                criteria.append(current_criterion)
            
            # Fill in missing fields
            for i, criterion in enumerate(criteria):
                criterion.setdefault('question_text', f'Question {i+1}')
                criterion.setdefault('expected_answer', '')
                criterion.setdefault('point_value', 1)
                criterion.setdefault('marks_allocated', criterion.get('point_value', 1))
                criterion.setdefault('rubric_details', '')
            
            logger.info(f"Extracted {len(criteria)} criteria using fallback method")
            return criteria
            
        except Exception as e:
            logger.error(f"Fallback criteria extraction failed: {e}")
            return []


# Global instance for easy access
guide_processing_router = GuideProcessingRouter()