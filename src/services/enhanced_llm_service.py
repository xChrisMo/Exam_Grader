"""
Enhanced LLM Service with improved prompt engineering and output validation.
Provides better OCR preprocessing, standardized prompts, and robust output validation.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from utils.logger import logger
from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService


class EnhancedLLMService:
    """Enhanced LLM service with improved accuracy and reliability."""
    
    def __init__(self, llm_service):
        """Initialize with existing LLM service."""
        self.llm_service = llm_service
        self.model = llm_service.model if llm_service else None
    
    def preprocess_ocr_text(self, text: str) -> str:
        """
        Preprocess OCR text using LLM to improve understanding.
        
        Args:
            text: Raw OCR text
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        try:
            if self.llm_service:
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
                
                user_prompt = f"Clean and preprocess this OCR text:\n\n{text}"
                
                response = self.llm_service.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1
                )
                
                return response.strip() if response else text
            else:
                # Basic fallback preprocessing without regex
                lines = text.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.isdigit():  # Skip page numbers
                         # Basic character fixes
                         line = line.replace('|', 'I')
                         line = line.replace('"', '"').replace('"', '"')
                         line = line.replace(''', "'").replace(''', "'")
                         cleaned_lines.append(line)
                 
                    return '\n'.join(cleaned_lines)
                 
        except Exception as e:
            logger.warning(f"OCR text preprocessing failed: {e}, using basic cleanup")
            # Basic fallback
            lines = text.split('\n')
            return '\n'.join(line.strip() for line in lines if line.strip())
    
    def get_standardized_grading_prompt(self, guide_type: str, num_questions: int) -> str:
        """
        Get standardized grading prompt for consistent results.
        
        Args:
            guide_type: Type of guide (questions or answers)
            num_questions: Number of questions to grade
            
        Returns:
            str: Standardized system prompt
        """
        base_prompt = f"""
You are an expert educational assessment AI. Your task is to grade student submissions against marking guides.

CRITICAL INSTRUCTIONS:
1. Work with the RAW TEXT provided - do not restructure or extract
2. Handle OCR artifacts gracefully - focus on semantic meaning
3. Ignore minor formatting issues, typos, or OCR noise
4. Look for conceptual understanding, not exact word matches
5. Consider alternative correct approaches
6. Award partial credit for partially correct answers
7. Provide specific, constructive feedback
8. Respond with ONLY valid JSON - no comments or explanations outside JSON

GRADING CRITERIA:
- Content Accuracy (40%): Correctness of facts, concepts, procedures
- Completeness (30%): Inclusion of required information
- Understanding (20%): Demonstrated comprehension
- Clarity (10%): Clear expression of ideas

OUTPUT FORMAT:
{{
    "mappings": [
        {{
            "guide_id": "g1",
            "guide_text": "question text",
            "guide_answer": "model answer",
            "max_score": 10,
            "submission_id": "s1", 
            "submission_text": "student answer",
            "match_score": 0.85,
            "match_reason": "semantic match on topic X",
            "grade_score": 8.5,
            "grade_percentage": 85.0,
            "grade_feedback": "Excellent understanding of X. Good explanation of Y. Could improve on Z.",
            "strengths": ["clear explanation", "correct methodology"],
            "weaknesses": ["missing detail on Z", "could be more specific"]
        }}
    ],
    "overall_grade": {{
        "total_score": 25.5,
        "max_possible_score": 30.0,
        "percentage": 85.0,
        "letter_grade": "B+"
    }}
}}
"""
        
        if guide_type == "questions":
            return base_prompt + f"""
SPECIFIC GUIDELINES FOR QUESTION-BASED GRADING:
- Identify {num_questions} questions in the marking guide
- Match student answers to corresponding questions
- Grade based on how well answers address the questions
- Look for mark allocations: "(5 marks)", "[10 points]", etc.
"""
        else:
            return base_prompt + f"""
SPECIFIC GUIDELINES FOR ANSWER-BASED GRADING:
- Identify {num_questions} model answers in the marking guide
- Match student answers to corresponding model answers
- Grade based on similarity to model answers
- Consider alternative valid approaches
"""
    
    def validate_llm_output(self, output: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and clean LLM output.
        
        Args:
            output: Raw LLM output
            
        Returns:
            Tuple[Dict, List]: (Cleaned output, List of validation errors)
        """
        errors = []
        
        try:
            # Clean the output
            cleaned_output = self._clean_json_output(output)
            
            # Parse JSON
            parsed = json.loads(cleaned_output)
            
            # Validate structure
            if not isinstance(parsed, dict):
                errors.append("Output is not a valid JSON object")
                return {}, errors
            
            # Validate required fields
            if 'mappings' not in parsed:
                errors.append("Missing 'mappings' field")
            if 'overall_grade' not in parsed:
                errors.append("Missing 'overall_grade' field")
            
            # Validate mappings
            mappings = parsed.get('mappings', [])
            if not isinstance(mappings, list):
                errors.append("'mappings' must be a list")
            else:
                for i, mapping in enumerate(mappings):
                    mapping_errors = self._validate_mapping(mapping, i)
                    errors.extend(mapping_errors)
            
            # Validate overall grade
            overall_grade = parsed.get('overall_grade', {})
            grade_errors = self._validate_overall_grade(overall_grade)
            errors.extend(grade_errors)
            
            # If there are critical errors, return empty result
            if any("Missing" in error for error in errors):
                return {}, errors
            
            # Clean and normalize the data
            cleaned_parsed = self._normalize_output(parsed)
            
            return cleaned_parsed, errors
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            return {}, errors
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {}, errors
    
    def _clean_json_output(self, output: str) -> str:
        """Clean JSON output from LLM using LLM-only approach."""
        try:
            if self.llm_service:
                # Use LLM to clean and extract JSON
                system_prompt = """
You are a JSON cleaning expert. Extract and clean valid JSON from the provided text.
Rules:
1. Extract only the JSON object from the text
2. Remove any comments or explanations
3. Fix common JSON formatting issues
4. Convert single quotes to double quotes
5. Remove trailing commas
6. Return only valid JSON, no explanations
"""
                
                user_prompt = f"Extract and clean valid JSON from this text:\n\n{output}"
                
                response = self.llm_service.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1
                )
                
                return response.strip() if response else output
            else:
                # Basic fallback cleaning without regex
                # Remove any text before the first {
                start_idx = output.find('{')
                if start_idx != -1:
                    output = output[start_idx:]
                
                # Remove any text after the last }
                end_idx = output.rfind('}')
                if end_idx != -1:
                    output = output[:end_idx + 1]
                
                # Basic quote fixes
                output = output.replace("'", '"')
                
                return output
                
        except Exception as e:
            logger.warning(f"JSON cleaning failed: {e}, using basic extraction")
            # Basic fallback
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            if start_idx != -1 and end_idx != -1:
                return output[start_idx:end_idx + 1]
            return output
    
    def _validate_mapping(self, mapping: Dict[str, Any], index: int) -> List[str]:
        """Validate individual mapping."""
        errors = []
        
        required_fields = ['guide_id', 'guide_text', 'submission_text', 'max_score']
        for field in required_fields:
            if field not in mapping:
                errors.append(f"Mapping {index}: Missing required field '{field}'")
        
        # Validate data types
        if 'max_score' in mapping and not isinstance(mapping['max_score'], (int, float)):
            errors.append(f"Mapping {index}: max_score must be a number")
        
        if 'match_score' in mapping:
            score = mapping['match_score']
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                errors.append(f"Mapping {index}: match_score must be between 0 and 1")
        
        if 'grade_score' in mapping and not isinstance(mapping['grade_score'], (int, float)):
            errors.append(f"Mapping {index}: grade_score must be a number")
        
        return errors
    
    def _validate_overall_grade(self, overall_grade: Dict[str, Any]) -> List[str]:
        """Validate overall grade structure."""
        errors = []
        
        required_fields = ['total_score', 'max_possible_score', 'percentage', 'letter_grade']
        for field in required_fields:
            if field not in overall_grade:
                errors.append(f"Overall grade: Missing required field '{field}'")
        
        # Validate data types
        if 'total_score' in overall_grade and not isinstance(overall_grade['total_score'], (int, float)):
            errors.append("Overall grade: total_score must be a number")
        
        if 'percentage' in overall_grade:
            percentage = overall_grade['percentage']
            if not isinstance(percentage, (int, float)) or percentage < 0 or percentage > 100:
                errors.append("Overall grade: percentage must be between 0 and 100")
        
        return errors
    
    def _normalize_output(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and clean the parsed output."""
        # Ensure all mappings have required fields with defaults
        for mapping in parsed.get('mappings', []):
            mapping.setdefault('guide_answer', '')
            mapping.setdefault('match_score', 0.5)
            mapping.setdefault('match_reason', '')
            mapping.setdefault('grade_score', 0)
            mapping.setdefault('grade_percentage', 0)
            mapping.setdefault('grade_feedback', '')
            mapping.setdefault('strengths', [])
            mapping.setdefault('weaknesses', [])
            
            # Ensure lists are actually lists
            if not isinstance(mapping.get('strengths'), list):
                mapping['strengths'] = []
            if not isinstance(mapping.get('weaknesses'), list):
                mapping['weaknesses'] = []
        
        # Ensure overall grade has required fields
        overall_grade = parsed.get('overall_grade', {})
        overall_grade.setdefault('total_score', 0)
        overall_grade.setdefault('max_possible_score', 0)
        overall_grade.setdefault('percentage', 0)
        overall_grade.setdefault('letter_grade', 'F')
        
        return parsed
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def grade_submission_enhanced(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = 1,
        guide_type: str = "questions"
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Enhanced grading with improved prompts and validation.
        
        Args:
            marking_guide_content: Preprocessed marking guide content
            student_submission_content: Preprocessed student submission content
            num_questions: Number of questions to grade
            guide_type: Type of guide (questions or answers)
            
        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message if any)
        """
        try:
            if not self.llm_service:
                raise Exception("LLM service not available")
            
            # Preprocess content
            marking_guide_content = self.preprocess_ocr_text(marking_guide_content)
            student_submission_content = self.preprocess_ocr_text(student_submission_content)
            
            # Get standardized prompt
            system_prompt = self.get_standardized_grading_prompt(guide_type, num_questions)
            
            # Create user prompt
            user_prompt = f"""
MARKING GUIDE CONTENT:
{marking_guide_content}

STUDENT SUBMISSION CONTENT:
{student_submission_content}

REQUIREMENTS:
- Grade exactly {num_questions} questions/answers
- Work with the raw text provided
- Handle any OCR artifacts gracefully
- Focus on semantic understanding
- Provide comprehensive feedback

CRITICAL: Respond with ONLY valid JSON. No comments or explanations outside the JSON object.
"""
            
            # Call LLM
            params = {
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
            }
            
            # Add seed for deterministic results if available
            if (
                hasattr(self.llm_service, "deterministic")
                and self.llm_service.deterministic
                and hasattr(self.llm_service, "seed")
                and self.llm_service.seed is not None
            ):
                params["seed"] = self.llm_service.seed
            
            response = self.llm_service.client.chat.completions.create(**params)
            result = response.choices[0].message.content
            
            # Validate and clean output
            validated_result, validation_errors = self.validate_llm_output(result)
            
            if validation_errors:
                logger.warning(f"LLM output validation warnings: {validation_errors}")
            
            if not validated_result:
                raise Exception(f"Failed to validate LLM output: {validation_errors}")
            
            return validated_result, None
            
        except Exception as e:
            logger.error(f"Enhanced grading failed: {str(e)}")
            return {}, str(e)


# Global instance
enhanced_llm_service = None


def init_enhanced_llm_service(llm_service):
    """Initialize enhanced LLM service."""
    global enhanced_llm_service
    enhanced_llm_service = EnhancedLLMService(llm_service)
    return enhanced_llm_service