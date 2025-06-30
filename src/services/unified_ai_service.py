"""
Unified AI Processing Service with Progress Tracking
Combines mapping and grading into a single streamlined workflow with real-time progress updates.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

from utils.logger import logger


@dataclass
class ProcessingProgress:
    """Data class for tracking processing progress"""
    current_step: int
    total_steps: int
    current_operation: str
    submission_index: int
    total_submissions: int
    percentage: float
    estimated_time_remaining: Optional[float] = None
    status: str = "processing"  # processing, completed, error
    details: Optional[str] = None


class UnifiedAIService:
    """
    Unified AI Processing Service that combines mapping and grading into a single workflow
    with comprehensive progress tracking and real-time status updates.
    """

    def __init__(self, mapping_service=None, grading_service=None, llm_service=None):
        """
        Initialize the unified AI service.
        
        Args:
            mapping_service: MappingService instance
            grading_service: GradingService instance  
            llm_service: LLMService instance
        """
        if mapping_service is None:
            raise ValueError("MappingService must be provided to UnifiedAIService")
        if grading_service is None:
            raise ValueError("GradingService must be provided to UnifiedAIService")
        if llm_service is None:
            raise ValueError("LLMService must be provided to UnifiedAIService")

        self.mapping_service = mapping_service
        self.grading_service = grading_service
        self.llm_service = llm_service
        
        # Progress tracking
        self.progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
        self.start_time: Optional[float] = None
        self.processing_times: List[float] = []
        self.total_submissions: int = 0 # Initialize total_submissions
        
        logger.info("Unified AI Service initialized")

    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def _update_progress(self, progress: ProcessingProgress):
        """Update progress and call callback if set"""
        if self.progress_callback:
            self.progress_callback(progress)
        
        logger.info(f"Progress: {progress.percentage:.1f}% - {progress.current_operation}")

    def _estimate_time_remaining(self, current_step: int) -> float:
        if current_step == 0 or not self.start_time or self.total_submissions == 0:
            return 0.0
        elapsed_time = time.time() - self.start_time
        progress_ratio = current_step / self.total_submissions
        if progress_ratio == 0:
            return float('inf')  # Avoid division by zero
        estimated_total_time = elapsed_time / progress_ratio
        return max(0.0, estimated_total_time - elapsed_time) # Ensure non-negative time

    def process_unified_ai_grading(
        self,
        marking_guide_content: Dict,
        submissions: List[Dict],
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
        max_questions: Optional[int] = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Process unified AI grading with mapping and grading combined.
        
        Args:
            marking_guide_content: Content of the marking guide
            submissions: List of submission dictionaries
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple[Dict, Optional[str]]: (Results, Error message if any)
        """
        try:
            self.start_time = time.time()
            if progress_callback:
                self.set_progress_callback(progress_callback)
            
            self.total_submissions = len(submissions) # Set total_submissions
            logger.info(f"Starting unified AI processing for {self.total_submissions} submissions")
            
            # Calculate total steps for progress tracking
            # Steps: 1. Guide analysis, 2-N. Process each submission, N+1. Finalize results
            total_steps = 2 + self.total_submissions
            current_step = 0
            
            # Step 1: Analyze marking guide
            current_step += 1
            self._update_progress(ProcessingProgress(
                current_step=current_step,
                total_steps=total_steps,
                current_operation="Analyzing marking guide structure...",
                submission_index=0,
                total_submissions=len(submissions),
                percentage=(current_step / total_steps) * 100,
                estimated_time_remaining=self._estimate_time_remaining(current_step)
            ))
            
            # Determine guide type once for all submissions
            guide_type = "questions"  # Default
            guide_confidence = 0.5
            
            if self.mapping_service and self.mapping_service.llm_service:
                try:
                    guide_type, guide_confidence = self.mapping_service.determine_guide_type(
                        marking_guide_content.get("raw_content", "")
                    )
                    logger.info(f"Guide type determined: {guide_type} (confidence: {guide_confidence})")
                except Exception as e:
                    logger.warning(f"Guide type determination failed: {str(e)}, using default")
            
            # Initialize results
            all_results = []
            successful_gradings = 0
            failed_gradings = 0
            total_score = 0
            total_max_score = 0
            
            # Step 2: Process each submission with unified mapping + grading
            for i, submission in enumerate(submissions):
                current_step += 1
                submission_content = submission.get('content_text', submission.get('content', ''))
                submission_filename = submission.get('filename', f'submission_{i+1}')
                
                if not submission_content:
                    logger.warning(f"No content found for submission {submission_filename}. Skipping.")
                    failed_gradings += 1
                    all_results.append({
                        'submission_id': submission.get('id', f'sub_{i}'),
                        'filename': submission_filename,
                        'status': 'error',
                        'error': 'Empty submission content',
                        'score': 0,
                        'max_score': 0,
                        'percentage': 0,
                        'letter_grade': 'F',
                        'details': 'No text could be extracted from the submission file. Please ensure the file contains readable text or images.'
                    })
                    self._update_progress(ProcessingProgress(
                        current_step=current_step,
                        total_steps=total_steps,
                        current_operation=f"Skipping empty submission {submission_filename}",
                        submission_index=i + 1,
                        total_submissions=len(submissions),
                        percentage=(current_step / total_steps) * 100,
                        estimated_time_remaining=self._estimate_time_remaining(current_step),
                        details="No content found for this submission. It will be marked as failed."
                    ))
                    continue
                
                # Calculate and update progress for current submission
                current_percentage = int((current_step / total_steps) * 100)
                self._update_progress(ProcessingProgress(
                    current_step=current_step,
                    total_steps=total_steps,
                    current_operation=f"Processing {submission_filename}",
                    submission_index=i + 1,
                    total_submissions=len(submissions),
                    percentage=current_percentage,
                    estimated_time_remaining=self._estimate_time_remaining(current_step),
                    details=f"Mapping answers and grading submission {i+1} of {len(submissions)}"
                ))
                
                try:
                    mapping_result = None
                    mapping_error = None
                    if self.mapping_service:
                        mapping_result, mapping_error = self.mapping_service.map_submission_to_guide(
                            marking_guide_content.get("raw_content", ""), submission_content, num_questions=max_questions
                        )

                    if mapping_error:
                        logger.error(f"Mapping failed for {submission_filename}: {mapping_error}")
                        failed_gradings += 1
                        all_results.append({
                            'submission_id': submission.get('id', f'sub_{i}'),
                            'filename': submission_filename,
                            'status': 'error',
                            'error': mapping_error,
                            'score': 0,
                            'max_score': 0,
                            'percentage': 0,
                            'letter_grade': 'F'
                        })
                        continue

                    grading_result = None
                    grading_error = None
                    if self.grading_service and mapping_result:
                        # Pass the mapped questions and answers to the grading service
                        # Assuming mapping_result contains 'mapped_questions' and 'student_answers'
                        grading_result, grading_error = self.grading_service.grade_submission(
                            marking_guide_content, submission_content, 
                            mapped_questions=mapping_result.get('mappings'),
                            guide_type=guide_type
                        )

                    if grading_error:
                        logger.error(f"Grading failed for {submission_filename}: {grading_error}")
                        failed_gradings += 1
                        all_results.append({
                            'submission_id': submission.get('id', f'sub_{i}'),
                            'filename': submission_filename,
                            'status': 'error',
                            'error': grading_error,
                            'score': 0,
                            'max_score': 0,
                            'percentage': 0,
                            'letter_grade': 'F'
                        })
                        continue

                    if not mapping_result and not grading_result:
                        logger.warning("No mapping or grading service available, or no results generated.")
                        failed_gradings += 1
                        all_results.append({
                            'submission_id': submission.get('id', f'sub_{i}'),
                            'filename': submission_filename,
                            'status': 'error',
                            'error': 'No AI services available or no results generated',
                            'score': 0,
                            'max_score': 0,
                            'percentage': 0,
                            'letter_grade': 'F'
                        })
                        continue

                    # Extract grading results
                    score = grading_result.get('score', 0)
                    max_score = grading_result.get('max_score', 0)
                    percentage = grading_result.get('percentage', 0)

                    # Calculate letter grade
                    letter_grade = self._get_letter_grade(percentage)

                    successful_gradings += 1
                    total_score += score
                    total_max_score += max_score

                    all_results.append({
                        'submission_id': submission.get('id', f'sub_{i}'),
                        'filename': submission_filename,
                        'status': 'success',
                        'score': score,
                        'max_score': max_score,
                        'percentage': round(percentage, 1),
                        'letter_grade': letter_grade,
                        'detailed_feedback': grading_result.get('detailed_feedback', {}),
                        'mappings': mapping_result.get('mappings', []) if mapping_result else [],
                        'guide_type': guide_type,
                        'processing_time': time.time() - self.start_time
                    })

                    logger.info(f"Successfully processed {submission_filename}: {percentage:.1f}%")
                
                except Exception as e:
                    logger.error(f"Error processing {submission_filename}: {str(e)}")
                    failed_gradings += 1
                    all_results.append({
                        'submission_id': submission.get('id', f'sub_{i}'),
                        'filename': submission_filename,
                        'status': 'error',
                        'error': str(e),
                        'score': 0,
                        'max_score': 0,
                        'percentage': 0,
                        'letter_grade': 'F'
                    })
            
            # Step 3: Finalize results
            current_step += 1
            self._update_progress(ProcessingProgress(
                current_step=current_step,
                total_steps=total_steps,
                current_operation="Finalizing results and generating summary...",
                submission_index=len(submissions),
                total_submissions=len(submissions),
                percentage=100.0,
                status="completed",
                details=f"Processed {successful_gradings} successful, {failed_gradings} failed"
            ))
            
            # Calculate summary statistics
            average_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            processing_time = time.time() - self.start_time
            
            # Create comprehensive result
            result = {
                'status': 'success',
                'message': f'Unified AI processing completed: {successful_gradings} successful, {failed_gradings} failed',
                'results': all_results,
                'summary': {
                    'successful': successful_gradings,
                    'failed': failed_gradings,
                    'total': len(submissions),
                    'total_score': total_score,
                    'total_max_score': total_max_score,
                    'average_percentage': round(average_percentage, 1),
                    'processing_time': round(processing_time, 2),
                    'guide_type': guide_type,
                    'guide_confidence': guide_confidence
                },
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'processing_method': 'unified_ai',
                    'guide_analysis': {
                        'type': guide_type,
                        'confidence': guide_confidence
                    }
                }
            }
            
            logger.info(f"Unified AI processing completed in {processing_time:.2f}s: {average_percentage:.1f}% average")
            return result, None
            
        except Exception as e:
            error_message = f"Unified AI processing failed: {str(e)}"
            logger.error(error_message)
            
            # Update progress with error status
            if self.progress_callback:
                self._update_progress(ProcessingProgress(
                    current_step=0,
                    total_steps=1,
                    current_operation="Processing failed",
                    submission_index=0,
                    total_submissions=len(submissions),
                    percentage=0,
                    status="error",
                    details=str(e)
                ))
            
            return {'status': 'error', 'message': error_message}, error_message

    def _get_letter_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade"""
        if percentage >= 97: return "A+"
        elif percentage >= 93: return "A"
        elif percentage >= 90: return "A-"
        elif percentage >= 87: return "B+"
        elif percentage >= 83: return "B"
        elif percentage >= 80: return "B-"
        elif percentage >= 77: return "C+"
        elif percentage >= 73: return "C"
        elif percentage >= 70: return "C-"
        elif percentage >= 67: return "D+"
        elif percentage >= 63: return "D"
        elif percentage >= 60: return "D-"
        else: return "F"

    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'service_type': 'unified_ai',
            'mapping_service_available': self.mapping_service is not None,
            'grading_service_available': self.grading_service is not None,
            'llm_service_available': self.llm_service is not None,
            'processing_times': self.processing_times[-10:] if self.processing_times else [],
            'average_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }
