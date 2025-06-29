"""
Unified AI Processing Service with Progress Tracking
Combines mapping and grading into a single streamlined workflow with real-time progress updates.
"""

import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from src.database.models import db # Import db from models.py

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
        self.submission_processing_times: List[float] = [] # Initialize submission_processing_times
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

    @lru_cache(maxsize=128)
    def _cached_determine_guide_type(self, guide_content: str) -> Tuple[str, float]:
        """Cache guide type determination to avoid redundant LLM calls"""
        return self.mapping_service.determine_guide_type(guide_content)

    async def _process_single_submission(
        self,
        submission: Dict,
        marking_guide_content: Dict,
        guide_type: str,
        index: int,
        total_submissions: int,
        max_questions: Optional[int] = None
    ) -> Dict:
        """Process a single submission asynchronously using async mapping and grading."""
        submission_content = submission.get('content_text', submission.get('content', ''))
        submission_filename = submission.get('filename', f'submission_{index+1}')
        submission_start_time = time.time()

        try:
            if not submission_content:
                return {
                    'submission_id': submission.get('id', f'sub_{index}'),
                    'filename': submission_filename,
                    'status': 'error',
                    'error': 'Empty submission content',
                    'score': 0,
                    'max_score': 0,
                    'percentage': 0,
                    'letter_grade': 'F',
                    'details': 'No text could be extracted from the submission file.'
                }

            # Async mapping
            mapping_result, mapping_error = await self.mapping_service.map_submission_to_guide_async(
                marking_guide_content.get("raw_content", ""),
                submission_content,
                num_questions=max_questions
            )
            if mapping_error:
                logger.error(f"Mapping error for submission {submission_filename}: {mapping_error}")
                return {
                    'submission_id': submission.get('id', f'sub_{index}'),
                    'filename': submission_filename,
                    'status': 'error',
                    'error': mapping_error,
                    'score': 0,
                    'max_score': 0,
                    'percentage': 0,
                    'letter_grade': 'F'
                }

            # Async grading
            grading_result, grading_error = await self.grading_service.grade_submission_async(
                marking_guide_content,
                submission_content,
                mapped_questions=mapping_result.get('mappings'),
                guide_type=guide_type
            )
            if grading_error:
                logger.error(f"Grading error for submission {submission_filename}: {grading_error}")
                return {
                    'submission_id': submission.get('id', f'sub_{index}'),
                    'filename': submission_filename,
                    'status': 'error',
                    'error': grading_error,
                    'score': 0,
                    'max_score': 0,
                    'percentage': 0,
                    'letter_grade': 'F'
                }

            score = grading_result.get('score', 0)
            max_score = grading_result.get('max_score', 0)
            percentage = grading_result.get('percentage', 0)
            letter_grade = self._get_letter_grade(percentage)

            return {
                'submission_id': submission.get('id', f'sub_{index}'),
                'filename': submission_filename,
                'status': 'success',
                'score': score,
                'max_score': max_score,
                'percentage': round(percentage, 1),
                'letter_grade': letter_grade,
                'detailed_feedback': grading_result.get('detailed_feedback', {}),
                'mappings': mapping_result.get('mappings', []) if mapping_result else [],
                'guide_type': guide_type,
                'processing_time': time.time() - submission_start_time
            }

        except Exception as e:
            logger.error(f"Unexpected error during single submission processing for {submission_filename}: {str(e)}")
            return {
                'submission_id': submission.get('id', f'sub_{index}'),
                'filename': submission_filename,
                'status': 'error',
                'error': str(e),
                'score': 0,
                'max_score': 0,
                'percentage': 0,
                'letter_grade': 'F'
            }

    async def process_unified_ai_grading(self,
        submissions: List[Dict],
        marking_guide_content: Dict,
        max_questions: Optional[int] = None,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Refactored: Run all async processing in an event loop using asyncio.gather for parallelism.
        """
        error_message = "Unknown error during processing"  # Initialize with default
        try:
            # Initialize database connection
            if not db.session.is_active:
                logger.info("Initializing database connection")
                db.session.begin()
                db.create_all()  # Ensure tables exist
            self.start_time = time.time()
            if progress_callback:
                self.set_progress_callback(progress_callback)
            self.total_submissions = len(submissions)
            logger.info(f"Starting unified AI processing for {self.total_submissions} submissions")
            total_steps = 2 + self.total_submissions
            current_step = 0
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
            guide_type = "questions"
            guide_confidence = 0.5
            if self.mapping_service and self.mapping_service.llm_service:
                try:
                    guide_type, guide_confidence = self._cached_determine_guide_type(
                        marking_guide_content.get("raw_content", "")
                    )
                    logger.info(f"Guide type determined: {guide_type} (confidence: {guide_confidence})")
                except Exception as e:
                    logger.warning(f"Guide type determination failed: {str(e)}, using default")
            all_results = []
            successful_gradings = 0
            failed_gradings = 0
            total_score = 0
            total_max_score = 0
            batch_size = 2
            async def process_all():
                tasks = [self._process_single_submission(
                    submission,
                    marking_guide_content,
                    guide_type,
                    i,
                    len(submissions),
                    max_questions
                ) for i, submission in enumerate(submissions)]
                return await asyncio.gather(*tasks)
            batch_results = await process_all()
            for result in batch_results:
                all_results.append(result)
                if result['status'] == 'success':
                    successful_gradings += 1
                    total_score += result.get('score', 0)
                    total_max_score += result.get('max_score', 0)
                else:
                    failed_gradings += 1
                    logger.warning(f"Failed grading for submission {result.get('submission_id', 'unknown')}: {result.get('error', 'Unknown error')}")
            total_time = time.time() - self.start_time
            average_time = total_time / len(submissions) if submissions else 0
            success_rate = (successful_gradings / len(submissions)) * 100 if submissions else 0
            average_score = total_score / successful_gradings if successful_gradings > 0 else 0
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
            average_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
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
                    'processing_time': round(total_time, 2),
                    'guide_type': guide_type,
                    'guide_confidence': guide_confidence,
                },
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'processing_method': 'unified_ai_parallel',
                    'guide_analysis': {
                        'type': guide_type,
                        'confidence': guide_confidence
                    }
                }
            }
            logger.info(f"Unified AI processing completed in {total_time:.2f}s with {batch_size} parallel submissions")
            return result, None
        except RuntimeError as e:
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                error_message = "Unified AI processing failed: Please use asyncio.create_task() instead of asyncio.run() when inside an event loop"
            else:
                error_message: str = f"Unified AI processing failed: {str(e)}"
            logger.error(error_message)
            if self.progress_callback:
                self._update_progress(ProcessingProgress(
                    current_step=0,
                    total_steps=1,
                    current_operation="Error occurred",
                    submission_index=0,
                    total_submissions=len(submissions),
                    percentage=0,
                    status="error",
                    details=error_message
                ))
            return {
                'status': 'error',
                'message': error_message,
                'results': [],
                'summary': {
                    'successful': 0,
                    'failed': len(submissions),
                    'total': len(submissions)
                }
            }, error_message
        finally:
            # Cleanup database connection
            try:
                # Use the db variable that was imported at the top of the file
                # Cleanup session
                if db.session.is_active:
                    db.session.remove()
                    db.session.expunge_all()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
            if self.progress_callback:
                self._update_progress(ProcessingProgress(
                    current_step=0,
                    total_steps=1,
                    current_operation="Processing failed",
                    submission_index=0,
                    total_submissions=len(submissions),
                    percentage=0,
                    status="error",
                    details=str(e) if 'e' in locals() else error_message
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
