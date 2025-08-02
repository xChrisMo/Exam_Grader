"""Optimized Background Tasks with enhanced pipeline orchestration and progress tracking."""
from typing import List

import json
import time
from datetime import datetime, timezone

from celery import Celery
from celery.utils.log import get_task_logger

from src.services.consolidated_ocr_service import ConsolidatedOCRService as OptimizedOCRService
from src.services.consolidated_mapping_service import ConsolidatedMappingService as OptimizedMappingService
from src.services.consolidated_grading_service import ConsolidatedGradingService as OptimizedGradingService
from src.services.consolidated_llm_service import ConsolidatedLLMService as LLMService
from src.database.models import Submission, MarkingGuide, GradingResult, Mapping
from src.database.models import db
from utils.logger import logger
try:
    from utils.socketio_utils import broadcast_update
except ImportError:
    def broadcast_update(event, data):
        pass

# Initialize Celery
celery_app = Celery('exam_grader')
celery_logger = get_task_logger(__name__)

# Initialize optimized services
ocr_service = OptimizedOCRService(
    # Redis removed - using in-memory caching instead
)
llm_service = LLMService()
mapping_service = OptimizedMappingService(llm_service)
grading_service = OptimizedGradingService(llm_service, mapping_service)

class ProcessingProgress:
    """Enhanced progress tracking for optimized pipeline."""
    
    def __init__(self, task_id: str, total_submissions: int = 1):
        self.task_id = task_id
        self.total_submissions = total_submissions
        self.current_submission = 0
        self.current_stage = "initializing"
        self.stage_progress = 0
        self.start_time = time.time()
        self.errors = []
        self.warnings = []
        
        self.stage_weights = {
            "ocr": 0.3,
            "mapping": 0.3,
            "grading": 0.4
        }
    
    def update_stage(self, stage: str, progress: float = 0, message: str = ""):
        """Update current processing stage."""
        self.current_stage = stage
        self.stage_progress = max(0, min(100, progress))
        
        overall_progress = self._calculate_overall_progress()
        
        # Broadcast update
        self._broadcast_progress(overall_progress, message)
    
    def update_submission(self, submission_index: int, message: str = ""):
        """Update current submission being processed."""
        self.current_submission = submission_index
        overall_progress = self._calculate_overall_progress()
        self._broadcast_progress(overall_progress, message)
    
    def add_error(self, error: str):
        """Add error to tracking."""
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "stage": self.current_stage
        })
    
    def add_warning(self, warning: str):
        """Add warning to tracking."""
        self.warnings.append({
            "timestamp": datetime.now().isoformat(),
            "warning": warning,
            "stage": self.current_stage
        })
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_submissions == 0:
            return 100
        
        # Progress per submission
        submission_progress = (self.current_submission / self.total_submissions) * 100
        
        # Current submission stage progress
        stage_weight = self.stage_weights.get(self.current_stage, 0.33)
        current_submission_stage_progress = (self.stage_progress / 100) * stage_weight * (100 / self.total_submissions)
        
        return min(100, submission_progress + current_submission_stage_progress)
    
    def _broadcast_progress(self, progress: float, message: str = ""):
        """Broadcast progress update via WebSocket."""
        try:
            update_data = {
                "task_id": self.task_id,
                "progress": round(progress, 1),
                "stage": self.current_stage,
                "stage_progress": self.stage_progress,
                "current_submission": self.current_submission,
                "total_submissions": self.total_submissions,
                "message": message,
                "elapsed_time": round(time.time() - self.start_time, 1),
                "errors_count": len(self.errors),
                "warnings_count": len(self.warnings)
            }
            
            broadcast_update('processing_progress', update_data)
            
        except Exception as e:
            celery_logger.warning(f"Failed to broadcast progress: {e}")

@celery_app.task(bind=True)
def process_optimized_ocr_task(self, submission_id: int, file_paths: List[str]):
    """Optimized OCR processing with parallel execution and caching."""
    
    progress = ProcessingProgress(self.request.id)
    
    try:
        progress.update_stage("ocr", 0, "Starting OCR processing")
        
        # Get submission
        submission = db.session.get(Submission, submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Process multiple files in parallel
        if len(file_paths) > 1:
            progress.update_stage("ocr", 10, f"Processing {len(file_paths)} files in parallel")
            results = ocr_service.extract_text_from_multiple_images_parallel(file_paths)
        else:
            progress.update_stage("ocr", 10, "Processing single file")
            text = ocr_service.extract_text_from_image(file_paths[0])
            results = [(file_paths[0], text, None)]
        
        progress.update_stage("ocr", 70, "Combining OCR results")
        
        # Combine results
        combined_text = ""
        errors = []
        
        for file_path, text, error in results:
            if error:
                errors.append(f"OCR failed for {file_path}: {error}")
                progress.add_error(f"OCR failed for {file_path}: {error}")
            else:
                combined_text += f"\n\n--- Page {file_path} ---\n{text}"
        
        if not combined_text.strip():
            raise ValueError("No text extracted from any files")
        
        progress.update_stage("ocr", 90, "Saving OCR results")
        
        # Update submission
        submission.raw_text = combined_text.strip()
        submission.status = 'ocr_completed'
        submission.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        progress.update_stage("ocr", 100, "OCR processing completed")
        
        return {
            'success': True,
            'submission_id': submission_id,
            'text_length': len(combined_text),
            'files_processed': len(file_paths),
            'errors': errors
        }
        
    except Exception as e:
        error_msg = f"OCR processing failed: {str(e)}"
        celery_logger.error(error_msg)
        progress.add_error(error_msg)
        
        # Update submission status
        try:
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.status = 'ocr_failed'
                submission.updated_at = datetime.now(timezone.utc)
                db.session.commit()
        except Exception:
            pass
        
        return {
            'success': False,
            'submission_id': submission_id,
            'error': error_msg
        }

@celery_app.task(bind=True)
def process_optimized_full_pipeline(self, submission_ids: List[int], marking_guide_id: int):
    """Optimized full pipeline with enhanced efficiency and redundancy elimination."""
    
    progress = ProcessingProgress(self.request.id, len(submission_ids))
    
    try:
        progress.update_stage("initializing", 0, "Loading marking guide and submissions")
        
        # Load marking guide
        marking_guide = db.session.get(MarkingGuide, marking_guide_id)
        if not marking_guide:
            raise ValueError(f"Marking guide {marking_guide_id} not found")
        
        # Load submissions
        submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
        if not submissions:
            raise ValueError("No submissions found")
        
        submission_data = []
        for submission in submissions:
            if submission.raw_text:
                submission_data.append({
                    'id': submission.id,
                    'content': submission.raw_text,
                    'student_name': getattr(submission, 'student_name', f'Student_{submission.id}')
                })
        
        if not submission_data:
            raise ValueError("No submissions with text content found")
        
        # Initialize optimized unified service
        try:
            from src.services.core_service import core_service as ConsolidatedUnifiedAIService
            # Use consolidated service with backward compatibility
            unified_service = ConsolidatedUnifiedAIService(
                mapping_service=mapping_service,
                grading_service=grading_service,
                llm_service=llm_service
            )
        except ImportError:
            return self._process_fallback_pipeline(submission_data, marking_guide, progress)
        
        # Set up progress callback
        def progress_callback(progress_data):
            progress.update_stage(
                progress_data.get('stage', 'processing'),
                progress_data.get('percentage', 0),
                progress_data.get('message', '')
            )
        
        unified_service.set_progress_callback(progress_callback)
        
        # Process all submissions with optimizations
        guide_data = {
            'content': marking_guide.content,
            'max_questions': getattr(marking_guide, 'max_questions', 10)
        }
        
        batch_result = unified_service.process_batch_optimized(
            guide_data=guide_data,
            submissions=submission_data,
            progress_id=self.request.id
        )
        
        # Save results to database
        saved_count = 0
        results = []
        
        for result in batch_result['results']:
            try:
                submission_id = result['submission_id']
                mapping_data = result['mapping']
                grading_data = result['grading']
                
                # Handle duplicate detection
                if result.get('is_duplicate'):
                    original_id = result.get('original_submission_id')
                    existing_mapping = Mapping.query.filter_by(
                        submission_id=original_id, 
                        marking_guide_id=marking_guide_id
                    ).first()
                    
                    if existing_mapping:
                        duplicate_mapping = Mapping(
                            submission_id=submission_id,
                            marking_guide_id=marking_guide_id,
                            mapping_data=json.dumps(mapping_data),
                            created_at=datetime.now(timezone.utc)
                        )
                        db.session.add(duplicate_mapping)
                        
                        existing_grading = GradingResult.query.filter_by(
                            submission_id=original_id,
                            marking_guide_id=marking_guide_id
                        ).first()
                        
                        if existing_grading:
                            duplicate_grading = GradingResult(
                                submission_id=submission_id,
                                marking_guide_id=marking_guide_id,
                                total_score=grading_data.get('total_score', 0),
                                max_possible_score=grading_data.get('max_possible_score', 100),
                                percentage=grading_data.get('percentage', 0),
                                letter_grade=grading_data.get('letter_grade', 'F'),
                                detailed_feedback=json.dumps(grading_data.get('detailed_grades', [])),
                                summary=json.dumps(grading_data.get('summary', {})),
                                created_at=datetime.now(timezone.utc)
                            )
                            db.session.add(duplicate_grading)
                        
                        celery_logger.info(f"Saved duplicate references for submission {submission_id}")
                        saved_count += 1
                        continue
                
                # Save original mapping
                mapping_obj = Mapping(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id,
                    mapping_data=json.dumps(mapping_data),
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(mapping_obj)
                
                # Save grading result
                grade_obj = GradingResult(
                    submission_id=submission_id,
                    marking_guide_id=marking_guide_id,
                    total_score=grading_data.get('total_score', 0),
                    max_possible_score=grading_data.get('max_possible_score', 100),
                    percentage=grading_data.get('percentage', 0),
                    letter_grade=grading_data.get('letter_grade', 'F'),
                    detailed_feedback=json.dumps(grading_data.get('detailed_grades', [])),
                    summary=json.dumps(grading_data.get('summary', {})),
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(grade_obj)
                
                # Update submission status
                submission = db.session.get(Submission, submission_id)
                if submission:
                    submission.status = 'graded'
                    submission.updated_at = datetime.now(timezone.utc)
                
                results.append({
                    'submission_id': submission_id,
                    'success': True,
                    'score': grading_data.get('total_score', 0),
                    'percentage': grading_data.get('percentage', 0),
                    'letter_grade': grading_data.get('letter_grade', 'F')
                })
                
                saved_count += 1
                
            except Exception as e:
                error_msg = f"Error saving results for submission {submission_id}: {e}"
                celery_logger.error(error_msg)
                progress.add_error(error_msg)
                
                results.append({
                    'submission_id': submission_id,
                    'success': False,
                    'error': str(e)
                })
                continue
        
        # Commit all changes
        db.session.commit()
        
        progress.update_stage("completed", 100, "Pipeline processing completed")
        
        # Calculate summary statistics
        total_processing_time = time.time() - progress.start_time
        successful_results = [r for r in results if r.get('success')]
        average_score = sum(r.get('percentage', 0) for r in successful_results) / len(successful_results) if successful_results else 0
        
        # Get optimization stats
        cache_stats = unified_service.get_cache_stats() if hasattr(unified_service, 'get_cache_stats') else {}
        llm_stats = llm_service.get_grading_stats() if hasattr(llm_service, 'get_grading_stats') else {}
        
        return {
            'success': True,
            'total_submissions': len(submission_ids),
            'successful_count': len(successful_results),
            'failed_count': len(results) - len(successful_results),
            'results': results,
            'summary': {
                'average_percentage': round(average_score, 2),
                'processing_time': round(total_processing_time, 2),
                'guide_type': batch_result.get('guide_type', 'unknown'),
                'errors': progress.errors,
                'warnings': progress.warnings,
                'optimizations_applied': batch_result.get('optimizations_applied', []),
                'duplicates_found': batch_result.get('duplicates_found', 0),
                'unique_contents': batch_result.get('unique_contents', len(submission_data)),
                'cache_stats': cache_stats,
                'llm_stats': llm_stats
            }
        }
        
    except Exception as e:
        error_msg = f"Full pipeline processing failed: {str(e)}"
        celery_logger.error(error_msg)
        progress.add_error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'total_submissions': len(submission_ids),
            'successful_count': 0,
            'failed_count': len(submission_ids)
        }
    
    def _process_fallback_pipeline(self, submission_data, marking_guide, progress):
        """Fallback to original processing if unified service unavailable."""
        progress.update_stage("mapping", 5, "Using fallback processing")
        
        guide_type_result = mapping_service.determine_guide_type(marking_guide.content)
        guide_type = guide_type_result.get('type', 'questions')
        
        results = []
        for i, submission_info in enumerate(submission_data):
            try:
                progress.update_submission(i, f"Processing submission {submission_info['id']}")
                
                # Original mapping
                mapping_result = mapping_service.map_submission_to_guide_optimized(
                    marking_guide.content,
                    submission_info['content'],
                    guide_type
                )
                
                # Original grading
                grading_result = grading_service.grade_submission_optimized(
                    submission_info['content'],
                    marking_guide.content,
                    mapping_result
                )
                
                results.append({
                    'submission_id': submission_info['id'],
                    'mapping': mapping_result,
                    'grading': grading_result
                })
                
            except Exception as e:
                celery_logger.error(f"Fallback processing failed for {submission_info['id']}: {e}")
                continue
        
        return {
            'success': True,
            'results': results,
            'guide_type': guide_type,
            'optimizations_applied': ['fallback_processing'],
            'duplicates_found': 0,
            'unique_contents': len(submission_data)
        }

@celery_app.task(bind=True)
def process_batch_submissions_optimized(self, submission_ids: List[int], marking_guide_id: int, batch_size: int = 5):
    """Process submissions in optimized batches for better resource utilization."""
    
    progress = ProcessingProgress(self.request.id, len(submission_ids))
    
    try:
        progress.update_stage("initializing", 0, "Starting batch processing")
        
        all_results = []
        total_successful = 0
        total_failed = 0
        
        # Process in batches
        for i in range(0, len(submission_ids), batch_size):
            batch = submission_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(submission_ids) + batch_size - 1) // batch_size
            
            progress.update_stage(
                "processing", 
                (i / len(submission_ids)) * 100,
                f"Processing batch {batch_num}/{total_batches}"
            )
            
            # Process batch
            batch_result = process_optimized_full_pipeline.apply(
                args=[batch, marking_guide_id]
            ).get()
            
            if batch_result.get('success'):
                all_results.extend(batch_result.get('results', []))
                total_successful += batch_result.get('successful_count', 0)
                total_failed += batch_result.get('failed_count', 0)
            else:
                total_failed += len(batch)
                progress.add_error(f"Batch {batch_num} failed: {batch_result.get('error')}")
        
        progress.update_stage("completed", 100, "Batch processing completed")
        
        return {
            'success': True,
            'total_submissions': len(submission_ids),
            'successful_count': total_successful,
            'failed_count': total_failed,
            'results': all_results,
            'batches_processed': total_batches
        }
        
    except Exception as e:
        error_msg = f"Batch processing failed: {str(e)}"
        celery_logger.error(error_msg)
        progress.add_error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'total_submissions': len(submission_ids)
        }

# Task monitoring and management
@celery_app.task
def get_task_status(task_id: str):
    """Get detailed status of a processing task."""
    try:
        result = celery_app.AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info,
            'successful': result.successful() if result.ready() else None,
            'failed': result.failed() if result.ready() else None
        }
    except Exception as e:
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'error': str(e)
        }

@celery_app.task
def cleanup_old_tasks(days_old: int = 7):
    """Clean up old task results and cache entries."""
    try:
        # Clean OCR cache
        if hasattr(ocr_service, 'clear_cache'):
            cleared_count = ocr_service.clear_cache()
            logger.info(f"Cleared {cleared_count} old OCR cache entries")
        
        # Additional cleanup logic can be added here
        
        return {
            'success': True,
            'message': f"Cleanup completed for tasks older than {days_old} days"
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }