"""
Background Task Processing Service using Celery.
Handles OCR processing, LLM grading, and other long-running tasks asynchronously.
"""
from typing import Any, Dict, List

import os

from celery import Celery
from flask import current_app

from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService
from src.services.consolidated_llm_service import ConsolidatedLLMService as LLMService
from src.services.consolidated_mapping_service import ConsolidatedMappingService as MappingService
from src.services.consolidated_grading_service import ConsolidatedGradingService as GradingService
from src.database.models import db, Submission, GradingResult, Mapping, MarkingGuide
from utils.logger import logger

# Initialize Celery
celery_app = Celery('exam_grader')

# Configure Celery (using database instead of Redis)
celery_app.conf.update(
    broker_url='sqla+sqlite:///celery_broker.db',
    result_backend='db+sqlite:///celery_results.db',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

class BackgroundTaskService:
    """Service for managing background tasks and job processing."""
    
    def __init__(self):
        """Initialize the background task service."""
        self.ocr_service = None
        self.llm_service = None
        self.mapping_service = None
        self.grading_service = None
    
    def init_services(self):
        """Initialize OCR, LLM, and other services."""
        try:
            self.ocr_service = OCRService()
            self.llm_service = LLMService()
            self.mapping_service = MappingService(llm_service=self.llm_service)
            self.grading_service = GradingService(llm_service=self.llm_service, mapping_service=self.mapping_service)
            logger.info("Background task services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize background services: {str(e)}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a background task."""
        task = celery_app.AsyncResult(task_id)
        return {
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.ready() else None,
            'info': task.info if hasattr(task, 'info') else None,
        }

# Global instance
background_service = BackgroundTaskService()

@celery_app.task(bind=True, name='process_ocr')
def process_ocr_task(self, submission_id: str, file_path: str, user_id: str):
    """
    Background task for OCR processing.
    
    Args:
        submission_id: ID of the submission to process
        file_path: Path to the file to process
        user_id: ID of the user who uploaded the file
    """
    try:
        logger.info(f"Starting OCR processing for submission {submission_id}")
        
        if not background_service.ocr_service:
            background_service.init_services()
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Initializing OCR processing...'}
        )
        
        # Broadcast status update
        realtime_service.broadcast_ocr_status(
            user_id, os.path.basename(file_path), 'starting', 0.0, "Initializing OCR processing..."
        )
        
        # Process OCR
        self.update_state(
            state='PROGRESS',
            meta={'current': 25, 'total': 100, 'status': 'Extracting text from document...'}
        )
        
        realtime_service.broadcast_ocr_status(
            user_id, os.path.basename(file_path), 'processing', 25.0, "Extracting text from document..."
        )
        
        extracted_text = background_service.ocr_service.extract_text_from_image(file_path)
        
        # Update submission with extracted text
        with current_app.app_context():
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.content_text = extracted_text
                submission.processing_status = 'ocr_completed'
                submission.ocr_confidence = 0.8  # Default confidence
                db.session.commit()
                
                logger.info(f"OCR processing completed for submission {submission_id}")
                
                # Broadcast completion
                realtime_service.broadcast_ocr_status(
                    user_id, os.path.basename(file_path), 'completed', 100.0, "OCR processing completed successfully"
                )
                
                return {
                    'status': 'success',
                    'submission_id': submission_id,
                    'extracted_text': extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text,
                    'text_length': len(extracted_text)
                }
            else:
                raise Exception(f"Submission {submission_id} not found")
                
    except Exception as e:
        logger.exception(f"OCR processing failed for submission {submission_id}: {str(e)}")
        
        # Update submission status
        with current_app.app_context():
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.processing_status = 'failed'
                submission.processing_error = str(e)
                db.session.commit()
        
        # Broadcast error
        realtime_service.broadcast_ocr_status(
            user_id, os.path.basename(file_path), 'failed', 0.0, f"OCR processing failed: {str(e)}"
        )
        
        raise Exception({"error": "OCR_FAILED", "message": str(e)})

@celery_app.task(bind=True, name='process_llm_grading')
def process_llm_grading_task(self, submission_id: str, marking_guide_id: str, user_id: str, num_questions: int = None):
    """
    Background task for LLM grading.
    
    Args:
        submission_id: ID of the submission to grade
        marking_guide_id: ID of the marking guide to use
        user_id: ID of the user
        num_questions: Number of questions to grade (optional)
    """
    try:
        logger.info(f"Starting LLM grading for submission {submission_id}")
        
        if not background_service.llm_service:
            background_service.init_services()
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Initializing LLM grading...'}
        )
        
        # Get submission and marking guide
        with current_app.app_context():
            submission = db.session.get(Submission, submission_id)
            marking_guide = db.session.get(MarkingGuide, marking_guide_id)
            
            if not submission:
                raise Exception(f"Submission {submission_id} not found")
            if not marking_guide:
                raise Exception(f"Marking guide {marking_guide_id} not found")
            
            filename = submission.filename
            
            # Broadcast status update
            realtime_service.broadcast_llm_status(
                user_id, filename, 'starting', 0.0, "Initializing LLM grading..."
            )
        
        # Update progress - Mapping phase
        self.update_state(
            state='PROGRESS',
            meta={'current': 25, 'total': 100, 'status': 'Mapping answers to questions...'}
        )
        
        realtime_service.broadcast_llm_status(
            user_id, filename, 'mapping', 25.0, "Mapping answers to questions..."
        )
        
        # Perform mapping and grading
        mapping_result, mapping_error = background_service.mapping_service.map_submission_to_guide(
            marking_guide.content_text,
            submission.content_text,
            num_questions=num_questions or 1
        )
        
        if mapping_error:
            raise Exception(f"Mapping failed: {mapping_error}")
        
        # Update progress - Grading phase
        self.update_state(
            state='PROGRESS',
            meta={'current': 75, 'total': 100, 'status': 'Grading answers...'}
        )
        
        realtime_service.broadcast_llm_status(
            user_id, filename, 'grading', 75.0, "Grading answers..."
        )
        
        # Save results to database
        with current_app.app_context():
            # Create mappings
            mappings = []
            for mapping_data in mapping_result.get('mappings', []):
                mapping = Mapping(
                    submission_id=submission_id,
                    guide_question_id=mapping_data.get('guide_id', ''),
                    guide_question_text=mapping_data.get('guide_text', ''),
                    guide_answer=mapping_data.get('guide_answer', ''),
                    max_score=mapping_data.get('max_score', 0),
                    submission_answer=mapping_data.get('submission_text', ''),
                    match_score=mapping_data.get('match_score', 0),
                    match_reason=mapping_data.get('match_reason', ''),
                    mapping_method='llm'
                )
                db.session.add(mapping)
                mappings.append(mapping)
            
            db.session.commit()
            
            # Create grading results
            overall_grade = mapping_result.get('overall_grade', {})
            grading_result = GradingResult(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id,
                score=overall_grade.get('total_score', 0),
                max_score=overall_grade.get('max_possible_score', 0),
                percentage=overall_grade.get('percentage', 0),
                feedback=overall_grade.get('letter_grade', ''),
                detailed_feedback=mapping_result,
                grading_method='llm'
            )
            db.session.add(grading_result)
            
            # Update submission status
            submission.processing_status = 'completed'
            submission.processed = True
            db.session.commit()
            
            logger.info(f"LLM grading completed for submission {submission_id}")
            
            # Broadcast completion
            realtime_service.broadcast_llm_status(
                user_id, filename, 'completed', 100.0, "LLM grading completed successfully"
            )
            
            # Broadcast grading completion summary
            results_summary = {
                'submission_id': submission_id,
                'filename': filename,
                'score': overall_grade.get('total_score', 0),
                'max_score': overall_grade.get('max_possible_score', 0),
                'percentage': overall_grade.get('percentage', 0),
                'letter_grade': overall_grade.get('letter_grade', 'F'),
                'mappings_count': len(mappings)
            }
            
            realtime_service.broadcast_grading_complete(user_id, results_summary)
            
            return {
                'status': 'success',
                'submission_id': submission_id,
                'grading_result': results_summary,
                'mappings_count': len(mappings)
            }
                
    except Exception as e:
        logger.exception(f"LLM grading failed for submission {submission_id}: {str(e)}")
        
        # Update submission status
        with current_app.app_context():
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.processing_status = 'failed'
                submission.processing_error = str(e)
                db.session.commit()
        
        # Broadcast error
        realtime_service.broadcast_llm_status(
            user_id, filename if 'filename' in locals() else 'Unknown', 'failed', 0.0, f"LLM grading failed: {str(e)}"
        )
        
        raise Exception({"error": "LLM_GRADING_FAILED", "message": str(e)})

@celery_app.task(bind=True, name='process_batch_grading')
def process_batch_grading_task(self, submission_ids: List[str], marking_guide_id: str, user_id: str, num_questions: int = None):
    """
    Background task for batch grading of multiple submissions.
    
    Args:
        submission_ids: List of submission IDs to grade
        marking_guide_id: ID of the marking guide to use
        user_id: ID of the user
        num_questions: Number of questions to grade (optional)
    """
    try:
        logger.info(f"Starting batch grading for {len(submission_ids)} submissions")
        
        if not background_service.llm_service:
            background_service.init_services()
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for i, submission_id in enumerate(submission_ids):
            try:
                # Update progress
                progress = (i / len(submission_ids)) * 100
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1,
                        'total': len(submission_ids),
                        'status': f'Processing submission {i + 1} of {len(submission_ids)}...'
                    }
                )
                
                # Process individual submission
                result = process_llm_grading_task.apply_async(
                    args=[submission_id, marking_guide_id, user_id, num_questions],
                    countdown=0
                )
                
                task_result = result.get(timeout=300)  # 5 minutes timeout
                
                if task_result and task_result.get('status') == 'success':
                    successful_count += 1
                    results.append(task_result)
                else:
                    failed_count += 1
                    results.append({
                        'submission_id': submission_id,
                        'status': 'failed',
                        'error': 'Task failed or timed out'
                    })
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to process submission {submission_id}: {str(e)}")
                results.append({
                    'submission_id': submission_id,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Broadcast batch completion
        batch_summary = {
            'total_submissions': len(submission_ids),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'results': results
        }
        
        realtime_service.broadcast_grading_complete(user_id, batch_summary)
        
        return {
            'status': 'success',
            'batch_summary': batch_summary
        }
        
    except Exception as e:
        logger.exception(f"Batch grading failed: {str(e)}")
        raise Exception({"error": "BATCH_GRADING_FAILED", "message": str(e)})

def init_background_tasks(app):
    """Initialize background task service with Flask app."""
    background_service.init_services()
    return background_service