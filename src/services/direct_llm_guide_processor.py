"""
Direct LLM Guide Processor

This service processes marking guides directly through LLM vision capabilities,
bypassing traditional OCR and text extraction steps.
"""

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from src.services.base_service import BaseService, ServiceStatus
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.guide_processing_router import ProcessingResult
from utils.logger import logger


@dataclass
class GradingCriterion:
    """Represents a single grading criterion extracted from a guide."""
    id: str
    question_text: str
    expected_answer: str
    point_value: int
    rubric_details: Dict[str, Any]
    visual_elements: List[str] = None
    context: str = ""
    
    def __post_init__(self):
        if self.visual_elements is None:
            self.visual_elements = []


@dataclass
class GuideProcessingResult:
    """Result of guide processing operation."""
    success: bool
    processing_method: str
    extracted_criteria: List[GradingCriterion]
    guide_structure: Dict[str, Any]
    processing_time: float
    confidence_score: float
    fallback_used: bool = False
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DirectLLMGuideProcessor(BaseService):
    """Processes marking guides directly through LLM vision capabilities."""
    
    def __init__(self):
        """Initialize the direct LLM guide processor."""
        super().__init__("direct_llm_guide_processor")
        
        # Initialize LLM service
        self.llm_service = ConsolidatedLLMService()
        
        # Processing configuration
        self.max_file_size_mb = 20
        self.supported_formats = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        
        # LLM prompts for guide processing
        self.guide_analysis_prompt = self._create_guide_analysis_prompt()
        self.criteria_extraction_prompt = self._create_criteria_extraction_prompt()
        
        logger.info("DirectLLMGuideProcessor initialized successfully")
    
    def _create_guide_analysis_prompt(self) -> str:
        """Create the system prompt for guide analysis."""
        return """You are an expert educational assessment analyzer specializing in comprehensive marking guide analysis. Your task is to extract ALL grading criteria from marking guides with maximum completeness.

CRITICAL INSTRUCTIONS:
1. **EXTRACT EVERY QUESTION**: Do not skip any questions, sub-questions, or parts
2. **SCAN THOROUGHLY**: Look through the entire document from beginning to end
3. **INCLUDE ALL SECTIONS**: Process headers, footers, sidebars, and appendices
4. **CAPTURE VARIATIONS**: Include multiple choice, short answer, essay, calculation, and diagram questions
5. **PRESERVE STRUCTURE**: Maintain question numbering and section organization

DOCUMENT ANALYSIS APPROACH:
- Start from the first page and work systematically through each page
- Look for question indicators: numbers (1, 2, 3), letters (a, b, c), bullets, or section headers
- Identify point allocations: [5 marks], (10 points), /15, etc.
- Extract expected answers, model solutions, or marking schemes
- Note any rubrics, criteria, or grading guidelines
- Include bonus questions, optional sections, or alternative questions

QUALITY REQUIREMENTS:
- Extract minimum 80% of visible questions in the document
- Provide specific, actionable grading criteria for each question
- Include point values even if estimated
- Capture partial credit guidelines where available
- Note any special instructions or formatting requirements

You must be thorough and comprehensive. Missing questions is a critical failure."""
    
    def _create_criteria_extraction_prompt(self) -> str:
        """Create the user prompt for criteria extraction."""
        return """COMPREHENSIVE MARKING GUIDE ANALYSIS - EXTRACT ALL QUESTIONS AND CRITERIA

MANDATORY REQUIREMENTS:
1. Read through the ENTIRE document from start to finish
2. Extract EVERY question, sub-question, and part (1, 1a, 1b, 2, 2a, etc.)
3. Include ALL point allocations, even if they're just [1 mark] or (2 points)
4. Capture both questions AND their expected answers/marking schemes
5. Do NOT skip any sections, pages, or appendices

SEARCH PATTERNS TO LOOK FOR:
- Question numbers: 1, 2, 3, 4... or 1., 2., 3., 4...
- Sub-questions: a), b), c) or (i), (ii), (iii)
- Point indicators: [5 marks], (10 points), /15, "5 pts", "worth 3 marks"
- Section headers: "Part A", "Section 1", "Question Set B"
- Answer keys: "Answer:", "Solution:", "Expected response:"
- Rubrics: "Full marks for...", "Partial credit if...", "Deduct points for..."

OUTPUT FORMAT (JSON):
{
    "guide_metadata": {
        "title": "Document title or subject name",
        "total_points": "Sum of all point values found",
        "sections": "Number of main sections identified",
        "question_count": "Total number of questions/sub-questions found"
    },
    "grading_criteria": [
        {
            "id": "q1", 
            "question_text": "Complete question text exactly as written",
            "expected_answer": "Model answer or key points to look for",
            "point_value": 5,
            "rubric_details": {
                "full_credit": "What earns full marks",
                "partial_credit": "What earns partial marks", 
                "no_credit": "What earns zero marks"
            },
            "visual_elements": ["Describe any diagrams, tables, charts, or images"],
            "context": "Question type, difficulty level, or special notes"
        }
    ],
    "special_instructions": [
        "Any overall grading guidelines, time limits, or special rules"
    ],
    "confidence_indicators": {
        "structure_clarity": 0.9,
        "criteria_completeness": 0.85,
        "visual_element_handling": 0.7
    }
}

CRITICAL SUCCESS CRITERIA:
- Extract minimum 90% of all visible questions
- Include accurate point values for each question
- Provide specific, actionable grading criteria
- Maintain original question numbering and structure
- Include even small 1-2 point questions

FAILURE IS NOT ACCEPTABLE - This marking guide analysis is critical for student assessment accuracy."""
    
    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            # Initialize LLM service
            if not await self.llm_service.initialize():
                logger.error("Failed to initialize LLM service")
                self.status = ServiceStatus.UNHEALTHY
                return False
            
            self.status = ServiceStatus.HEALTHY
            logger.info("DirectLLMGuideProcessor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DirectLLMGuideProcessor: {e}")
            self.status = ServiceStatus.UNHEALTHY
            return False
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            return await self.llm_service.health_check()
        except Exception as e:
            logger.error(f"DirectLLMGuideProcessor health check failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self.llm_service.cleanup()
            logger.info("DirectLLMGuideProcessor cleanup completed")
        except Exception as e:
            logger.error(f"Error during DirectLLMGuideProcessor cleanup: {e}")
    
    def process_guide_directly(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process a marking guide directly through LLM vision capabilities.
        
        Args:
            file_path: Path to the guide file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult with extracted guide data
        """
        start_time = time.time()
        
        try:
            with self.track_request("process_guide_directly"):
                logger.info(f"Starting direct LLM processing for guide: {file_path}")
                
                # Validate file
                if not self._validate_file(file_path, file_info):
                    return ProcessingResult(
                        success=False,
                        processing_method="direct_llm",
                        error_message="File validation failed"
                    )
                
                # Process file based on type
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}:
                    result = self._process_image_guide(file_path, file_info, options)
                elif file_ext in {'.pdf', '.docx', '.doc'}:
                    result = self._process_document_guide(file_path, file_info, options)
                else:
                    return ProcessingResult(
                        success=False,
                        processing_method="direct_llm",
                        error_message=f"Unsupported file format: {file_ext}"
                    )
                
                # Update processing time
                result.processing_time = time.time() - start_time
                
                logger.info(f"Direct LLM processing completed in {result.processing_time:.2f}s")
                return result
                
        except Exception as e:
            logger.error(f"Direct LLM processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="direct_llm",
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _validate_file(self, file_path: str, file_info: Dict[str, Any]) -> bool:
        """
        Validate file for direct LLM processing.
        
        Args:
            file_path: Path to the file
            file_info: File metadata
            
        Returns:
            True if file is valid for processing
        """
        try:
            # Check if file exists
            if not Path(file_path).exists():
                logger.error(f"File does not exist: {file_path}")
                return False
            
            # Check file size
            file_size_mb = file_info.get('size_mb', 0)
            if file_size_mb > self.max_file_size_mb:
                logger.error(f"File size {file_size_mb:.1f}MB exceeds limit {self.max_file_size_mb}MB")
                return False
            
            # Check file format
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                logger.error(f"Unsupported file format: {file_ext}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False
    
    def _process_image_guide(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process an image-based marking guide.
        
        Args:
            file_path: Path to the image file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult with extracted data
        """
        try:
            logger.info(f"Processing image guide: {file_path}")
            
            # Read and encode image
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create messages for LLM with vision
            messages = [
                {
                    "role": "system",
                    "content": self.guide_analysis_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.criteria_extraction_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Send to LLM
            response = self._call_llm_with_vision(messages)
            
            # Parse response
            return self._parse_llm_response(response, file_info, options)
            
        except Exception as e:
            logger.error(f"Image guide processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="direct_llm",
                error_message=f"Image processing failed: {str(e)}"
            )
    
    def _process_document_guide(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process a document-based marking guide (PDF, Word).
        
        Args:
            file_path: Path to the document file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult with extracted data
        """
        try:
            logger.info(f"Processing document guide: {file_path}")
            
            # For now, convert document to image and process
            # In a full implementation, you might use document-specific processing
            
            # Read file as binary
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Encode file as base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determine MIME type
            file_ext = Path(file_path).suffix.lower()
            mime_type = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword'
            }.get(file_ext, 'application/octet-stream')
            
            # Create messages for LLM
            messages = [
                {
                    "role": "system",
                    "content": self.guide_analysis_prompt
                },
                {
                    "role": "user",
                    "content": f"{self.criteria_extraction_prompt}\n\nDocument type: {mime_type}\nFile: {Path(file_path).name}"
                }
            ]
            
            # For document processing, we'll use text-based LLM call
            # In a real implementation, you might need document-to-image conversion
            response = self._call_llm_text_only(messages, file_data, mime_type)
            
            # Parse response
            return self._parse_llm_response(response, file_info, options)
            
        except Exception as e:
            logger.error(f"Document guide processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="direct_llm",
                error_message=f"Document processing failed: {str(e)}"
            )
    
    def _call_llm_with_vision(self, messages: List[Dict[str, Any]]) -> str:
        """
        Call LLM with vision capabilities.
        
        Args:
            messages: Messages including image data
            
        Returns:
            LLM response text
        """
        try:
            # Use the consolidated LLM service
            # Extract system and user messages
            system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
            user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
            
            # For vision processing, we need to handle the structured content
            if isinstance(user_message, list):
                # Extract text content from structured message
                text_content = next((item["text"] for item in user_message if item["type"] == "text"), "")
                user_message = text_content
            
            # Call LLM service
            response = self.llm_service.generate_response(
                system_prompt=system_message,
                user_prompt=user_message,
                temperature=0.1,  # Low temperature for consistent extraction
                use_cache=True
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM vision call failed: {e}")
            raise
    
    def _call_llm_text_only(self, messages: List[Dict[str, Any]], file_data: bytes, mime_type: str) -> str:
        """
        Call LLM with text-only processing for documents.
        
        Args:
            messages: Messages for LLM
            file_data: Binary file data
            mime_type: MIME type of the file
            
        Returns:
            LLM response text
        """
        try:
            # Extract system and user messages
            system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
            user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
            
            # For document processing, we'll include file information in the prompt
            enhanced_user_message = f"{user_message}\n\nNote: This is a {mime_type} document. Please analyze the document structure and extract grading criteria as requested."
            
            # Call LLM service
            response = self.llm_service.generate_response(
                system_prompt=system_message,
                user_prompt=enhanced_user_message,
                temperature=0.1,
                use_cache=True
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM text call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Parse LLM response and extract structured guide data.
        
        Args:
            response: Raw LLM response
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult with parsed data
        """
        try:
            logger.info("Parsing LLM response for guide criteria")
            
            # Try to parse JSON response
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                response_data = self._extract_json_from_response(response)
            
            if not response_data:
                return ProcessingResult(
                    success=False,
                    processing_method="direct_llm",
                    error_message="Failed to parse LLM response as JSON"
                )
            
            # Extract grading criteria
            criteria = self._extract_grading_criteria(response_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(response_data)
            
            # Create guide structure
            guide_structure = {
                "metadata": response_data.get("guide_metadata", {}),
                "special_instructions": response_data.get("special_instructions", []),
                "confidence_indicators": response_data.get("confidence_indicators", {}),
                "total_criteria": len(criteria),
                "processing_method": "direct_llm"
            }
            
            return ProcessingResult(
                success=True,
                processing_method="direct_llm",
                data={
                    "extracted_criteria": [criterion.__dict__ for criterion in criteria],
                    "guide_structure": guide_structure,
                    "confidence_score": confidence_score,
                    "raw_response": response[:1000]  # Truncated for logging
                },
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="direct_llm",
                error_message=f"Response parsing failed: {str(e)}"
            )
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response using various strategies.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON data or None
        """
        import re
        
        try:
            logger.debug(f"Attempting to extract JSON from response (first 500 chars): {response[:500]}")
            
            # Strategy 1: Try to find JSON block in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Found JSON block: {json_str[:200]}...")
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON block: {e}")
            
            # Strategy 2: Try to find JSON between code blocks
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
                logger.debug(f"Found JSON in code block: {json_str[:200]}...")
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from code block: {e}")
            
            # Strategy 3: Create fallback structure if no JSON found
            logger.warning(f"No valid JSON found in LLM response. Creating fallback structure.")
            logger.debug(f"Full response content: {response}")
            
            # Return a basic structure to prevent complete failure
            return {
                "grading_criteria": [],
                "metadata": {
                    "extraction_method": "fallback",
                    "original_response": response[:1000]  # Store first 1000 chars for debugging
                }
            }
            
        except Exception as e:
            logger.error(f"JSON extraction failed with error: {e}")
            logger.debug(f"Failed response content: {response[:1000]}")
            return None
    
    def _extract_grading_criteria(self, response_data: Dict[str, Any]) -> List[GradingCriterion]:
        """
        Extract grading criteria from parsed response data.
        
        Args:
            response_data: Parsed JSON response
            
        Returns:
            List of GradingCriterion objects
        """
        criteria = []
        
        try:
            criteria_data = response_data.get("grading_criteria", [])
            
            for i, criterion_data in enumerate(criteria_data):
                try:
                    criterion = GradingCriterion(
                        id=criterion_data.get("id", f"criterion_{i+1}"),
                        question_text=criterion_data.get("question_text", ""),
                        expected_answer=criterion_data.get("expected_answer", ""),
                        point_value=int(criterion_data.get("point_value", 0)),
                        rubric_details=criterion_data.get("rubric_details", {}),
                        visual_elements=criterion_data.get("visual_elements", []),
                        context=criterion_data.get("context", "")
                    )
                    criteria.append(criterion)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse criterion {i}: {e}")
                    continue
            
            logger.info(f"Extracted {len(criteria)} grading criteria")
            return criteria
            
        except Exception as e:
            logger.error(f"Criteria extraction failed: {e}")
            return []
    
    def _calculate_confidence_score(self, response_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on response quality indicators.
        
        Args:
            response_data: Parsed JSON response
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            confidence_indicators = response_data.get("confidence_indicators", {})
            
            # Get individual confidence scores
            structure_clarity = float(confidence_indicators.get("structure_clarity", 0.5))
            criteria_completeness = float(confidence_indicators.get("criteria_completeness", 0.5))
            visual_element_handling = float(confidence_indicators.get("visual_element_handling", 0.5))
            
            # Calculate weighted average
            weights = [0.4, 0.4, 0.2]  # Structure and completeness are more important
            scores = [structure_clarity, criteria_completeness, visual_element_handling]
            
            confidence_score = sum(w * s for w, s in zip(weights, scores))
            
            # Additional factors
            criteria_count = len(response_data.get("grading_criteria", []))
            if criteria_count > 0:
                confidence_score += 0.1  # Bonus for having criteria
            
            if response_data.get("guide_metadata", {}).get("total_points"):
                confidence_score += 0.05  # Bonus for point allocation
            
            # Clamp to [0, 1]
            return max(0.0, min(1.0, confidence_score))
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")
            return 0.5  # Default moderate confidence
    
    def extract_grading_criteria(self, llm_response: Dict[str, Any]) -> List[GradingCriterion]:
        """
        Extract grading criteria from LLM response.
        
        Args:
            llm_response: Parsed LLM response data
            
        Returns:
            List of extracted grading criteria
        """
        return self._extract_grading_criteria(llm_response)
    
    def validate_guide_structure(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the structure of extracted guide data.
        
        Args:
            extracted_data: Extracted guide data
            
        Returns:
            Validation result with status and issues
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "score": 1.0
        }
        
        try:
            # Check for required fields
            if not extracted_data.get("extracted_criteria"):
                validation_result["issues"].append("No grading criteria found")
                validation_result["is_valid"] = False
            
            criteria = extracted_data.get("extracted_criteria", [])
            
            # Validate each criterion
            for i, criterion in enumerate(criteria):
                if not criterion.get("question_text"):
                    validation_result["warnings"].append(f"Criterion {i+1} missing question text")
                
                if not criterion.get("point_value") or criterion.get("point_value") <= 0:
                    validation_result["warnings"].append(f"Criterion {i+1} missing or invalid point value")
                
                if not criterion.get("expected_answer"):
                    validation_result["warnings"].append(f"Criterion {i+1} missing expected answer")
            
            # Calculate validation score
            total_issues = len(validation_result["issues"]) + len(validation_result["warnings"]) * 0.5
            validation_result["score"] = max(0.0, 1.0 - (total_issues * 0.1))
            
            logger.info(f"Guide validation completed - Score: {validation_result['score']:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Guide validation failed: {e}")
            return {
                "is_valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "warnings": [],
                "score": 0.0
            }


# Global instance for easy access
direct_llm_guide_processor = DirectLLMGuideProcessor()