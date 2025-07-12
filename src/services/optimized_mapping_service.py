"""Optimized Mapping Service with batching, structured templates, and enhanced LLM efficiency."""

import json
import re
from typing import Dict, List, Optional, Tuple, Any

from src.services.mapping_service import MappingService
from utils.logger import logger


class OptimizedMappingService(MappingService):
    """Enhanced mapping service with batching and optimized prompts."""

    def __init__(self, llm_service=None):
        """Initialize optimized mapping service."""
        super().__init__(llm_service)
        self.batch_size = 10  # Process multiple Q&A pairs at once
        
    def _clean_and_deduplicate_content(self, content: str) -> str:
        """Clean and deduplicate content to reduce LLM input size."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Remove duplicate lines (common in OCR)
        lines = content.split('\n')
        seen_lines = set()
        unique_lines = []
        
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen_lines:
                seen_lines.add(line_clean)
                unique_lines.append(line.strip())
        
        # Remove common OCR artifacts
        content = '\n'.join(unique_lines)
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', content)  # Remove control chars
        content = re.sub(r'\b(page|\d+|scan|copy|image)\b', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _create_structured_mapping_prompt(self, guide_content: str, submission_content: str, guide_type: str) -> str:
        """Create optimized, structured prompt for mapping."""
        
        # Clean inputs
        guide_clean = self._clean_and_deduplicate_content(guide_content)
        submission_clean = self._clean_and_deduplicate_content(submission_content)
        
        if guide_type.lower() == "questions":
            system_prompt = """You are an expert at mapping student answers to exam questions. Your task is to:
1. Extract questions from the marking guide
2. Extract answers from the student submission
3. Map each answer to its corresponding question
4. Return structured JSON output

Rules:
- Be precise and concise
- Only map clear matches
- Use question numbers/identifiers when available
- Skip unclear or incomplete content"""
            
            user_prompt = f"""MARKING GUIDE (Questions):
{guide_clean[:1500]}

STUDENT SUBMISSION (Answers):
{submission_clean[:2000]}

Return JSON format:
{{
  "mappings": [
    {{
      "question_id": "Q1",
      "question_text": "What is...",
      "answer_text": "Student's answer...",
      "confidence": 0.95
    }}
  ]
}}"""
        else:
            system_prompt = """You are an expert at mapping student answers to answer keys. Your task is to:
1. Extract answer keys from the marking guide
2. Extract student answers from the submission
3. Map student answers to corresponding answer keys
4. Return structured JSON output

Rules:
- Match by question numbers/topics
- Be precise with mappings
- Only include confident matches
- Use clear identifiers"""
            
            user_prompt = f"""MARKING GUIDE (Answer Key):
{guide_clean[:1500]}

STUDENT SUBMISSION (Answers):
{submission_clean[:2000]}

Return JSON format:
{{
  "mappings": [
    {{
      "question_id": "Q1",
      "expected_answer": "Correct answer...",
      "student_answer": "Student's answer...",
      "confidence": 0.90
    }}
  ]
}}"""
        
        return system_prompt, user_prompt
    
    def map_submission_to_guide_optimized(self, guide_content: str, submission_content: str, guide_type: str = None) -> Dict[str, Any]:
        """Optimized mapping with structured prompts and validation."""
        
        if not self.llm_service:
            logger.error("LLM service not available for optimized mapping")
            return self._fallback_mapping(guide_content, submission_content)
        
        # Determine guide type if not provided
        if not guide_type:
            guide_type_result = self.determine_guide_type(guide_content)
            guide_type = guide_type_result.get('type', 'questions')
        
        try:
            # Create structured prompt
            system_prompt, user_prompt = self._create_structured_mapping_prompt(
                guide_content, submission_content, guide_type
            )
            
            # Call LLM with structured prompt
            response = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                # max_tokens=2000,  # Removed token limit
                temperature=0.1  # Low temperature for consistency
            )
            
            # Parse and validate response
            result = self._parse_and_validate_mapping_response(response, guide_type)
            
            if result:
                logger.info(f"Successfully mapped {len(result.get('mappings', []))} items")
                return result
            else:
                logger.warning("LLM mapping failed, using fallback")
                return self._fallback_mapping(guide_content, submission_content)
                
        except Exception as e:
            logger.error(f"Optimized mapping failed: {e}")
            return self._fallback_mapping(guide_content, submission_content)
    
    def _parse_and_validate_mapping_response(self, response: str, guide_type: str) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM mapping response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            result = json.loads(json_match.group())
            
            # Validate structure
            if 'mappings' not in result or not isinstance(result['mappings'], list):
                return None
            
            # Validate each mapping
            valid_mappings = []
            for mapping in result['mappings']:
                if self._validate_mapping_item(mapping, guide_type):
                    valid_mappings.append(mapping)
            
            result['mappings'] = valid_mappings
            return result if valid_mappings else None
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return None
    
    def _validate_mapping_item(self, mapping: Dict, guide_type: str) -> bool:
        """Validate individual mapping item."""
        required_fields = ['question_id']
        
        if guide_type.lower() == "questions":
            required_fields.extend(['question_text', 'answer_text'])
        else:
            required_fields.extend(['expected_answer', 'student_answer'])
        
        # Check required fields
        for field in required_fields:
            if field not in mapping or not mapping[field]:
                return False
        
        # Check confidence if present
        if 'confidence' in mapping:
            try:
                conf = float(mapping['confidence'])
                if not 0 <= conf <= 1:
                    return False
            except (ValueError, TypeError):
                return False
        
        return True
    
    def batch_map_submissions(self, guide_content: str, submissions: List[Dict], guide_type: str = None) -> List[Dict[str, Any]]:
        """Map multiple submissions efficiently with batching."""
        
        if not submissions:
            return []
        
        # Determine guide type once
        if not guide_type:
            guide_type_result = self.determine_guide_type(guide_content)
            guide_type = guide_type_result.get('type', 'questions')
        
        results = []
        
        # Process submissions in batches for efficiency
        for i in range(0, len(submissions), self.batch_size):
            batch = submissions[i:i + self.batch_size]
            
            if len(batch) == 1:
                # Single submission - use optimized individual mapping
                submission = batch[0]
                result = self.map_submission_to_guide_optimized(
                    guide_content, 
                    submission.get('content', ''), 
                    guide_type
                )
                results.append({
                    'submission_id': submission.get('id'),
                    'mapping_result': result
                })
            else:
                # Multiple submissions - use batch processing
                batch_results = self._process_batch_mapping(guide_content, batch, guide_type)
                results.extend(batch_results)
        
        return results
    
    def _process_batch_mapping(self, guide_content: str, submissions: List[Dict], guide_type: str) -> List[Dict[str, Any]]:
        """Process multiple submissions in a single LLM call."""
        
        if not self.llm_service:
            # Fallback to individual processing
            return [
                {
                    'submission_id': sub.get('id'),
                    'mapping_result': self._fallback_mapping(guide_content, sub.get('content', ''))
                }
                for sub in submissions
            ]
        
        try:
            # Create batch prompt
            system_prompt = self._create_batch_system_prompt(guide_type)
            user_prompt = self._create_batch_user_prompt(guide_content, submissions, guide_type)
            
            # Call LLM
            response = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                # max_tokens=4000,  # Removed token limit
                temperature=0.1
            )
            
            # Parse batch response
            return self._parse_batch_response(response, submissions)
            
        except Exception as e:
            logger.error(f"Batch mapping failed: {e}, falling back to individual processing")
            # Fallback to individual processing
            return [
                {
                    'submission_id': sub.get('id'),
                    'mapping_result': self.map_submission_to_guide_optimized(
                        guide_content, sub.get('content', ''), guide_type
                    )
                }
                for sub in submissions
            ]
    
    def _create_batch_system_prompt(self, guide_type: str) -> str:
        """Create system prompt for batch processing."""
        return f"""You are an expert at mapping student answers to exam {'questions' if guide_type.lower() == 'questions' else 'answer keys'}.

Process multiple submissions efficiently:
1. Map each submission's answers to the marking guide
2. Return structured JSON for all submissions
3. Use clear submission identifiers
4. Only include confident mappings

Be concise and accurate."""
    
    def _create_batch_user_prompt(self, guide_content: str, submissions: List[Dict], guide_type: str) -> str:
        """Create user prompt for batch processing."""
        
        guide_clean = self._clean_and_deduplicate_content(guide_content)
        
        prompt = f"MARKING GUIDE:\n{guide_clean[:1000]}\n\nSUBMISSIONS:\n"
        
        for i, sub in enumerate(submissions):
            content_clean = self._clean_and_deduplicate_content(sub.get('content', ''))
            prompt += f"\nSubmission {sub.get('id', i+1)}:\n{content_clean[:800]}\n"
        
        prompt += "\nReturn JSON format:\n{\n  \"results\": [\n    {\n      \"submission_id\": \"1\",\n      \"mappings\": [...]\n    }\n  ]\n}"
        
        return prompt
    
    def _parse_batch_response(self, response: str, submissions: List[Dict]) -> List[Dict[str, Any]]:
        """Parse batch LLM response."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            result = json.loads(json_match.group())
            
            if 'results' not in result:
                raise ValueError("No results field in response")
            
            parsed_results = []
            for item in result['results']:
                parsed_results.append({
                    'submission_id': item.get('submission_id'),
                    'mapping_result': {'mappings': item.get('mappings', [])}
                })
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"Batch response parsing failed: {e}")
            # Return fallback results
            return [
                {
                    'submission_id': sub.get('id'),
                    'mapping_result': self._fallback_mapping('', sub.get('content', ''))
                }
                for sub in submissions
            ]
    
    def _fallback_mapping(self, guide_content: str, submission_content: str) -> Dict[str, Any]:
        """Fallback mapping using regex when LLM fails."""
        try:
            # Use parent class fallback method if available
            if hasattr(super(), '_fallback_mapping'):
                return super()._fallback_mapping(guide_content, submission_content)
            
            # Simple regex-based fallback
            mappings = []
            
            # Extract question patterns
            question_patterns = re.findall(r'(?:question|q)\s*(\d+)[:.\s]*(.*?)(?=(?:question|q)\s*\d+|$)', 
                                         submission_content, re.IGNORECASE | re.DOTALL)
            
            for i, (q_num, answer) in enumerate(question_patterns[:5]):  # Limit to 5
                if answer.strip():
                    mappings.append({
                        'question_id': f"Q{q_num or i+1}",
                        'question_text': f"Question {q_num or i+1}",
                        'answer_text': answer.strip()[:500],  # Limit length
                        'confidence': 0.5  # Low confidence for fallback
                    })
            
            return {'mappings': mappings}
            
        except Exception as e:
            logger.error(f"Fallback mapping failed: {e}")
            return {'mappings': []}