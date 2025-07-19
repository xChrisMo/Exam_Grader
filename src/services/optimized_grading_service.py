"""Optimized Grading Service with batch processing, deterministic prompts, and enhanced efficiency."""

import json
# Removed regex import - using LLM-based approaches instead
from typing import Dict, List, Optional, Any, Tuple

from src.services.grading_service import GradingService
from utils.logger import logger


class OptimizedGradingService(GradingService):
    """Enhanced grading service with batch processing and optimized prompts."""

    def __init__(self, llm_service=None, mapping_service=None):
        """Initialize optimized grading service."""
        super().__init__(llm_service, mapping_service)
        self.max_batch_size = 8  # Process multiple Q&A pairs at once
        self.chunk_size = 3000  # Max characters per LLM call
        
    def _create_deterministic_grading_prompt(self, qa_pairs: List[Dict], marking_guide: str) -> Tuple[str, str]:
        """Create optimized, deterministic prompt for grading multiple Q&A pairs."""
        
        system_prompt = """You are an expert exam grader. Grade student answers efficiently and consistently.

GRADING RULES:
1. Score each answer 0-100 based on correctness and completeness
2. Provide concise feedback (max 50 words per answer)
3. Be consistent and fair across all answers
4. Focus on key concepts and accuracy
5. Return structured JSON output only

SCORING SCALE:
- 90-100: Excellent, complete, accurate
- 80-89: Good, mostly correct, minor gaps
- 70-79: Satisfactory, some errors or omissions
- 60-69: Below average, significant issues
- 0-59: Poor, major errors or incomplete"""
        
        # Prepare marking guide excerpt
        guide_excerpt = marking_guide[:800] if marking_guide else "No specific marking guide provided."
        
        user_prompt = f"""MARKING GUIDE:
{guide_excerpt}

GRADE THESE ANSWERS:
"""
        
        for i, qa in enumerate(qa_pairs, 1):
            question = qa.get('question_text', qa.get('question', f"Question {i}"))
            answer = qa.get('answer_text', qa.get('student_answer', qa.get('answer', '')))
            expected = qa.get('expected_answer', '')
            
            user_prompt += f"\n{i}. QUESTION: {question[:200]}"
            if expected:
                user_prompt += f"\n   EXPECTED: {expected[:150]}"
            user_prompt += f"\n   STUDENT: {answer}\n"
        
        user_prompt += "\nReturn JSON format:\n{\n  \"grades\": [\n    {\n      \"question_id\": 1,\n      \"score\": 85,\n      \"feedback\": \"Good understanding, minor error in calculation\",\n      \"strengths\": [\"Clear explanation\"],\n      \"weaknesses\": [\"Calculation error\"]\n    }\n  ]\n}"
        
        return system_prompt, user_prompt
    
    def grade_submission_batch(self, mapped_qa_pairs: List[Dict], marking_guide: str = "") -> Dict[str, Any]:
        """Grade multiple Q&A pairs efficiently in batches."""
        
        if not mapped_qa_pairs:
            return {
                'total_score': 0,
                'percentage': 0,
                'letter_grade': 'F',
                'detailed_grades': [],
                'summary': {'total_questions': 0, 'average_score': 0}
            }
        
        all_grades = []
        total_score = 0
        max_possible_score = 0
        
        # Process in batches
        for i in range(0, len(mapped_qa_pairs), self.max_batch_size):
            batch = mapped_qa_pairs[i:i + self.max_batch_size]
            
            try:
                batch_grades = self._grade_batch(batch, marking_guide)
                all_grades.extend(batch_grades)
                
                # Calculate scores
                for grade in batch_grades:
                    score = grade.get('score', 0)
                    total_score += score
                    max_possible_score += 100  # Assuming 100 is max per question
                    
            except Exception as e:
                logger.error(f"Batch grading failed for batch {i//self.max_batch_size + 1}: {e}")
                # Add fallback grades for this batch
                fallback_grades = self._create_fallback_grades(batch)
                all_grades.extend(fallback_grades)
                max_possible_score += len(batch) * 100
        
        # Calculate final metrics
        percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
        letter_grade = self._calculate_letter_grade(percentage)
        
        return {
            'total_score': total_score,
            'max_possible_score': max_possible_score,
            'percentage': round(percentage, 2),
            'letter_grade': letter_grade,
            'detailed_grades': all_grades,
            'summary': {
                'total_questions': len(mapped_qa_pairs),
                'average_score': round(total_score / len(mapped_qa_pairs), 2) if mapped_qa_pairs else 0,
                'graded_successfully': len([g for g in all_grades if g.get('score', 0) > 0])
            }
        }
    
    def _grade_batch(self, qa_pairs: List[Dict], marking_guide: str, recursion_depth: int = 0) -> List[Dict]:
        """Grade a batch of Q&A pairs using LLM."""
        
        if not self.llm_service:
            logger.warning("LLM service not available, using fallback grading")
            return self._create_fallback_grades(qa_pairs)
        
        # Prevent infinite recursion
        if recursion_depth > 3:
            logger.warning(f"Maximum recursion depth reached, using fallback grading for {len(qa_pairs)} pairs")
            return self._create_fallback_grades(qa_pairs)
        
        try:
            # Create optimized prompt
            system_prompt, user_prompt = self._create_deterministic_grading_prompt(qa_pairs, marking_guide)
            
            # Check if prompt is too long and chunk if necessary
            if len(user_prompt) > self.chunk_size:
                return self._grade_chunked_batch(qa_pairs, marking_guide, recursion_depth + 1)
            
            # Call LLM
            response = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                # max_tokens=1500,  # Removed token limit
                temperature=0.1  # Low temperature for consistency
            )
            
            # Parse and validate response
            grades = self._parse_grading_response(response, qa_pairs)
            
            if grades:
                logger.info(f"Successfully graded {len(grades)} answers in batch")
                return grades
            else:
                logger.warning("LLM grading failed, using fallback")
                return self._create_fallback_grades(qa_pairs)
                
        except Exception as e:
            logger.error(f"Batch grading error: {e}")
            return self._create_fallback_grades(qa_pairs)
    
    def _grade_chunked_batch(self, qa_pairs: List[Dict], marking_guide: str, recursion_depth: int = 0) -> List[Dict]:
        """Grade large batches by chunking into smaller pieces."""
        logger.info(f"Chunking {len(qa_pairs)} Q&A pairs for grading (depth: {recursion_depth})")
        
        all_grades = []
        # Increase chunk division based on recursion depth to ensure smaller chunks
        chunk_divisor = 2 + recursion_depth  # Start with 2, increase with depth
        chunk_size = max(1, self.max_batch_size // chunk_divisor)
        
        for i in range(0, len(qa_pairs), chunk_size):
            chunk = qa_pairs[i:i + chunk_size]
            logger.info(f"Grading chunk {i//chunk_size + 1} with {len(chunk)} pairs (depth: {recursion_depth})")
            
            chunk_grades = self._grade_batch(chunk, marking_guide, recursion_depth)
            all_grades.extend(chunk_grades)
        
        return all_grades
    
    def _parse_grading_response(self, response: str, qa_pairs: List[Dict]) -> Optional[List[Dict]]:
        """Parse and validate LLM grading response."""
        
        try:
            # Extract JSON from response using LLM-based approach
            try:
                # First attempt direct JSON parsing
                result = json.loads(response)
            except json.JSONDecodeError:
                # Use LLM to extract and clean JSON
                try:
                    if hasattr(self, 'llm_service') and self.llm_service:
                        json_cleaning_prompt = f"""
                        Extract and clean the JSON from this response. Return only valid JSON:
                        
                        {response}
                        """
                        
                        json_response = self.llm_service.client.chat.completions.create(
                            model=self.llm_service.model,
                            messages=[
                                {"role": "system", "content": "Extract and return only valid JSON from the given text. No explanations."},
                                {"role": "user", "content": json_cleaning_prompt}
                            ],
                            temperature=0.0
                        )
                        
                        cleaned_response = json_response.choices[0].message.content.strip()
                        result = json.loads(cleaned_response)
                    else:
                        return None
                except Exception:
                    return None
            
            if 'grades' not in result or not isinstance(result['grades'], list):
                return None
            
            # Validate and clean grades
            validated_grades = []
            for i, grade in enumerate(result['grades']):
                validated_grade = self._validate_and_clean_grade(grade, qa_pairs[i] if i < len(qa_pairs) else {})
                validated_grades.append(validated_grade)
            
            # Ensure we have grades for all Q&A pairs
            while len(validated_grades) < len(qa_pairs):
                validated_grades.append(self._create_fallback_grade(qa_pairs[len(validated_grades)]))
            
            return validated_grades[:len(qa_pairs)]  # Don't return more than we asked for
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return None
    
    def _validate_and_clean_grade(self, grade: Dict, qa_pair: Dict) -> Dict:
        """Validate and clean individual grade."""
        
        # Ensure required fields
        validated = {
            'question_id': grade.get('question_id', qa_pair.get('question_id', 'Unknown')),
            'score': self._validate_score(grade.get('score', 0)),
            'feedback': self._clean_feedback(grade.get('feedback', 'No feedback provided')),
            'strengths': self._clean_list_field(grade.get('strengths', [])),
            'weaknesses': self._clean_list_field(grade.get('weaknesses', []))
        }
        
        # Add question and answer for reference
        validated['question_text'] = qa_pair.get('question_text', qa_pair.get('question', ''))
        validated['student_answer'] = qa_pair.get('answer_text', qa_pair.get('student_answer', ''))
        
        return validated
    
    def _validate_score(self, score: Any) -> int:
        """Validate and normalize score to 0-100 range."""
        try:
            score = float(score)
            return max(0, min(100, int(round(score))))
        except (ValueError, TypeError):
            return 0
    
    def _clean_feedback(self, feedback: str) -> str:
        """Clean and limit feedback text."""
        if not isinstance(feedback, str):
            return "No feedback provided"
        
        # Remove excessive whitespace and limit length using basic string operations
        feedback = ' '.join(feedback.strip().split())
        return feedback[:200] if len(feedback) > 200 else feedback
    
    def _clean_list_field(self, items: Any) -> List[str]:
        """Clean and validate list fields like strengths/weaknesses."""
        if not isinstance(items, list):
            return []
        
        cleaned = []
        for item in items[:3]:  # Limit to 3 items
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip()[:100])  # Limit length
        
        return cleaned
    
    def _create_fallback_grades(self, qa_pairs: List[Dict]) -> List[Dict]:
        """Create fallback grades when LLM fails."""
        return [self._create_fallback_grade(qa) for qa in qa_pairs]
    
    def _create_fallback_grade(self, qa_pair: Dict) -> Dict:
        """Create a single fallback grade."""
        
        # Simple heuristic scoring based on answer length and content
        answer = qa_pair.get('answer_text', qa_pair.get('student_answer', ''))
        
        if not answer or len(answer.strip()) < 10:
            score = 0
            feedback = "No answer provided or answer too short"
        elif len(answer.strip()) < 50:
            score = 30
            feedback = "Answer provided but lacks detail"
        else:
            score = 60  # Default middle score
            feedback = "Answer provided - manual review recommended"
        
        return {
            'question_id': qa_pair.get('question_id', 'Unknown'),
            'score': score,
            'feedback': feedback,
            'strengths': [],
            'weaknesses': ['Automated grading - manual review needed'],
            'question_text': qa_pair.get('question_text', qa_pair.get('question', '')),
            'student_answer': answer
        }
    
    def _calculate_letter_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage."""
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def grade_submission_optimized(self, submission_content: str, marking_guide: str, mapped_data: Dict = None) -> Dict[str, Any]:
        """Optimized single submission grading with optional pre-mapped data."""
        
        try:
            # Use pre-mapped data if available, otherwise map first
            if mapped_data and 'mappings' in mapped_data:
                qa_pairs = mapped_data['mappings']
            else:
                # Fall back to mapping if not provided
                if self.mapping_service:
                    mapping_result = self.mapping_service.map_submission_to_guide_optimized(
                        marking_guide, submission_content
                    )
                    qa_pairs = mapping_result.get('mappings', [])
                else:
                    logger.warning("No mapping service available and no pre-mapped data")
                    qa_pairs = []
            
            # Grade the mapped Q&A pairs
            return self.grade_submission_batch(qa_pairs, marking_guide)
            
        except Exception as e:
            logger.error(f"Optimized grading failed: {e}")
            return {
                'total_score': 0,
                'percentage': 0,
                'letter_grade': 'F',
                'detailed_grades': [],
                'summary': {'total_questions': 0, 'average_score': 0, 'error': str(e)}
            }
    
    def get_grading_stats(self) -> Dict[str, Any]:
        """Get grading performance statistics."""
        return {
            'max_batch_size': self.max_batch_size,
            'chunk_size': self.chunk_size,
            'llm_available': self.llm_service is not None,
            'mapping_available': self.mapping_service is not None
        }