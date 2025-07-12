"""Refactored Unified AI Processing Pipeline.

This module implements the centralized, idempotent AI processing pipeline:
retrieve_text_from_db() → run_llm_mapping() → run_llm_grading() → select_best_answers() → save_to_database()

Features:
- Form-configured max_questions_to_answer from marking_guides table
- Centralized, one-time LLM processing
- Detailed step-by-step frontend progress tracking
- Idempotent design with session tracking
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import (
    db, MarkingGuide, Submission, Mapping, GradingResult, GradingSession
)
from utils.logger import logger


@dataclass
class ProcessingStepResult:
    """Result of a processing step."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    step_details: Optional[Dict] = None


@dataclass
class PipelineProgress:
    """Progress tracking for the refactored pipeline."""
    session_id: str
    submission_id: str
    guide_id: str
    status: str  # not_started, text_retrieval, mapping, grading, saving, completed, failed
    steps: Dict[str, str]  # step_name -> status (pending, in_progress, completed, failed)
    current_operation: str = ""
    progress_percentage: float = 0.0
    questions_mapped: int = 0
    questions_graded: int = 0
    max_questions_limit: Optional[int] = None
    start_time: float = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
        if not self.steps:
            self.steps = {
                "text_retrieval": "pending",
                "mapping": "pending", 
                "grading": "pending",
                "saving": "pending"
            }


class RefactoredUnifiedAIService:
    """Refactored unified AI processing service with centralized pipeline."""
    
    def __init__(self, llm_service=None, mapping_service=None, grading_service=None):
        """Initialize the refactored service."""
        self.llm_service = llm_service
        self.mapping_service = mapping_service
        self.grading_service = grading_service
        self.progress_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable):
        """Set progress callback for real-time updates."""
        self.progress_callback = callback
        
    def _update_progress(self, progress: PipelineProgress, step: str, status: str, 
                        operation: str = "", percentage: float = None):
        """Update progress and notify callback."""
        progress.steps[step] = status
        progress.status = step if status == "in_progress" else progress.status
        progress.current_operation = operation
        
        if percentage is not None:
            progress.progress_percentage = percentage
        else:
            # Calculate percentage based on completed steps
            completed_steps = sum(1 for s in progress.steps.values() if s == "completed")
            progress.progress_percentage = (completed_steps / len(progress.steps)) * 100
            
        # Update database session
        try:
            grading_session = db.session.query(GradingSession).filter_by(
                submission_id=progress.submission_id,
                marking_guide_id=progress.guide_id
            ).first()
            
            if grading_session:
                grading_session.status = "in_progress" if status == "in_progress" else grading_session.status
                grading_session.current_step = step
                grading_session.total_questions_mapped = progress.questions_mapped
                grading_session.total_questions_graded = progress.questions_graded
                if status == "failed":
                    grading_session.error_message = progress.error_message
                db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to update grading session: {e}")
            
        # Notify callback
        if self.progress_callback:
            self.progress_callback({
                "session_id": progress.session_id,
                "status": progress.status,
                "steps": progress.steps,
                "current_operation": progress.current_operation,
                "progress_percentage": progress.progress_percentage,
                "questions_mapped": progress.questions_mapped,
                "questions_graded": progress.questions_graded,
                "max_questions_limit": progress.max_questions_limit,
                "timestamp": datetime.now().isoformat()
            })
            
        logger.info(f"Progress update - {step}: {status} ({progress.progress_percentage:.1f}%) - {operation}")
    
    def retrieve_text_from_db(self, submission_id: str, guide_id: str) -> ProcessingStepResult:
        """Step 1: Retrieve cleaned OCR text and marking guide from database."""
        try:
            # Fetch submission
            submission = db.session.query(Submission).filter_by(id=submission_id).first()
            if not submission:
                return ProcessingStepResult(
                    success=False,
                    error=f"Submission {submission_id} not found"
                )
                
            # Fetch marking guide
            marking_guide = db.session.query(MarkingGuide).filter_by(id=guide_id).first()
            if not marking_guide:
                return ProcessingStepResult(
                    success=False,
                    error=f"Marking guide {guide_id} not found"
                )
                
            # Extract data
            submission_text = submission.content_text or ""
            guide_content = marking_guide.content_text or ""
            max_questions = marking_guide.max_questions_to_answer
            
            if not submission_text.strip():
                return ProcessingStepResult(
                    success=False,
                    error="Submission has no OCR text content"
                )
                
            if not guide_content.strip():
                return ProcessingStepResult(
                    success=False,
                    error="Marking guide has no content"
                )
                
            return ProcessingStepResult(
                success=True,
                data={
                    "submission": submission,
                    "marking_guide": marking_guide,
                    "submission_text": submission_text,
                    "guide_content": guide_content,
                    "max_questions_to_answer": max_questions
                },
                step_details={
                    "submission_length": len(submission_text),
                    "guide_length": len(guide_content),
                    "max_questions_limit": max_questions
                }
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in retrieve_text_from_db: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"Database error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in retrieve_text_from_db: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def run_llm_mapping(self, submission_text: str, guide_content: str, 
                       submission_id: str, guide_id: str) -> ProcessingStepResult:
        """Step 2: Use LLM to map all possible question-answer pairs (no limits)."""
        try:
            if not self.mapping_service:
                return ProcessingStepResult(
                    success=False,
                    error="Mapping service not available"
                )
                
            # Use LLM to map all possible Q&A pairs without limits
            logger.info(f"Starting LLM mapping for submission {submission_id}")
            
            # Call mapping service to get all possible mappings
            mapping_result = self.mapping_service.map_submission_to_guide(
                marking_guide_content=guide_content,
                student_submission_content=submission_text,
                num_questions=None  # No limit in mapping step
            )
            
            if not mapping_result or len(mapping_result) < 2:
                return ProcessingStepResult(
                    success=False,
                    error="Mapping service returned invalid result"
                )
                
            mappings_data, error_msg = mapping_result
            
            if error_msg:
                return ProcessingStepResult(
                    success=False,
                    error=f"Mapping failed: {error_msg}"
                )
                
            if not mappings_data or 'mappings' not in mappings_data:
                return ProcessingStepResult(
                    success=False,
                    error="No mappings found in result"
                )
                
            mappings = mappings_data['mappings']
            total_mapped = len(mappings)
            
            logger.info(f"LLM mapping completed: {total_mapped} question-answer pairs mapped")
            
            return ProcessingStepResult(
                success=True,
                data={
                    "mappings": mappings,
                    "mapping_metadata": mappings_data.get('metadata', {}),
                    "total_mapped": total_mapped
                },
                step_details={
                    "total_mappings_found": total_mapped,
                    "mapping_method": "llm"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in run_llm_mapping: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"LLM mapping failed: {str(e)}"
            )
    
    def run_llm_grading(self, mappings: List[Dict], guide_content: str, 
                       submission_text: str) -> ProcessingStepResult:
        """Step 3: Grade each mapped Q&A pair using LLM."""
        try:
            if not self.grading_service:
                return ProcessingStepResult(
                    success=False,
                    error="Grading service not available"
                )
                
            logger.info(f"Starting LLM grading for {len(mappings)} mappings")
            
            graded_results = []
            
            for i, mapping in enumerate(mappings):
                try:
                    # Grade individual mapping
                    grading_result = self.grading_service.grade_submission_optimized(
                        submission_content=submission_text,
                        marking_guide=guide_content,
                        mapped_data={"mappings": [mapping]}
                    )
                    
                    if grading_result and 'results' in grading_result:
                        # Extract grading details
                        result = grading_result['results'][0] if grading_result['results'] else {}
                        
                        graded_mapping = {
                            "mapping": mapping,
                            "score": result.get('score', 0.0),
                            "max_score": result.get('max_score', 0.0),
                            "percentage": result.get('percentage', 0.0),
                            "feedback": result.get('feedback', ''),
                            "detailed_feedback": result.get('detailed_feedback', {}),
                            "confidence": result.get('confidence', 0.0),
                            "grading_method": "llm"
                        }
                        
                        graded_results.append(graded_mapping)
                        
                    logger.debug(f"Graded mapping {i+1}/{len(mappings)}")
                    
                except Exception as e:
                    logger.warning(f"Failed to grade mapping {i+1}: {e}")
                    # Continue with other mappings
                    continue
                    
            if not graded_results:
                return ProcessingStepResult(
                    success=False,
                    error="No mappings could be graded successfully"
                )
                
            logger.info(f"LLM grading completed: {len(graded_results)} mappings graded")
            
            return ProcessingStepResult(
                success=True,
                data={
                    "graded_mappings": graded_results,
                    "total_graded": len(graded_results)
                },
                step_details={
                    "total_graded": len(graded_results),
                    "grading_method": "llm"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in run_llm_grading: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"LLM grading failed: {str(e)}"
            )
    
    def select_best_answers(self, graded_mappings: List[Dict], 
                           max_questions: Optional[int]) -> ProcessingStepResult:
        """Step 4: Select the best N answers based on max_questions_to_answer."""
        try:
            if not graded_mappings:
                return ProcessingStepResult(
                    success=False,
                    error="No graded mappings to select from"
                )
                
            # Sort by score (descending) and confidence (descending)
            sorted_mappings = sorted(
                graded_mappings,
                key=lambda x: (x.get('score', 0), x.get('confidence', 0)),
                reverse=True
            )
            
            # Apply limit if specified
            if max_questions and max_questions > 0:
                selected_mappings = sorted_mappings[:max_questions]
                logger.info(f"Selected top {len(selected_mappings)} answers (limit: {max_questions})")
            else:
                selected_mappings = sorted_mappings
                logger.info(f"Selected all {len(selected_mappings)} answers (no limit)")
                
            return ProcessingStepResult(
                success=True,
                data={
                    "selected_mappings": selected_mappings,
                    "total_selected": len(selected_mappings),
                    "total_available": len(graded_mappings)
                },
                step_details={
                    "selection_criteria": "score_and_confidence",
                    "limit_applied": max_questions,
                    "selected_count": len(selected_mappings)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in select_best_answers: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"Answer selection failed: {str(e)}"
            )
    
    def save_to_database(self, selected_mappings: List[Dict], submission_id: str, 
                        guide_id: str, session_id: str) -> ProcessingStepResult:
        """Step 5: Save results to mapped_questions, graded_responses, and grading_sessions tables."""
        try:
            saved_mappings = []
            saved_results = []
            
            # Begin transaction
            db.session.begin()
            
            for mapping_data in selected_mappings:
                mapping_info = mapping_data['mapping']
                
                # Create Mapping record
                mapping_record = Mapping(
                    submission_id=submission_id,
                    guide_question_id=mapping_info.get('question_id', 'unknown'),
                    guide_question_text=mapping_info.get('question_text', ''),
                    guide_answer=mapping_info.get('expected_answer', ''),
                    max_score=mapping_data.get('max_score', 0.0),
                    submission_answer=mapping_info.get('student_answer', ''),
                    match_score=mapping_info.get('match_score', 0.0),
                    match_reason=mapping_info.get('match_reason', ''),
                    mapping_method="llm"
                )
                
                db.session.add(mapping_record)
                db.session.flush()  # Get the ID
                
                # Create GradingResult record
                grading_record = GradingResult(
                    submission_id=submission_id,
                    marking_guide_id=guide_id,
                    mapping_id=mapping_record.id,
                    score=mapping_data.get('score', 0.0),
                    max_score=mapping_data.get('max_score', 0.0),
                    percentage=mapping_data.get('percentage', 0.0),
                    feedback=mapping_data.get('feedback', ''),
                    detailed_feedback=mapping_data.get('detailed_feedback', {}),
                    grading_method="llm",
                    confidence=mapping_data.get('confidence', 0.0)
                )
                
                db.session.add(grading_record)
                
                saved_mappings.append(mapping_record)
                saved_results.append(grading_record)
                
            # Update grading session
            grading_session = db.session.query(GradingSession).filter_by(
                submission_id=submission_id,
                marking_guide_id=guide_id
            ).first()
            
            if grading_session:
                grading_session.status = "completed"
                grading_session.current_step = "saving"
                grading_session.total_questions_mapped = len(saved_mappings)
                grading_session.total_questions_graded = len(saved_results)
                grading_session.processing_end_time = datetime.utcnow()
            
            # Update submission status
            submission = db.session.query(Submission).filter_by(id=submission_id).first()
            if submission:
                submission.processing_status = "completed"
                submission.processed = True
                
            # Commit transaction
            db.session.commit()
            
            logger.info(f"Successfully saved {len(saved_mappings)} mappings and {len(saved_results)} grading results")
            
            return ProcessingStepResult(
                success=True,
                data={
                    "mappings_saved": len(saved_mappings),
                    "results_saved": len(saved_results),
                    "session_updated": True
                },
                step_details={
                    "database_records_created": len(saved_mappings) + len(saved_results),
                    "session_status": "completed"
                }
            )
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in save_to_database: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"Database save failed: {str(e)}"
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in save_to_database: {e}")
            return ProcessingStepResult(
                success=False,
                error=f"Save operation failed: {str(e)}"
            )
    
    def create_or_get_session(self, submission_id: str, guide_id: str, 
                             user_id: str) -> Tuple[str, bool]:
        """Create or get existing grading session. Returns (session_id, is_new)."""
        try:
            # Check for existing session
            existing_session = db.session.query(GradingSession).filter_by(
                submission_id=submission_id,
                marking_guide_id=guide_id
            ).first()
            
            if existing_session and existing_session.status in ["completed", "in_progress"]:
                # Return existing session if completed or in progress
                return existing_session.id, False
                
            # Create new session
            progress_id = str(uuid.uuid4())
            
            # Get max_questions from marking guide
            marking_guide = db.session.query(MarkingGuide).filter_by(id=guide_id).first()
            max_questions = marking_guide.max_questions_to_answer if marking_guide else None
            
            grading_session = GradingSession(
                submission_id=submission_id,
                marking_guide_id=guide_id,
                user_id=user_id,
                progress_id=progress_id,
                status="not_started",
                max_questions_limit=max_questions,
                processing_start_time=datetime.utcnow()
            )
            
            db.session.add(grading_session)
            db.session.commit()
            
            logger.info(f"Created new grading session {grading_session.id} for submission {submission_id}")
            return grading_session.id, True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating grading session: {e}")
            raise
    
    def process_submission(self, submission_id: str, guide_id: str, 
                          user_id: str) -> Dict[str, Any]:
        """Main pipeline: Execute the complete refactored processing workflow."""
        start_time = time.time()
        
        try:
            # Create or get session
            session_id, is_new = self.create_or_get_session(submission_id, guide_id, user_id)
            
            # Initialize progress tracking
            progress = PipelineProgress(
                session_id=session_id,
                submission_id=submission_id,
                guide_id=guide_id,
                status="not_started"
            )
            
            logger.info(f"Starting refactored AI processing pipeline for submission {submission_id}")
            
            # Step 1: Retrieve text from database
            self._update_progress(progress, "text_retrieval", "in_progress", 
                                "Retrieving submission and guide data", 10)
            
            retrieval_result = self.retrieve_text_from_db(submission_id, guide_id)
            if not retrieval_result.success:
                self._update_progress(progress, "text_retrieval", "failed", 
                                    f"Failed: {retrieval_result.error}")
                progress.error_message = retrieval_result.error
                return self._create_error_response(retrieval_result.error, progress)
                
            self._update_progress(progress, "text_retrieval", "completed", 
                                "Data retrieved successfully", 25)
            
            # Extract data
            data = retrieval_result.data
            progress.max_questions_limit = data['max_questions_to_answer']
            
            # Step 2: Run LLM mapping
            self._update_progress(progress, "mapping", "in_progress", 
                                "Mapping questions and answers", 30)
            
            mapping_result = self.run_llm_mapping(
                data['submission_text'], 
                data['guide_content'],
                submission_id,
                guide_id
            )
            
            if not mapping_result.success:
                self._update_progress(progress, "mapping", "failed", 
                                    f"Failed: {mapping_result.error}")
                progress.error_message = mapping_result.error
                return self._create_error_response(mapping_result.error, progress)
                
            progress.questions_mapped = mapping_result.data['total_mapped']
            self._update_progress(progress, "mapping", "completed", 
                                f"Mapped {progress.questions_mapped} question-answer pairs", 50)
            
            # Step 3: Run LLM grading
            self._update_progress(progress, "grading", "in_progress", 
                                "Grading mapped answers", 55)
            
            grading_result = self.run_llm_grading(
                mapping_result.data['mappings'],
                data['guide_content'],
                data['submission_text']
            )
            
            if not grading_result.success:
                self._update_progress(progress, "grading", "failed", 
                                    f"Failed: {grading_result.error}")
                progress.error_message = grading_result.error
                return self._create_error_response(grading_result.error, progress)
                
            progress.questions_graded = grading_result.data['total_graded']
            self._update_progress(progress, "grading", "completed", 
                                f"Graded {progress.questions_graded} answers", 75)
            
            # Step 4: Select best answers
            selection_result = self.select_best_answers(
                grading_result.data['graded_mappings'],
                progress.max_questions_limit
            )
            
            if not selection_result.success:
                progress.error_message = selection_result.error
                return self._create_error_response(selection_result.error, progress)
            
            # Step 5: Save to database
            self._update_progress(progress, "saving", "in_progress", 
                                "Saving results to database", 80)
            
            save_result = self.save_to_database(
                selection_result.data['selected_mappings'],
                submission_id,
                guide_id,
                session_id
            )
            
            if not save_result.success:
                self._update_progress(progress, "saving", "failed", 
                                    f"Failed: {save_result.error}")
                progress.error_message = save_result.error
                return self._create_error_response(save_result.error, progress)
                
            self._update_progress(progress, "saving", "completed", 
                                "Results saved successfully", 100)
            
            # Mark as completed
            progress.status = "completed"
            
            processing_time = time.time() - start_time
            
            logger.info(f"Refactored AI processing completed successfully in {processing_time:.2f}s")
            
            return {
                "success": True,
                "session_id": session_id,
                "submission_id": submission_id,
                "guide_id": guide_id,
                "processing_time": processing_time,
                "questions_mapped": progress.questions_mapped,
                "questions_graded": progress.questions_graded,
                "questions_selected": selection_result.data['total_selected'],
                "max_questions_limit": progress.max_questions_limit,
                "mappings_saved": save_result.data['mappings_saved'],
                "results_saved": save_result.data['results_saved'],
                "status": "completed",
                "steps": progress.steps
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in process_submission: {e}")
            progress.error_message = str(e)
            progress.status = "failed"
            return self._create_error_response(str(e), progress)
    
    def _create_error_response(self, error_message: str, progress: PipelineProgress) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "error": error_message,
            "session_id": progress.session_id,
            "submission_id": progress.submission_id,
            "guide_id": progress.guide_id,
            "status": "failed",
            "steps": progress.steps,
            "questions_mapped": progress.questions_mapped,
            "questions_graded": progress.questions_graded,
            "max_questions_limit": progress.max_questions_limit
        }
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a processing session."""
        try:
            grading_session = db.session.query(GradingSession).filter_by(id=session_id).first()
            if not grading_session:
                return None
                
            return {
                "session_id": session_id,
                "submission_id": grading_session.submission_id,
                "guide_id": grading_session.marking_guide_id,
                "status": grading_session.status,
                "current_step": grading_session.current_step,
                "questions_mapped": grading_session.total_questions_mapped,
                "questions_graded": grading_session.total_questions_graded,
                "max_questions_limit": grading_session.max_questions_limit,
                "error_message": grading_session.error_message,
                "created_at": grading_session.created_at.isoformat(),
                "updated_at": grading_session.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None