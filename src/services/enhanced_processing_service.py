"""Enhanced Processing Service for LLM-driven marking guide and submission processing.

This service implements the complete pipeline:
1. Marking Guide Processing - LLM extracts structured questions/answers
2. Submission Processing - OCR + LLM mapping to guide questions
3. Grading Process - LLM grades with max_questions_to_answer logic
"""
from typing import Any, Dict, List, Optional, Tuple

import hashlib
import json
import os
from datetime import datetime


from src.database.models import (
    GradingResult,
    GradingSession,
    Mapping,
    MarkingGuide,
    Submission,
    db,
)
from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService
from utils.logger import logger

# Import LLM service for type hints
try:
    from src.services.consolidated_llm_service import ConsolidatedLLMService as LLMService
except ImportError:
    # Use string type hint if import fails
    LLMService = 'ConsolidatedLLMService'


class EnhancedProcessingService:
    """Enhanced service for complete LLM-driven processing pipeline."""

    def __init__(self, llm_service: Optional[LLMService] = None, ocr_service: Optional[OCRService] = None):
        """Initialize the enhanced processing service.
        
        Args:
            llm_service: Optional LLM service instance
            ocr_service: Optional OCR service instance
        """
        self.llm_service = llm_service or LLMService()
        self.ocr_service = ocr_service or OCRService()
        
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash for content deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def process_marking_guide(self, guide_id: str, file_path: str, raw_content: str) -> Tuple[Dict, Optional[str]]:
        """Process marking guide using LLM to extract structured content.
        
        Args:
            guide_id: Database ID of the marking guide
            file_path: Path to the uploaded file
            raw_content: Raw text content extracted from file
            
        Returns:
            Tuple[Dict, Optional[str]]: (Structured guide data, Error message)
        """
        try:
            logger.info(f"Processing marking guide {guide_id} with LLM extraction")
            
            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(raw_content)
            
            # Check for existing guide with same content
            existing_guide = MarkingGuide.query.filter_by(content_hash=content_hash).first()
            if existing_guide and existing_guide.id != guide_id:
                logger.warning(f"Duplicate content detected for guide {guide_id}")
                return {}, f"Duplicate content detected. Similar guide exists: {existing_guide.title}"
            
            # Use LLM to extract structured content
            structured_data = self._extract_guide_structure(raw_content)
            
            # Update database with structured content
            guide = MarkingGuide.query.get(guide_id)
            if guide:
                guide.content_text = raw_content
                guide.content_hash = content_hash
                guide.questions = structured_data
                guide.total_marks = self._calculate_total_marks(structured_data)
                guide.updated_at = datetime.utcnow()
                
                db.session.commit()
                logger.info(f"Successfully processed marking guide {guide_id}")
                
                return structured_data, None
            else:
                return {}, f"Guide {guide_id} not found in database"
                
        except Exception as e:
            logger.error(f"Error processing marking guide {guide_id}: {str(e)}")
            db.session.rollback()
            return {}, f"Failed to process marking guide: {str(e)}"
    
    def _extract_guide_structure(self, raw_content: str) -> Dict:
        """Use LLM to extract structured questions and answers from guide."""
        try:
            system_prompt = """You are an expert at analyzing academic marking guides. There are THREE types of marking guides:

1. QUESTIONS ONLY - Contains only questions without model answers
2. ANSWERS ONLY - Contains only model answers/solutions without questions  
3. MIXED - Contains both questions and their corresponding model answers

Your task is to:
1. Identify which type of guide this is
2. Extract the appropriate content based on the type
3. Structure the data consistently regardless of type

Return a JSON object with this EXACT structure:
{
    "type": "questions_only" | "answers_only" | "mixed",
    "questions": [
        {
            "id": 1,
            "question": "Question text (or 'Question N' if answers_only)",
            "answer": "Model answer (or empty string if questions_only)",
            "marks": 10,
            "section": "Optional section name"
        }
    ],
    "total_marks": 100,
    "instructions": "Any general grading instructions",
    "guide_analysis": {
        "has_questions": true/false,
        "has_answers": true/false,
        "question_count": number,
        "answer_count": number
    }
}

IMPORTANT GUIDELINES:
- For QUESTIONS ONLY: Extract questions, set answer to empty string
- For ANSWERS ONLY: Create generic question labels, extract the answers
- For MIXED: Extract both questions and their corresponding answers
- Always assign reasonable marks (typically 5-20 per question)
- Number questions sequentially starting from 1"""
            
            user_prompt = f"""Please analyze this marking guide and extract structured content:

{raw_content}

Extract all questions, answers, and marking criteria in the specified JSON format."""
            
            # Make LLM call
            response = self.llm_service._make_api_call_with_retry({
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            })
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                structured_data = json.loads(result_text)
                logger.info(f"Successfully extracted {len(structured_data.get('questions', []))} questions from guide")
                return structured_data
            except json.JSONDecodeError:
                # Fallback: use LLM to fix JSON
                fixed_json = self.llm_service._get_structured_response(result_text)
                return json.loads(fixed_json)
                
        except Exception as e:
            logger.error(f"Error extracting guide structure: {str(e)}")
            # Return basic structure as fallback
            return {
                "type": "unknown",
                "questions": [],
                "total_marks": 0,
                "instructions": "Failed to extract structured content"
            }
    
    def _calculate_total_marks(self, structured_data: Dict) -> float:
        """Calculate total marks from structured guide data."""
        try:
            if 'questions' in structured_data:
                return sum(q.get('marks', 0) for q in structured_data['questions'])
            return structured_data.get('total_marks', 0)
        except Exception:
            return 0.0
    
    def process_submission(self, submission_id: str, file_path: str, marking_guide_id: str) -> Tuple[Dict, Optional[str]]:
        """Process student submission using OCR and LLM mapping.
        
        Args:
            submission_id: Database ID of the submission
            file_path: Path to the uploaded submission file
            marking_guide_id: ID of the associated marking guide
            
        Returns:
            Tuple[Dict, Optional[str]]: (Processing result, Error message)
        """
        try:
            logger.info(f"Processing submission {submission_id} with OCR and LLM mapping")
            
            # Extract text using OCR
            submission_text = self.ocr_service.extract_text_from_image(file_path)
            if not submission_text:
                return {}, "Failed to extract text from submission file"
            
            ocr_confidence = 0.8  # Default confidence for successful extraction
            
            # Generate content hash
            content_hash = self._generate_content_hash(submission_text)
            
            # Check for duplicate submissions
            existing_submission = Submission.query.filter_by(
                content_hash=content_hash,
                marking_guide_id=marking_guide_id
            ).first()
            
            if existing_submission and existing_submission.id != submission_id:
                logger.warning(f"Duplicate submission detected for {submission_id}")
                return {}, f"Duplicate submission detected. Similar submission exists: {existing_submission.filename}"
            
            # Get marking guide data
            guide = MarkingGuide.query.get(marking_guide_id)
            if not guide or not guide.questions:
                return {}, "Marking guide not found or not processed"
            
            # Use LLM to map submission to guide questions
            mapping_result = self._map_submission_to_guide(submission_text, guide.questions)
            
            # Update submission in database
            submission = Submission.query.get(submission_id)
            if submission:
                submission.content_text = submission_text
                submission.content_hash = content_hash
                submission.ocr_confidence = ocr_confidence
                submission.answers = mapping_result
                submission.processing_status = "completed"
                submission.processed = True
                submission.updated_at = datetime.utcnow()
                
                # Save mappings to database
                self._save_mappings(submission_id, mapping_result)
                
                db.session.commit()
                logger.info(f"Successfully processed submission {submission_id}")
                
                return mapping_result, None
            else:
                return {}, f"Submission {submission_id} not found in database"
                
        except Exception as e:
            logger.error(f"Error processing submission {submission_id}: {str(e)}")
            db.session.rollback()
            return {}, f"Failed to process submission: {str(e)}"
    
    def _map_submission_to_guide(self, submission_text: str, guide_questions: Dict) -> Dict:
        """Use LLM to intelligently map submission answers to guide questions."""
        try:
            # Determine guide type from the structured data
            guide_type = guide_questions.get('type', 'mixed')
            
            system_prompt = f"""You are an expert at analyzing student submissions and mapping answers to marking guide content.

IMPORTANT: The marking guide is of type "{guide_type}":

1. QUESTIONS_ONLY - Guide contains only questions, no model answers
   - Map student answers to the corresponding questions
   - Student must provide the answers to match the questions

2. ANSWERS_ONLY - Guide contains only model answers/solutions, no questions
   - Map student answers to the corresponding model answers
   - Compare student responses against the provided solutions

3. MIXED - Guide contains both questions and their model answers
   - Map student answers to questions AND compare against model answers
   - Use both question context and model answer for evaluation

Your task based on guide type "{guide_type}":
- Extract student responses from the submission
- Map each response to the appropriate guide item
- Provide confidence scores for each mapping
- Include the guide answer when available for comparison

Return a JSON object with this structure:
{{
    "guide_type": "{guide_type}",
    "mappings": [
        {{
            "question_id": 1,
            "question_text": "Question from guide (or generated if answers_only)",
            "guide_answer": "Model answer from guide (empty if questions_only)",
            "student_answer": "Student's response",
            "max_score": 10,
            "confidence": 0.95,
            "match_reason": "Why this mapping was chosen"
        }}
    ],
    "unmapped_content": "Any content that couldn't be mapped"
}}"""
            
            user_prompt = f"""Marking Guide Questions:
{json.dumps(guide_questions, indent=2)}

Student Submission:
{submission_text}

Please map the student's answers to the appropriate questions from the marking guide."""
            
            # Make LLM call
            response = self.llm_service._make_api_call_with_retry({
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            })
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                mapping_result = json.loads(result_text)
                logger.info(f"Successfully mapped {len(mapping_result.get('mappings', []))} answers")
                return mapping_result
            except json.JSONDecodeError:
                # Fallback: use LLM to fix JSON
                fixed_json = self.llm_service._get_structured_response(result_text)
                return json.loads(fixed_json)
                
        except Exception as e:
            logger.error(f"Error mapping submission to guide: {str(e)}")
            return {"mappings": [], "unmapped_content": submission_text}
    
    def _save_mappings(self, submission_id: str, mapping_result: Dict):
        """Save mapping results to database with retry logic."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Clear existing mappings
                Mapping.query.filter_by(submission_id=submission_id).delete()
                
                # Save new mappings
                for mapping in mapping_result.get('mappings', []):
                    db_mapping = Mapping(
                        submission_id=submission_id,
                        guide_question_id=str(mapping.get('question_id', '')),
                        guide_question_text=mapping.get('question_text', ''),
                        guide_answer=mapping.get('guide_answer', ''),
                        max_score=mapping.get('max_score', 0),
                        submission_answer=mapping.get('student_answer', ''),
                        match_score=mapping.get('confidence', 0.0),
                        match_reason=mapping.get('match_reason', ''),
                        mapping_method='llm'
                    )
                    db.session.add(db_mapping)
                
                # Commit with retry
                self._commit_with_retry("mapping save")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock saving mappings on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to save mappings after {max_retries} attempts: {str(e)}")
                    raise
    
    def _create_mappings_from_answers(self, submission: Submission, guide: MarkingGuide) -> List[Mapping]:
        """Create mappings from existing submission answers data."""
        try:
            mappings = []
            
            if not submission.answers or not isinstance(submission.answers, dict):
                return mappings
            
            # Get guide questions with robust type checking
            guide_questions = []
            if guide.questions:
                logger.debug(f"Guide questions type: {type(guide.questions)}, content: {guide.questions}")
                if isinstance(guide.questions, dict):
                    guide_questions = guide.questions.get('questions', [])
                    logger.debug(f"Extracted {len(guide_questions)} questions from dict")
                elif isinstance(guide.questions, list):
                    guide_questions = guide.questions
                    logger.debug(f"Using {len(guide_questions)} questions from list")
                else:
                    logger.warning(f"Unexpected guide.questions type: {type(guide.questions)}")
                    guide_questions = []
            else:
                logger.debug("No guide.questions found")
            
            # Create mappings from submission answers and guide questions
            # If we have guide questions, create mappings for each question
            # If we have submission answers, use those, otherwise use content_text
            
            max_mappings = max(len(guide_questions), len(submission.answers.items()) if submission.answers else 1)
            
            # If we have guide questions, use them to determine how many mappings to create
            if guide_questions:
                max_mappings = len(guide_questions)
                logger.debug(f"Creating {max_mappings} mappings based on guide questions")
            
            # Create mappings for each question/answer pair
            submission_answers_list = list(submission.answers.items()) if submission.answers else [('content', submission.content_text or '')]
            
            for i in range(max_mappings):
                # Get the answer for this question (cycle through available answers if needed)
                if submission_answers_list:
                    answer_index = i % len(submission_answers_list)
                    key, answer = submission_answers_list[answer_index]
                else:
                    key, answer = 'content', submission.content_text or ''
                # Try to match with guide questions
                guide_question = None
                if i < len(guide_questions):
                    potential_question = guide_questions[i]
                    # Check if it's a dictionary or list
                    if isinstance(potential_question, dict):
                        guide_question = potential_question
                    elif isinstance(potential_question, list) and len(potential_question) > 0:
                        # If it's a list, take the first element if it's a dict
                        if isinstance(potential_question[0], dict):
                            guide_question = potential_question[0]
                        else:
                            guide_question = None
                    else:
                        guide_question = None
                
                # If we don't have a valid guide question, create a generic one
                if not guide_question or not isinstance(guide_question, dict):
                    guide_question = {
                        'id': i + 1,
                        'question': f"Question {i + 1}",
                        'answer': '',
                        'marks': 10
                    }
                
                # Create mapping object with safe access to dictionary keys
                mapping = Mapping(
                    submission_id=submission.id,
                    guide_question_id=str(guide_question.get('id', i + 1)),
                    guide_question_text=guide_question.get('question', guide_question.get('text', f"Question {i + 1}")),
                    guide_answer=guide_question.get('answer', guide_question.get('model_answer', '')),
                    max_score=guide_question.get('marks', guide_question.get('max_marks', guide_question.get('points', 10))),
                    submission_answer=str(answer),
                    match_score=0.8,  # Default confidence
                    match_reason='Created from existing submission answers',
                    mapping_method='existing_data'
                )
                
                db.session.add(mapping)
                mappings.append(mapping)
            
            # Commit the mappings with retry logic
            self._commit_with_retry("mappings creation")
            logger.info(f"Created {len(mappings)} mappings from existing submission answers")
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error creating mappings from answers: {str(e)}")
            return []
    
    def process_grading(self, submission_id: str, marking_guide_id: str, max_questions_to_answer: Optional[int] = None) -> Tuple[Dict, Optional[str]]:
        """Process grading with max_questions_to_answer logic.
        
        Args:
            submission_id: ID of the submission to grade
            marking_guide_id: ID of the marking guide
            max_questions_to_answer: Maximum number of questions to grade (from form)
            
        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message)
        """
        try:
            logger.info(f"Processing grading for submission {submission_id} with max_questions: {max_questions_to_answer}")
            
            # Get submission and marking guide
            submission = Submission.query.get(submission_id)
            guide = MarkingGuide.query.get(marking_guide_id)
            
            if not submission:
                return {}, f"Submission {submission_id} not found"
            
            if not guide:
                return {}, f"Marking guide {marking_guide_id} not found"
            
            # Create or update grading session
            grading_session = self._create_grading_session(submission_id, marking_guide_id, max_questions_to_answer)
            
            # Check if we have existing mappings
            mappings = Mapping.query.filter_by(submission_id=submission_id).all()
            
            if not mappings:
                # If no mappings exist, try to create them from submission data
                logger.info(f"No existing mappings found for submission {submission_id}, creating from submission data")
                
                if not submission.content_text:
                    return {}, "No content available for grading - submission needs to be processed first"
                
                # Create mappings from submission answers if available
                if submission.answers and isinstance(submission.answers, dict):
                    mappings = self._create_mappings_from_answers(submission, guide)
                else:
                    # Use LLM to create mappings from content_text
                    mapping_result = self._map_submission_to_guide(submission.content_text, guide.questions or {})
                    self._save_mappings(submission_id, mapping_result)
                    mappings = Mapping.query.filter_by(submission_id=submission_id).all()
            
            if not mappings:
                return {}, "Unable to create mappings for grading"
            
            # Grade each mapping
            grading_results = []
            for mapping in mappings:
                grade_result = self._grade_single_mapping(mapping, guide)
                if grade_result:
                    grading_results.append(grade_result)
            
            if not grading_results:
                return {}, "No answers could be graded"
            
            # Sort by score and select top N
            grading_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            if max_questions_to_answer and max_questions_to_answer > 0:
                selected_results = grading_results[:max_questions_to_answer]
                logger.info(f"Selected top {len(selected_results)} answers out of {len(grading_results)}")
            else:
                selected_results = grading_results
            
            # Calculate final score
            final_result = self._calculate_final_score(selected_results, guide)
            
            # Save results to database with retry logic
            self._save_grading_results_with_retry(submission_id, marking_guide_id, selected_results, grading_session.id)
            
            # Update grading session with retry logic
            self._update_grading_session_with_retry(grading_session, len(selected_results))
            
            logger.info(f"Successfully completed grading for submission {submission_id}")
            return final_result, None
            
        except Exception as e:
            logger.error(f"Error processing grading: {str(e)}")
            db.session.rollback()
            return {}, f"Failed to process grading: {str(e)}"
    
    def _create_grading_session(self, submission_id: str, marking_guide_id: str, max_questions: Optional[int]) -> GradingSession:
        """Create or update grading session with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Check for existing session
                session = GradingSession.query.filter_by(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id
                ).first()
                
                if session:
                    session.status = "in_progress"
                    session.max_questions_limit = max_questions
                    session.processing_start_time = datetime.utcnow()
                    session.updated_at = datetime.utcnow()
                else:
                    # Get user_id from submission
                    submission = Submission.query.get(submission_id)
                    user_id = submission.user_id if submission else None
                    
                    session = GradingSession(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        user_id=user_id,
                        status="in_progress",
                        max_questions_limit=max_questions,
                        processing_start_time=datetime.utcnow()
                    )
                    db.session.add(session)
                
                # Commit immediately to avoid holding locks
                db.session.commit()
                return session
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to create grading session after {max_retries} attempts: {str(e)}")
                    raise
    
    def _grade_single_mapping(self, mapping: Mapping, guide: MarkingGuide) -> Optional[Dict]:
        """Grade a single question-answer mapping using LLM with full context awareness."""
        try:
            logger.info(f"Grading mapping {mapping.id} using LLM with full context")
            
            # Let LLM handle everything - guide type detection, scoring, and feedback
            # Pass all available context to LLM for intelligent processing
            
            system_prompt = """You are an expert educational grader with full context awareness. 

Your task is to:
1. Analyze the marking guide content to determine its type (questions_only, answers_only, or mixed)
2. Grade the student's response appropriately based on the guide type
3. Provide fair, encouraging feedback with partial credit

GUIDE TYPES:
- QUESTIONS_ONLY: Only questions provided, no model answers
- ANSWERS_ONLY: Only model answers provided, no questions  
- MIXED: Both questions and model answers provided

GRADING PHILOSOPHY:
- Be fair and encouraging
- Give credit for effort and understanding
- Look for relevant content even if not perfectly expressed
- Award partial credit generously
- Focus on what the student got right

SCORING SCALE:
- 90-100%: Excellent understanding and complete answer
- 70-89%: Good understanding with most key points
- 50-69%: Adequate understanding with basic points
- 30-49%: Some understanding with partial content
- 10-29%: Minimal understanding but shows effort
- 0-9%: No relevant content or understanding

Return JSON format (ensure all numbers are properly formatted):
{
    "score": 8.5,
    "max_score": 10.0,
    "percentage": 85.0,
    "feedback": "Encouraging and constructive feedback",
    "guide_type_detected": "mixed",
    "confidence": 0.9
}"""
            
            # Prepare all available context for the LLM
            guide_content = ""
            if guide.content_text:
                guide_content = guide.content_text[:2000]  # Limit to avoid token limits
            
            guide_questions_str = ""
            if guide.questions:
                try:
                    if isinstance(guide.questions, dict):
                        guide_questions_str = json.dumps(guide.questions, indent=2)[:1000]
                    else:
                        guide_questions_str = str(guide.questions)[:1000]
                except:
                    guide_questions_str = "Unable to parse guide questions"
            
            user_prompt = f"""GRADING CONTEXT:
Marking Guide Title: {guide.title}
Guide Content: {guide_content}
Structured Guide Data: {guide_questions_str}

SPECIFIC QUESTION/ANSWER:
Question Text: {mapping.guide_question_text or 'Not specified'}
Model Answer: {mapping.guide_answer or 'Not provided'}
Maximum Score: {mapping.max_score or 10}

STUDENT RESPONSE:
{mapping.submission_answer or 'No response provided'}

Please analyze the guide type, grade the student's response fairly, and provide constructive feedback."""
            
            # Make LLM call with error handling
            try:
                response = self.llm_service._make_api_call_with_retry({
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                })
                
                result_text = response.choices[0].message.content.strip()
                
                # Parse JSON response with error handling
                try:
                    grade_result = json.loads(result_text)
                    
                    # Ensure all required fields are present and properly formatted
                    score = float(grade_result.get('score', 0))
                    max_score = float(grade_result.get('max_score', mapping.max_score or 10))
                    
                    # Ensure score doesn't exceed max_score
                    score = min(score, max_score)
                    
                    # Calculate percentage
                    percentage = (score / max_score * 100) if max_score > 0 else 0
                    
                    # Return properly formatted result
                    return {
                        'mapping_id': mapping.id,
                        'question_id': mapping.guide_question_id,
                        'score': round(score, 2),
                        'max_score': round(max_score, 2),
                        'percentage': round(percentage, 1),
                        'feedback': grade_result.get('feedback', 'No feedback provided'),
                        'guide_type_detected': grade_result.get('guide_type_detected', 'unknown'),
                        'confidence': float(grade_result.get('confidence', 0.8))
                    }
                    
                except json.JSONDecodeError as json_error:
                    logger.warning(f"JSON parsing failed for mapping {mapping.id}: {json_error}")
                    return self._create_fallback_result(mapping)
                    
            except Exception as llm_error:
                logger.error(f"LLM call failed for mapping {mapping.id}: {llm_error}")
                return self._create_fallback_result(mapping)
                
        except Exception as e:
            logger.error(f"Error grading mapping {mapping.id}: {str(e)}")
            return None
    
    def _create_fallback_result(self, mapping: Mapping) -> Dict:
        """Create a fallback result when LLM processing fails."""
        try:
            student_answer = mapping.submission_answer or ""
            max_score = mapping.max_score or 10
            
            # Basic content analysis for fallback scoring
            if len(student_answer.strip()) == 0:
                score = 0
                feedback = "No response provided"
            elif len(student_answer.strip()) < 20:
                score = max_score * 0.3  # 30% for minimal effort
                feedback = "Brief response, shows some effort"
            elif len(student_answer.strip()) < 100:
                score = max_score * 0.6  # 60% for moderate effort
                feedback = "Moderate response, shows good effort"
            else:
                score = max_score * 0.8  # 80% for substantial effort
                feedback = "Substantial response, shows strong effort"
            
            return {
                'mapping_id': mapping.id,
                'question_id': mapping.guide_question_id,
                'score': round(score, 2),
                'max_score': round(max_score, 2),
                'percentage': round((score / max_score * 100), 1),
                'feedback': f"{feedback} (Fallback scoring applied)",
                'guide_type_detected': 'unknown',
                'confidence': 0.5
            }
        except Exception as e:
            logger.error(f"Even fallback failed for mapping {mapping.id}: {e}")
            return {
                'mapping_id': mapping.id,
                'question_id': mapping.guide_question_id,
                'score': 5.0,
                'max_score': 10.0,
                'percentage': 50.0,
                'feedback': 'Emergency fallback scoring applied',
                'guide_type_detected': 'unknown',
                'confidence': 0.3
            }
            
            # Prepare all available context for the LLM
            guide_content = ""
            if guide.content_text:
                guide_content = guide.content_text[:2000]  # Limit to avoid token limits
            
            guide_questions_str = ""
            if guide.questions:
                try:
                    if isinstance(guide.questions, dict):
                        guide_questions_str = json.dumps(guide.questions, indent=2)[:1000]
                    else:
                        guide_questions_str = str(guide.questions)[:1000]
                except:
                    guide_questions_str = "Unable to parse guide questions"
            
            user_prompt = f"""GRADING CONTEXT:
Marking Guide Title: {guide.title}
Guide Content: {guide_content}
Structured Guide Data: {guide_questions_str}

SPECIFIC QUESTION/ANSWER:
Question Text: {mapping.guide_question_text or 'Not specified'}
Model Answer: {mapping.guide_answer or 'Not provided'}
Maximum Score: {mapping.max_score or 10}

STUDENT RESPONSE:
{mapping.submission_answer or 'No response provided'}

Please analyze the guide type, grade the student's response fairly, and provide constructive feedback."""
            
            # Make LLM call with error handling
            try:
                response = self.llm_service._make_api_call_with_retry({
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                })
                
                result_text = response.choices[0].message.content.strip()
                
                # Parse JSON response with error handling
                try:
                    grade_result = json.loads(result_text)
                    
                    # Ensure all required fields are present and properly formatted
                    score = float(grade_result.get('score', 0))
                    max_score = float(grade_result.get('max_score', mapping.max_score or 10))
                    
                    # Ensure score doesn't exceed max_score
                    score = min(score, max_score)
                    
                    # Calculate percentage
                    percentage = (score / max_score * 100) if max_score > 0 else 0
                    
                    # Return properly formatted result
                    return {
                        'mapping_id': mapping.id,
                        'question_id': mapping.guide_question_id,
                        'score': round(score, 2),
                        'max_score': round(max_score, 2),
                        'percentage': round(percentage, 1),
                        'feedback': grade_result.get('feedback', 'No feedback provided'),
                        'guide_type_detected': grade_result.get('guide_type_detected', 'unknown'),
                        'confidence': float(grade_result.get('confidence', 0.8))
                    }
                    
                except json.JSONDecodeError as json_error:
                    logger.warning(f"JSON parsing failed for mapping {mapping.id}: {json_error}")
                    
                    # Fallback scoring based on content length and basic analysis
                    student_answer = mapping.submission_answer or ""
                    max_score = mapping.max_score or 10
                    
                    if len(student_answer.strip()) == 0:
                        score = 0
                    elif len(student_answer.strip()) < 20:
                        score = max_score * 0.3  # 30% for minimal effort
                    elif len(student_answer.strip()) < 100:
                        score = max_score * 0.6  # 60% for moderate effort
                    else:
                        score = max_score * 0.8  # 80% for substantial effort
                    
                    return {
                        'mapping_id': mapping.id,
                        'question_id': mapping.guide_question_id,
                        'score': round(score, 2),
                        'max_score': round(max_score, 2),
                        'percentage': round((score / max_score * 100), 1),
                        'feedback': f"Fallback scoring based on response length. Original LLM response parsing failed.",
                        'guide_type_detected': 'unknown',
                        'confidence': 0.5
                    }
                    
            except Exception as llm_error:
                logger.error(f"LLM call failed for mapping {mapping.id}: {llm_error}")
                
                # Fallback scoring
                max_score = mapping.max_score or 10
                score = max_score * 0.5  # Give 50% as fallback
                
                return {
                    'mapping_id': mapping.id,
                    'question_id': mapping.guide_question_id,
                    'score': round(score, 2),
                    'max_score': round(max_score, 2),
                    'percentage': 50.0,
                    'feedback': f"Fallback scoring due to LLM error: {str(llm_error)}",
                    'guide_type_detected': 'unknown',
                    'confidence': 0.3
                }
                
        except Exception as e:
            logger.error(f"Error grading mapping {mapping.id}: {str(e)}")
            return None
            
            # Determine guide type for context-aware grading
            guide_type = "mixed"  # Default
            if guide.questions and isinstance(guide.questions, dict):
                guide_type = guide.questions.get('type', 'mixed')
            
            # Use LLM to grade the answer with guide type awareness
            system_prompt = f"""You are a fair and encouraging educational grader. You understand there are THREE types of marking guides:

1. QUESTIONS_ONLY - Only questions provided, no model answers
2. ANSWERS_ONLY - Only model answers provided, no questions  
3. MIXED - Both questions and model answers provided

CURRENT GUIDE TYPE: {guide_type}

GRADING APPROACH based on guide type:

For QUESTIONS_ONLY:
- Focus on whether student answered the question appropriately
- Look for relevant content, understanding, and effort
- Be generous since no model answer is provided for comparison
- Award points for logical reasoning and topic knowledge

For ANSWERS_ONLY:
- Compare student response against the provided model answer
- Look for key concepts, facts, and approaches from the model
- Give partial credit for partially correct elements
- Consider alternative valid approaches

For MIXED:
- Use both question context AND model answer for evaluation
- Check if student addressed the question AND compare against model answer
- Most comprehensive grading possible

SCORING PHILOSOPHY:
- Be encouraging and fair
- Give credit for effort and partial understanding
- Look for any relevant content, even if not perfectly expressed
- Award partial credit generously for attempts showing understanding

Return JSON format:
{
    "score": 8.5,
    "max_score": 10,
    "percentage": 85.0,
    "feedback": "Encouraging and constructive feedback",
    "guide_type_used": "{guide_type}",
    "confidence": 0.9
}"""
            
            user_prompt = f"""GRADING CONTEXT:
Guide Type: {guide_type}
Question: {mapping.guide_question_text}
Model Answer: {guide_question.get('answer', 'No model answer provided')}
Student Answer: {mapping.submission_answer}
Maximum Score: {guide_question.get('marks', mapping.max_score)}

GRADING INSTRUCTIONS based on guide type "{guide_type}":

If QUESTIONS_ONLY:
- Focus on whether the student answered the question appropriately
- Look for understanding, effort, and relevant content
- Be generous since no model answer is available for direct comparison
- Award points for logical reasoning and topic knowledge

If ANSWERS_ONLY:
- Compare student response directly against the model answer
- Look for key concepts, facts, and approaches from the model
- Give partial credit for partially correct elements

If MIXED:
- Use both the question context AND model answer for comprehensive evaluation
- Check if student addressed the question AND compare against model answer

Please grade this answer fairly and encouragingly."""
            
            # Make LLM call
            response = self.llm_service._make_api_call_with_retry({
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            })
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                grade_result = json.loads(result_text)
                grade_result['mapping_id'] = mapping.id
                grade_result['question_id'] = mapping.guide_question_id
                return grade_result
            except json.JSONDecodeError:
                # Fallback: use LLM to fix JSON
                fixed_json = self.llm_service._get_structured_response(result_text)
                grade_result = json.loads(fixed_json)
                grade_result['mapping_id'] = mapping.id
                grade_result['question_id'] = mapping.guide_question_id
                return grade_result
                
        except Exception as e:
            logger.error(f"Error grading mapping {mapping.id}: {str(e)}")
            return None
    
    def _calculate_final_score(self, grading_results: List[Dict], guide: MarkingGuide) -> Dict:
        """Calculate final score from selected grading results with improved logic."""
        if not grading_results:
            return {
                "total_score": 0,
                "max_possible_score": guide.total_marks or 100,
                "percentage": 0,
                "grade_level": "F",
                "selected_questions": 0,
                "detailed_results": []
            }
        
        # Calculate scores with validation
        total_score = 0
        max_possible = 0
        
        for result in grading_results:
            score = float(result.get('score', 0))
            max_score = float(result.get('max_score', 10))  # Default to 10 if not specified
            
            # Ensure score doesn't exceed max_score
            score = min(score, max_score)
            
            total_score += score
            max_possible += max_score
            
            logger.debug(f"Question score: {score}/{max_score}")
        
        # Calculate percentage with fallback
        if max_possible > 0:
            percentage = (total_score / max_possible) * 100
        else:
            # Fallback: assume each question is worth equal points out of 100
            num_questions = len(grading_results)
            if num_questions > 0:
                avg_score_per_question = total_score / num_questions
                # Assume each question is worth 100/num_questions points
                percentage = (avg_score_per_question / 10) * 100  # Assuming 10 is typical max per question
            else:
                percentage = 0
        
        # Ensure percentage is within bounds
        percentage = max(0, min(100, percentage))
        
        # Determine grade level
        if percentage >= 90:
            grade_level = "A+"
        elif percentage >= 85:
            grade_level = "A"
        elif percentage >= 80:
            grade_level = "A-"
        elif percentage >= 75:
            grade_level = "B+"
        elif percentage >= 70:
            grade_level = "B"
        elif percentage >= 65:
            grade_level = "B-"
        elif percentage >= 60:
            grade_level = "C+"
        elif percentage >= 55:
            grade_level = "C"
        elif percentage >= 50:
            grade_level = "C-"
        else:
            grade_level = "F"
        
        logger.info(f"Final score calculation: {total_score}/{max_possible} = {percentage:.1f}% ({grade_level})")
        
        return {
            "total_score": round(total_score, 2),
            "max_possible_score": round(max_possible, 2),
            "percentage": round(percentage, 1),
            "grade_level": grade_level,
            "selected_questions": len(grading_results),
            "detailed_results": grading_results
        }
    
    def _save_grading_results(self, submission_id: str, marking_guide_id: str, results: List[Dict], session_id: str):
        """Save grading results to database with improved scoring logic."""
        try:
            # Clear existing results for this session
            GradingResult.query.filter_by(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id
            ).delete()
            
            # Calculate overall scores
            total_score = sum(result.get('score', 0) for result in results)
            total_max_score = sum(result.get('max_score', 10) for result in results)
            overall_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            
            # Save individual question results
            for result in results:
                question_score = float(result.get('score', 0))
                question_max_score = float(result.get('max_score', 10))
                question_percentage = (question_score / question_max_score * 100) if question_max_score > 0 else 0
                
                db_result = GradingResult(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id,
                    mapping_id=result.get('mapping_id'),
                    score=question_score,
                    max_score=question_max_score,
                    percentage=round(question_percentage, 1),
                    feedback=result.get('feedback', ''),
                    detailed_feedback=result,
                    grading_method='llm',
                    confidence=result.get('confidence', 0.0),
                    grading_session_id=session_id
                )
                db.session.add(db_result)
            
            # Save a summary result for the overall submission
            summary_feedback = {
                'total_questions_graded': len(results),
                'individual_scores': [
                    {
                        'question_id': r.get('question_id'),
                        'score': r.get('score'),
                        'max_score': r.get('max_score'),
                        'percentage': (r.get('score', 0) / r.get('max_score', 1) * 100) if r.get('max_score', 0) > 0 else 0
                    } for r in results
                ],
                'grading_summary': f"Graded {len(results)} questions. Total score: {total_score:.1f}/{total_max_score:.1f} ({overall_percentage:.1f}%)"
            }
            
            # Create overall summary result
            summary_result = GradingResult(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id,
                mapping_id=None,  # This is a summary, not tied to a specific mapping
                score=round(total_score, 2),
                max_score=round(total_max_score, 2),
                percentage=round(overall_percentage, 1),
                feedback=f"Overall submission score: {total_score:.1f}/{total_max_score:.1f} ({overall_percentage:.1f}%)",
                detailed_feedback=summary_feedback,
                grading_method='llm_summary',
                confidence=sum(r.get('confidence', 0) for r in results) / len(results) if results else 0.0,
                grading_session_id=session_id
            )
            db.session.add(summary_result)
            
            logger.info(f"Saved {len(results)} individual results + 1 summary result for submission {submission_id}")
                
        except Exception as e:
            logger.error(f"Error saving grading results: {str(e)}")
            raise
    
    def process_submission_mapping(self, submission_id: str, marking_guide_id: str) -> Dict:
        """Process submission mapping specifically (wrapper for process_submission).
        
        Args:
            submission_id: Database ID of the submission
            marking_guide_id: ID of the associated marking guide
            
        Returns:
            Dict: Processing result with success status and mapping data
        """
        try:
            # Get submission from database
            submission = Submission.query.get(submission_id)
            if not submission:
                return {
                    'success': False,
                    'error': f'Submission {submission_id} not found'
                }
            
            # Check if submission has a file path
            if not submission.file_path or not os.path.exists(submission.file_path):
                return {
                    'success': False,
                    'error': 'Submission file not found or path invalid'
                }
            
            # Process the submission (which includes mapping)
            mapping_result, error = self.process_submission(
                submission_id=submission_id,
                file_path=submission.file_path,
                marking_guide_id=marking_guide_id
            )
            
            if error:
                return {
                    'success': False,
                    'error': error
                }
            
            return {
                'success': True,
                'mapping_data': mapping_result,
                'message': 'Mapping completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error in process_submission_mapping: {str(e)}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}'
            }
    
    def get_processing_status(self, submission_id: str, marking_guide_id: str) -> Dict:
        """Get current processing status for a submission."""
        try:
            submission = Submission.query.get(submission_id)
            session = GradingSession.query.filter_by(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id
            ).first()
            
            if not submission:
                return {"status": "not_found", "message": "Submission not found"}
            
            status_info = {
                "submission_status": submission.processing_status,
                "submission_processed": submission.processed,
                "grading_session_status": session.status if session else "not_started",
                "current_step": session.current_step if session else None,
                "questions_mapped": session.total_questions_mapped if session else 0,
                "questions_graded": session.total_questions_graded if session else 0,
                "max_questions_limit": session.max_questions_limit if session else None
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _extract_text_from_file(self, file_path: str) -> Tuple[str, float]:
        """Extract text from file using OCR service."""
        try:
            logger.info("Starting OCR text extraction...")
            
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")
            
            # Use OCR service to extract text
            extracted_text = self.ocr_service.extract_text_from_image(file_path)
            
            if not extracted_text or not extracted_text.strip():
                raise Exception("No text could be extracted from the file")
            
            # Default confidence for successful extraction
            confidence = 0.8
            
            logger.info(f"OCR completed successfully. Extracted {len(extracted_text)} characters.")
            return extracted_text, confidence
            
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {str(e)}")
            raise
    
    def _grade_single_answer(self, question: str, model_answer: str, student_answer: str, max_score: float) -> Dict:
        """Grade a single answer using LLM."""
        try:
            system_prompt = """You are an expert grader. Grade the student's answer against the model answer.
            
Provide a score, feedback, and detailed analysis.

Return JSON format:
{
    "score": 8.5,
    "max_score": 10,
    "percentage": 85.0,
    "feedback": "Detailed feedback explaining the grade",
    "strengths": ["What the student did well"],
    "improvements": ["Areas for improvement"],
    "confidence": 0.9
}"""
            
            user_prompt = f"""Question: {question}

Model Answer: {model_answer}

Student Answer: {student_answer}

Maximum Score: {max_score}

Please grade this answer and provide detailed feedback."""
            
            # Make LLM call
            response = self.llm_service._make_api_call_with_retry({
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            })
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback: use LLM to fix JSON
                fixed_json = self.llm_service._get_structured_response(result_text)
                return json.loads(fixed_json)
                
        except Exception as e:
            logger.error(f"Error grading single answer: {str(e)}")
            return {
                "score": 0,
                "max_score": max_score,
                "percentage": 0,
                "feedback": f"Grading failed: {str(e)}",
                "confidence": 0.0
            }
    
    def _save_grading_results_with_retry(self, submission_id: str, marking_guide_id: str, results: List[Dict], session_id: str):
        """Save grading results to database with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Clear existing results for this session
                GradingResult.query.filter_by(
                    submission_id=submission_id,
                    grading_session_id=session_id
                ).delete()
                
                # Save new results
                for result in results:
                    grading_result = GradingResult(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        grading_session_id=session_id,
                        mapping_id=result.get('mapping_id'),
                        score=result.get('score', 0),
                        max_score=result.get('max_score', 0),
                        percentage=result.get('percentage', 0),
                        feedback=result.get('feedback', ''),
                        confidence=result.get('confidence', 0.0)
                    )
                    db.session.add(grading_result)
                
                # Commit immediately
                db.session.commit()
                logger.info(f"Successfully saved {len(results)} grading results")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock saving results on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to save grading results after {max_retries} attempts: {str(e)}")
                    raise
    
    def _update_grading_session_with_retry(self, grading_session: GradingSession, questions_graded: int):
        """Update grading session with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Refresh the session object to avoid stale data
                db.session.refresh(grading_session)
                
                # Update session
                grading_session.status = "completed"
                grading_session.total_questions_graded = questions_graded
                grading_session.processing_end_time = datetime.utcnow()
                
                # Commit immediately
                db.session.commit()
                logger.info(f"Successfully updated grading session {grading_session.id}")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock updating session on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to update grading session after {max_retries} attempts: {str(e)}")
                    raise
    
    def _commit_with_retry(self, operation_name: str):
        """Commit database changes with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                db.session.commit()
                logger.info(f"Successfully committed {operation_name}")
                return
            
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock during {operation_name} on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to commit {operation_name} after {max_retries} attempts: {str(e)}")
                    raise    

    def process_submission_grading(self, submission_id: str, marking_guide_id: str, max_questions_to_answer: Optional[int] = None) -> Tuple[Dict, Optional[str]]:
        """Process grading for a submission against a marking guide.
        
        Args:
            submission_id: Database ID of the submission
            marking_guide_id: Database ID of the marking guide
            max_questions_to_answer: Optional limit on questions to grade
            
        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message)
        """
        try:
            logger.info(f"Processing grading for submission {submission_id} with guide {marking_guide_id}")
            
            # Get submission and guide from database
            submission = Submission.query.get(submission_id)
            if not submission:
                return {}, f"Submission {submission_id} not found"
            
            guide = MarkingGuide.query.get(marking_guide_id)
            if not guide:
                return {}, f"Marking guide {marking_guide_id} not found"
            
            # Check if submission has content
            if not submission.content_text:
                return {}, "Submission content not available - OCR may be required"
            
            # Check if guide has structured questions
            if not guide.questions:
                return {}, "Marking guide not processed - structured questions not available"
            
            # Use the grading service to grade the submission
            from src.services.grading_service import GradingService
            from src.services.mapping_service import MappingService
            
            # Initialize services
            mapping_service = MappingService(llm_service=self.llm_service)
            grading_service = GradingService(llm_service=self.llm_service, mapping_service=mapping_service)
            
            # Prepare guide data for grading
            guide_data = {
                "raw_content": guide.content_text,
                "questions": guide.questions,
                "total_marks": guide.total_marks
            }
            
            # Grade the submission
            grading_result, error = grading_service.grade_submission(
                marking_guide_content=guide_data,
                student_submission_content=submission.content_text,
                guide_type=guide.questions.get('type', 'mixed') if isinstance(guide.questions, dict) else 'mixed'
            )
            
            if error:
                logger.error(f"Grading failed for submission {submission_id}: {error}")
                return {}, error
            
            # Apply max_questions_to_answer limit if specified
            if max_questions_to_answer and grading_result.get('criteria_scores'):
                # Sort by score and take top N questions
                criteria_scores = grading_result['criteria_scores']
                if len(criteria_scores) > max_questions_to_answer:
                    # Sort by points_earned/points_possible ratio (best performance first)
                    sorted_scores = sorted(
                        criteria_scores,
                        key=lambda x: x.get('points_earned', 0) / max(x.get('points_possible', 1), 1),
                        reverse=True
                    )
                    
                    # Take top N questions
                    limited_scores = sorted_scores[:max_questions_to_answer]
                    
                    # Recalculate totals
                    total_earned = sum(score.get('points_earned', 0) for score in limited_scores)
                    total_possible = sum(score.get('points_possible', 0) for score in limited_scores)
                    
                    # Update grading result
                    grading_result.update({
                        'criteria_scores': limited_scores,
                        'overall_score': total_earned,
                        'max_possible_score': total_possible,
                        'percent_score': (total_earned / total_possible * 100) if total_possible > 0 else 0,
                        'normalized_score': (total_earned / total_possible * 100) if total_possible > 0 else 0
                    })
                    
                    # Recalculate letter grade
                    from src.services.grading_service import GradingService
                    grading_result['letter_grade'] = GradingService()._get_letter_grade(grading_result['percent_score'])
                    
                    logger.info(f"Limited grading to top {max_questions_to_answer} questions for submission {submission_id}")
            
            # Save grading results to database
            try:
                # Create or update grading result record
                existing_result = GradingResult.query.filter_by(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id
                ).first()
                
                if existing_result:
                    # Update existing result
                    existing_result.score = grading_result.get('overall_score', 0)
                    existing_result.max_score = grading_result.get('max_possible_score', 0)
                    existing_result.percentage = grading_result.get('percent_score', 0)
                    existing_result.feedback = grading_result.get('detailed_feedback', {}).get('general', '')
                    existing_result.detailed_feedback = grading_result.get('detailed_feedback', {})
                    existing_result.grading_method = 'llm'
                    existing_result.updated_at = datetime.utcnow()
                else:
                    # Create new result
                    new_result = GradingResult(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        score=grading_result.get('overall_score', 0),
                        max_score=grading_result.get('max_possible_score', 0),
                        percentage=grading_result.get('percent_score', 0),
                        feedback=grading_result.get('detailed_feedback', {}).get('general', ''),
                        detailed_feedback=grading_result.get('detailed_feedback', {}),
                        grading_method='llm'
                    )
                    db.session.add(new_result)
                
                # Update submission status
                submission.processing_status = 'completed'
                submission.processed = True
                submission.updated_at = datetime.utcnow()
                
                db.session.commit()
                logger.info(f"Successfully saved grading results for submission {submission_id}")
                
            except Exception as db_error:
                logger.error(f"Error saving grading results to database: {str(db_error)}")
                db.session.rollback()
                # Continue with the grading result even if database save fails
            
            return grading_result, None
            
        except Exception as e:
            logger.error(f"Error processing submission grading {submission_id}: {str(e)}")
            return {}, f"Failed to process submission grading: {str(e)}"    

    def process_submission_grading(self, submission_id: str, marking_guide_id: str, max_questions_to_answer: Optional[int] = None) -> Tuple[Dict, Optional[str]]:
        """Process grading for a submission against a marking guide.
        
        Args:
            submission_id: Database ID of the submission
            marking_guide_id: Database ID of the marking guide
            max_questions_to_answer: Optional limit on questions to grade
            
        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message)
        """
        try:
            logger.info(f"Processing grading for submission {submission_id} with guide {marking_guide_id}")
            
            # Get submission and guide from database
            submission = Submission.query.get(submission_id)
            if not submission:
                return {}, f"Submission {submission_id} not found"
            
            guide = MarkingGuide.query.get(marking_guide_id)
            if not guide:
                return {}, f"Marking guide {marking_guide_id} not found"
            
            # Check if submission has content
            if not submission.content_text:
                return {}, "Submission content not available - OCR may not have been processed"
            
            # Check if guide has structured questions
            if not guide.questions:
                return {}, "Marking guide questions not available - guide may not have been processed"
            
            # Use the grading service to grade the submission
            from src.services.grading_service import GradingService
            from src.services.mapping_service import MappingService
            
            # Initialize services
            mapping_service = MappingService(llm_service=self.llm_service)
            grading_service = GradingService(llm_service=self.llm_service, mapping_service=mapping_service)
            
            # Prepare guide content for grading
            guide_content = {
                "raw_content": guide.content_text or "",
                "questions": guide.questions,
                "total_marks": guide.total_marks
            }
            
            # Grade the submission
            grading_result, grading_error = grading_service.grade_submission(
                marking_guide_content=guide_content,
                student_submission_content=submission.content_text,
                mapped_questions=None,  # Let the service handle mapping
                guide_type=None  # Let the service determine guide type
            )
            
            if grading_error:
                logger.error(f"Grading error for submission {submission_id}: {grading_error}")
                return {}, grading_error
            
            # Apply max_questions_to_answer limit if specified
            if max_questions_to_answer and grading_result.get('criteria_scores'):
                # Sort criteria by score (highest first) and limit
                criteria_scores = grading_result['criteria_scores']
                if len(criteria_scores) > max_questions_to_answer:
                    # Sort by percentage score descending
                    sorted_criteria = sorted(
                        criteria_scores, 
                        key=lambda x: x.get('similarity', 0), 
                        reverse=True
                    )
                    limited_criteria = sorted_criteria[:max_questions_to_answer]
                    
                    # Recalculate totals
                    total_earned = sum(c['points_earned'] for c in limited_criteria)
                    total_possible = sum(c['points_possible'] for c in limited_criteria)
                    
                    grading_result.update({
                        'criteria_scores': limited_criteria,
                        'overall_score': total_earned,
                        'max_possible_score': total_possible,
                        'percent_score': (total_earned / total_possible * 100) if total_possible > 0 else 0,
                        'normalized_score': (total_earned / total_possible * 100) if total_possible > 0 else 0
                    })
                    
                    # Recalculate letter grade
                    from src.services.grading_service import GradingService
                    grading_result['letter_grade'] = GradingService()._get_letter_grade(grading_result['percent_score'])
                    
                    logger.info(f"Limited grading to top {max_questions_to_answer} questions for submission {submission_id}")
            
            # Save grading results to database
            try:
                grading_result_record = GradingResult(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id,
                    score=grading_result.get('overall_score', 0),
                    max_score=grading_result.get('max_possible_score', 0),
                    percentage=grading_result.get('percent_score', 0),
                    feedback=grading_result.get('detailed_feedback', {}).get('general', ''),
                    detailed_feedback=grading_result.get('detailed_feedback', {}),
                    grading_method='llm',
                    confidence=0.85  # Default confidence for LLM grading
                )
                
                db.session.add(grading_result_record)
                
                # Update submission status
                submission.processing_status = 'completed'
                submission.processed = True
                
                db.session.commit()
                
                logger.info(f"Successfully saved grading results for submission {submission_id}")
                
            except Exception as db_error:
                logger.error(f"Error saving grading results to database: {str(db_error)}")
                db.session.rollback()
                # Continue with returning results even if database save fails
            
            return grading_result, None
            
        except Exception as e:
            logger.error(f"Error processing submission grading {submission_id}: {str(e)}")
            return {}, f"Failed to process submission grading: {str(e)}"