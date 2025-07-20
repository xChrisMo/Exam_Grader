"""Consolidated API endpoints using unified router structure.

This module provides consolidated endpoints for:
- Marking guides management
- Submissions handling
- AI processing operations
- File operations
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from flask import request, g, current_app, session
from flask_login import current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from src.api.unified_router import unified_api_bp, api_endpoint, APIMiddleware


def calculate_grade_level(percentage: float) -> str:
    """Calculate grade level from percentage."""
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
from src.models.api_responses import APIResponse, PaginatedResponse, ErrorResponse
from src.models.validation import ValidationResult, CommonValidators
from src.utils.response_utils import extract_pagination_params
from src.database.models import (
    db, MarkingGuide, Submission, GradingResult, 
    GradingSession, User, Mapping
)
from src.services.unified_ai_service import UnifiedAIService
from src.services.enhanced_upload_service import EnhancedUploadService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from src.services.enhanced_processing_service import EnhancedProcessingService
from src.services.consolidated_llm_service import ConsolidatedLLMService
from utils.logger import logger
from utils.input_sanitizer import sanitize_form_data, validate_file_upload

# Initialize services
ai_service = None
upload_service = None
ocr_service = None
enhanced_processing_service = None


def init_consolidated_services(app):
    """Initialize consolidated API services.
    
    Args:
        app: Flask application instance
    """
    global ai_service, upload_service, ocr_service, enhanced_processing_service
    
    with app.app_context():
        try:
            # Initialize OCR service
            ocr_service = ConsolidatedOCRService()
            
            # Initialize AI service
            ai_service = UnifiedAIService()
            
            # Initialize upload service
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            upload_service = EnhancedUploadService(upload_folder, ocr_service)
            
            # Initialize enhanced processing service
            llm_service = ConsolidatedLLMService()
            enhanced_processing_service = EnhancedProcessingService(llm_service, ocr_service)
            
            logger.info("Consolidated API services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize consolidated API services: {str(e)}")
            raise


# Marking Guides Endpoints
@unified_api_bp.route('/guides', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def get_marking_guides():
    """Get all marking guides for the current user.
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        search (str): Search term for guide names
        status (str): Filter by status (active, archived)
    
    Returns:
        PaginatedResponse with marking guides
    """
    try:
        # Extract pagination parameters
        page, per_page = extract_pagination_params(request)
        
        # Build query
        query = MarkingGuide.query.filter_by(user_id=current_user.id)
        
        # Apply search filter
        search = request.args.get('search', '').strip()
        if search:
            query = query.filter(
                MarkingGuide.name.ilike(f'%{search}%')
            )
        
        # Apply status filter
        status = request.args.get('status', '').strip()
        if status in ['active', 'archived']:
            is_active = status == 'active'
            query = query.filter(MarkingGuide.is_active == is_active)
        
        # Order by creation date (newest first)
        query = query.order_by(MarkingGuide.created_at.desc())
        
        # Paginate results
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format guides data
        guides_data = []
        for guide in pagination.items:
            # Count submissions using this guide
            submission_count = Submission.query.filter_by(
                marking_guide_id=guide.id
            ).count()
            
            guides_data.append({
                'id': guide.id,
                'name': guide.name,
                'subject': guide.subject,
                'total_marks': guide.total_marks,
                'is_active': guide.is_active,
                'created_at': guide.created_at.isoformat(),
                'updated_at': guide.updated_at.isoformat() if guide.updated_at else None,
                'submission_count': submission_count,
                'file_path': guide.file_path,
                'content_preview': guide.content[:200] + '...' if guide.content and len(guide.content) > 200 else guide.content
            })
        
        return PaginatedResponse.create(
            data=guides_data,
            page=pagination.page,
            per_page=pagination.per_page,
            total=pagination.total,
            pages=pagination.pages
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error fetching marking guides: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to fetch marking guides"
        ).to_dict(), 500


@unified_api_bp.route('/guides/<string:guide_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 200, 'window_seconds': 3600}
)
def get_marking_guide(guide_id: str):
    """Get a specific marking guide by ID.
    
    Args:
        guide_id: Marking guide ID
    
    Returns:
        APIResponse with guide details
    """
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Get submission statistics
        submission_stats = db.session.query(
            func.count(Submission.id).label('total'),
            func.count(Submission.id).filter(
                Submission.processing_status == 'completed'
            ).label('completed'),
            func.count(Submission.id).filter(
                Submission.processing_status == 'processing'
            ).label('processing'),
            func.count(Submission.id).filter(
                Submission.processing_status == 'failed'
            ).label('failed')
        ).filter(
            Submission.marking_guide_id == guide_id
        ).first()
        
        guide_data = {
            'id': guide.id,
            'name': guide.name,
            'subject': guide.subject,
            'total_marks': guide.total_marks,
            'is_active': guide.is_active,
            'created_at': guide.created_at.isoformat(),
            'updated_at': guide.updated_at.isoformat() if guide.updated_at else None,
            'file_path': guide.file_path,
            'content': guide.content,
            'statistics': {
                'total_submissions': submission_stats.total or 0,
                'completed_submissions': submission_stats.completed or 0,
                'processing_submissions': submission_stats.processing or 0,
                'failed_submissions': submission_stats.failed or 0
            }
        }
        
        return APIResponse.success(
            data=guide_data,
            message="Marking guide retrieved successfully"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error fetching marking guide {guide_id}: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to fetch marking guide"
        ).to_dict(), 500


@unified_api_bp.route('/guides', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 20, 'window_seconds': 3600},
    validate_json_fields=['name', 'subject']
)
def create_marking_guide():
    """Create a new marking guide.
    
    Request Body:
        name (str): Guide name (required)
        subject (str): Subject name (required)
        total_marks (int): Total marks (optional)
        content (str): Guide content (optional)
    
    Returns:
        APIResponse with created guide
    """
    try:
        data = g.validated_data
        
        # Additional validation
        validation_result = ValidationResult()
        
        # Validate name
        if not CommonValidators.min_length(data.get('name', ''), 3):
            validation_result.add_error('name', 'Name must be at least 3 characters long')
        
        if not CommonValidators.max_length(data.get('name', ''), 100):
            validation_result.add_error('name', 'Name must be less than 100 characters')
        
        # Validate subject
        if not CommonValidators.min_length(data.get('subject', ''), 2):
            validation_result.add_error('subject', 'Subject must be at least 2 characters long')
        
        # Validate total_marks if provided
        total_marks = data.get('total_marks')
        if total_marks is not None:
            if not isinstance(total_marks, int) or total_marks <= 0:
                validation_result.add_error('total_marks', 'Total marks must be a positive integer')
        
        if not validation_result.is_valid:
            return ErrorResponse.validation_error(
                message="Validation failed",
                details=[{
                    "field": error.field,
                    "message": error.message
                } for error in validation_result.errors]
            ).to_dict(), 400
        
        # Check for duplicate name
        existing_guide = MarkingGuide.query.filter_by(
            user_id=current_user.id,
            name=data['name']
        ).first()
        
        if existing_guide:
            return ErrorResponse.validation_error(
                message="A marking guide with this name already exists",
                details=[{"field": "name", "message": "Name must be unique"}]
            ).to_dict(), 400
        
        # Create new marking guide
        guide = MarkingGuide(
            name=data['name'],
            subject=data['subject'],
            total_marks=total_marks or 100,
            content=data.get('content', ''),
            user_id=current_user.id,
            is_active=True
        )
        
        db.session.add(guide)
        db.session.commit()
        
        guide_data = {
            'id': guide.id,
            'name': guide.name,
            'subject': guide.subject,
            'total_marks': guide.total_marks,
            'is_active': guide.is_active,
            'created_at': guide.created_at.isoformat(),
            'content': guide.content
        }
        
        return APIResponse.success(
            data=guide_data,
            message="Marking guide created successfully"
        ).to_dict(), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating marking guide: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to create marking guide"
        ).to_dict(), 500


# Submissions Endpoints
@unified_api_bp.route('/submissions', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def get_submissions():
    """Get submissions for the current user.
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        guide_id (int): Filter by marking guide ID
        status (str): Filter by processing status
        search (str): Search term for student names
    
    Returns:
        PaginatedResponse with submissions
    """
    try:
        # Extract pagination parameters
        page, per_page = extract_pagination_params(request)
        
        # Build query - get submissions for user's guides
        query = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            MarkingGuide.user_id == current_user.id
        )
        
        # Apply guide filter
        guide_id = request.args.get('guide_id', type=int)
        if guide_id:
            query = query.filter(Submission.marking_guide_id == guide_id)
        
        # Apply status filter
        status = request.args.get('status', '').strip()
        if status:
            query = query.filter(Submission.processing_status == status)
        
        # Apply search filter
        search = request.args.get('search', '').strip()
        if search:
            query = query.filter(
                Submission.student_name.ilike(f'%{search}%')
            )
        
        # Order by creation date (newest first)
        query = query.order_by(Submission.created_at.desc())
        
        # Paginate results
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format submissions data
        submissions_data = []
        for submission in pagination.items:
            # Get latest grading result
            latest_result = GradingResult.query.filter_by(
                submission_id=submission.id
            ).order_by(GradingResult.created_at.desc()).first()
            
            submissions_data.append({
                'id': submission.id,
                'student_name': submission.student_name,
                'student_id': submission.student_id,
                'processing_status': submission.processing_status,
                'created_at': submission.created_at.isoformat(),
                'updated_at': submission.updated_at.isoformat() if submission.updated_at else None,
                'file_path': submission.file_path,
                'marking_guide': {
                    'id': submission.marking_guide.id,
                    'name': submission.marking_guide.name,
                    'subject': submission.marking_guide.subject
                },
                'latest_result': {
                    'total_score': latest_result.total_score,
                    'letter_grade': latest_result.letter_grade,
                    'created_at': latest_result.created_at.isoformat()
                } if latest_result else None
            })
        
        return PaginatedResponse.create(
            data=submissions_data,
            page=pagination.page,
            per_page=pagination.per_page,
            total=pagination.total,
            pages=pagination.pages
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error fetching submissions: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to fetch submissions"
        ).to_dict(), 500


# Processing Endpoints
@unified_api_bp.route('/processing/batch', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 10, 'window_seconds': 3600},
    validate_json_fields=['guide_id', 'submission_ids']
)
def process_batch():
    """Process a batch of submissions.
    
    Request Body:
        guide_id (int): Marking guide ID (required)
        submission_ids (list): List of submission IDs (required)
        options (dict): Processing options (optional)
    
    Returns:
        APIResponse with processing task information
    """
    try:
        data = g.validated_data
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=data['guide_id'],
            user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Validate submissions
        submission_ids = data['submission_ids']
        if not isinstance(submission_ids, list) or not submission_ids:
            return ErrorResponse.validation_error(
                message="submission_ids must be a non-empty list"
            ).to_dict(), 400
        
        # Check submission ownership through guide
        submissions = Submission.query.filter(
            Submission.id.in_(submission_ids),
            Submission.marking_guide_id == data['guide_id']
        ).all()
        
        if len(submissions) != len(submission_ids):
            return ErrorResponse.validation_error(
                message="Some submissions not found or not accessible"
            ).to_dict(), 400
        
        # Start processing
        if ai_service:
            try:
                # Use the unified AI service for batch processing
                processing_options = data.get('options', {})
                
                # Create a processing session
                session_data = {
                    'guide_id': data['guide_id'],
                    'submission_ids': submission_ids,
                    'user_id': current_user.id,
                    'options': processing_options
                }
                
                # Start async processing (this would typically use Celery)
                task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_user.id}"
                
                # For now, return a mock response
                # In production, this would start a background task
                return APIResponse.success(
                    data={
                        'task_id': task_id,
                        'status': 'started',
                        'guide_id': data['guide_id'],
                        'submission_count': len(submission_ids),
                        'estimated_completion': '5-10 minutes'
                    },
                    message="Batch processing started successfully"
                ).to_dict(), 202
                
            except Exception as e:
                logger.error(f"Error starting batch processing: {str(e)}")
                return ErrorResponse.processing_error(
                    message="Failed to start batch processing"
                ).to_dict(), 500
        else:
            return ErrorResponse.service_unavailable(
                message="AI processing service is not available"
            ).to_dict(), 503
        
    except Exception as e:
        logger.error(f"Error in batch processing endpoint: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to process batch request"
        ).to_dict(), 500


@unified_api_bp.route('/processing/status/<task_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 200, 'window_seconds': 3600}
)
def get_processing_status(task_id: str):
    """Get processing status for a task.
    
    Args:
        task_id: Processing task ID
    
    Returns:
        APIResponse with task status
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return ErrorResponse.authentication_error().to_dict(), 401
        
        # Validate task_id format
        if not task_id or len(task_id) < 10:
            return ErrorResponse.validation_error(
                message="Invalid task ID"
            ).to_dict(), 400
        
        # Check if task_id corresponds to a submission or grading session
        submission = db.session.query(Submission).filter(
            Submission.id == task_id,
            Submission.user_id == user_id
        ).first()
        
        if submission:
            # Get submission processing status
            total_steps = 4  # OCR, Mapping, Grading, Completion
            current_step = 0
            
            if submission.content_text:
                current_step += 1  # OCR completed
            
            mappings_count = db.session.query(Mapping).filter(
                Mapping.submission_id == task_id
            ).count()
            if mappings_count > 0:
                current_step += 1  # Mapping completed
            
            results_count = db.session.query(GradingResult).filter(
                GradingResult.submission_id == task_id
            ).count()
            if results_count > 0:
                current_step += 1  # Grading completed
            
            if submission.processed:
                current_step = total_steps  # All completed
            
            percentage = int((current_step / total_steps) * 100)
            
            # Determine status
            if submission.processing_status == 'failed':
                status = 'failed'
            elif submission.processing_status == 'completed' or submission.processed:
                status = 'completed'
            elif submission.processing_status == 'processing':
                status = 'processing'
            else:
                status = 'pending'
            
            status_data = {
                'task_id': task_id,
                'status': status,
                'progress': {
                    'current': current_step,
                    'total': total_steps,
                    'percentage': percentage
                },
                'started_at': submission.created_at.isoformat(),
                'updated_at': submission.updated_at.isoformat() if submission.updated_at else None,
                'submission_info': {
                    'student_name': submission.student_name,
                    'filename': submission.filename,
                    'file_size': submission.file_size
                },
                'results': {
                    'mappings_created': mappings_count,
                    'grading_results': results_count,
                    'ocr_completed': bool(submission.content_text),
                    'processing_error': submission.processing_error
                }
            }
            
            return APIResponse.success(
                data=status_data,
                message="Processing status retrieved successfully"
            ).to_dict()
        
        # Check grading sessions
        grading_session = db.session.query(GradingSession).filter(
            GradingSession.id == task_id
        ).first()
        
        if grading_session:
            # Verify user owns the submission
            submission = db.session.query(Submission).filter(
                Submission.id == grading_session.submission_id,
                Submission.user_id == user_id
            ).first()
            
            if not submission:
                return ErrorResponse.not_found(
                    message="Task not found or access denied"
                ).to_dict(), 404
            
            status_data = {
                'task_id': task_id,
                'status': grading_session.status,
                'progress': {
                    'current': grading_session.current_step or 0,
                    'total': grading_session.total_questions_mapped or 1,
                    'percentage': int(((grading_session.current_step or 0) / (grading_session.total_questions_mapped or 1)) * 100)
                },
                'started_at': grading_session.created_at.isoformat(),
                'updated_at': grading_session.updated_at.isoformat() if grading_session.updated_at else None,
                'session_info': {
                    'submission_id': grading_session.submission_id,
                    'marking_guide_id': grading_session.marking_guide_id,
                    'total_questions': grading_session.total_questions_mapped
                },
                'results': {
                    'questions_graded': grading_session.current_step or 0,
                    'error_message': grading_session.error_message
                }
            }
            
            return APIResponse.success(
                data=status_data,
                message="Processing status retrieved successfully"
            ).to_dict()
        
        # Task not found
        return ErrorResponse.not_found(
            message="Task not found or access denied"
        ).to_dict(), 404
        
    except Exception as e:
        logger.error(f"Error fetching processing status for {task_id}: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to fetch processing status"
        ).to_dict(), 500


# Enhanced Processing Endpoints

@unified_api_bp.route('/processing/guide', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 20, 'window_seconds': 3600},
    validate_json_fields=['guide_id']
)
def process_marking_guide():
    """Process marking guide using LLM to extract structured content.
    
    Request Body:
        guide_id (int): Marking guide ID (required)
    
    Returns:
        APIResponse with processing result
    """
    try:
        data = g.validated_data
        guide_id = data['guide_id']
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Check if guide has content to process
        if not guide.content:
            return ErrorResponse.validation_error(
                message="No content available for processing",
                details=[{
                    "field": "content",
                    "message": "Marking guide must have content to process"
                }]
            ).to_dict(), 400
        
        # Process the marking guide
        if enhanced_processing_service:
            result, error = enhanced_processing_service.process_marking_guide(
                guide_id=guide_id,
                file_path=guide.file_path or '',
                raw_content=guide.content
            )
            
            if error:
                return ErrorResponse.processing_error(
                    message=f"Failed to process marking guide: {error}"
                ).to_dict(), 500
            
            return APIResponse.success(
                data={
                    'guide_id': guide_id,
                    'structured_content': result,
                    'questions_extracted': len(result.get('questions', [])),
                    'total_marks': result.get('total_marks', 0)
                },
                message="Marking guide processed successfully"
            ).to_dict()
        else:
            return ErrorResponse.service_unavailable(
                message="Processing service is not available"
            ).to_dict(), 503
        
    except Exception as e:
        logger.error(f"Error processing marking guide: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to process marking guide"
        ).to_dict(), 500


@unified_api_bp.route('/processing/submission', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 50, 'window_seconds': 3600},
    validate_json_fields=['submission_id', 'marking_guide_id']
)
def process_submission():
    """Process student submission using OCR and LLM mapping.
    
    Request Body:
        submission_id (int): Submission ID (required)
        marking_guide_id (int): Marking guide ID (required)
    
    Returns:
        APIResponse with processing result
    """
    try:
        data = g.validated_data
        submission_id = data['submission_id']
        marking_guide_id = data['marking_guide_id']
        
        # Validate submission ownership through guide
        submission = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id == submission_id,
            MarkingGuide.user_id == current_user.id
        ).first()
        
        if not submission:
            return ErrorResponse.not_found(
                message="Submission not found"
            ).to_dict(), 404
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=marking_guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Process the submission
        if enhanced_processing_service:
            result, error = enhanced_processing_service.process_submission(
                submission_id=submission_id,
                file_path=submission.file_path or '',
                marking_guide_id=marking_guide_id
            )
            
            if error:
                return ErrorResponse.processing_error(
                    message=f"Failed to process submission: {error}"
                ).to_dict(), 500
            
            return APIResponse.success(
                data={
                    'submission_id': submission_id,
                    'mapping_result': result,
                    'answers_mapped': len(result.get('mappings', [])),
                    'processing_status': 'completed'
                },
                message="Submission processed successfully"
            ).to_dict()
        else:
            return ErrorResponse.service_unavailable(
                message="Processing service is not available"
            ).to_dict(), 503
        
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to process submission"
        ).to_dict(), 500


@unified_api_bp.route('/processing/grading', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 30, 'window_seconds': 3600},
    validate_json_fields=['submission_id', 'marking_guide_id']
)
def process_grading():
    """Process grading with max_questions_to_answer logic.
    
    Request Body:
        submission_id (int): Submission ID (required)
        marking_guide_id (int): Marking guide ID (required)
        max_questions_to_answer (int): Maximum questions to grade (optional)
    
    Returns:
        APIResponse with grading result
    """
    try:
        data = g.validated_data
        submission_id = data['submission_id']
        marking_guide_id = data['marking_guide_id']
        max_questions_to_answer = data.get('max_questions_to_answer')
        
        # Validate submission ownership through guide
        submission = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id == submission_id,
            MarkingGuide.user_id == current_user.id
        ).first()
        
        if not submission:
            return ErrorResponse.not_found(
                message="Submission not found"
            ).to_dict(), 404
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=marking_guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Process grading
        if enhanced_processing_service:
            result, error = enhanced_processing_service.process_grading(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id,
                max_questions_to_answer=max_questions_to_answer
            )
            
            if error:
                return ErrorResponse.processing_error(
                    message=f"Failed to process grading: {error}"
                ).to_dict(), 500
            
            return APIResponse.success(
                data={
                    'submission_id': submission_id,
                    'grading_result': result,
                    'total_score': result.get('total_score', 0),
                            'max_possible_score': result.get('max_possible_score', 0),
                    'percentage': result.get('percentage', 0),
                    'grade_level': calculate_grade_level(result.get('percentage', 0)),
                    'questions_graded': result.get('selected_questions', 0)
                },
                message="Grading completed successfully"
            ).to_dict()
        else:
            return ErrorResponse.service_unavailable(
                message="Grading service is not available"
            ).to_dict(), 503
        
    except Exception as e:
        logger.error(f"Error processing grading: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to process grading"
        ).to_dict(), 500


@unified_api_bp.route('/processing/batch-enhanced', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 5, 'window_seconds': 3600},
    validate_json_fields=['submission_ids', 'marking_guide_id']
)
def process_batch_enhanced():
    """Process multiple submissions with the complete enhanced pipeline.
    
    Request Body:
        submission_ids (list): List of submission IDs (required)
        marking_guide_id (int): Marking guide ID (required)
        max_questions_to_answer (int): Maximum questions to grade (optional)
        process_steps (list): Steps to execute ['guide', 'submissions', 'grading'] (optional)
    
    Returns:
        APIResponse with batch processing result
    """
    try:
        data = g.validated_data
        submission_ids = data['submission_ids']
        marking_guide_id = data['marking_guide_id']
        max_questions_to_answer = data.get('max_questions_to_answer')
        process_steps = data.get('process_steps', ['grading'])  # Default to grading only
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=marking_guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found"
            ).to_dict(), 404
        
        # Validate submissions ownership
        submissions = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id.in_(submission_ids),
            MarkingGuide.user_id == current_user.id
        ).all()
        
        if len(submissions) != len(submission_ids):
            return ErrorResponse.validation_error(
                message="Some submissions not found or access denied",
                details=[{
                    "field": "submission_ids",
                    "message": "All submissions must exist and belong to the user"
                }]
            ).to_dict(), 400
        
        # Initialize enhanced processing service if not available
        current_enhanced_service = enhanced_processing_service
        if not current_enhanced_service:
            try:
                from src.services.enhanced_processing_service import EnhancedProcessingService
                from src.services.consolidated_llm_service import ConsolidatedLLMService
                from src.services.consolidated_ocr_service import ConsolidatedOCRService
                
                llm_service = ConsolidatedLLMService()
                ocr_service = ConsolidatedOCRService()
                current_enhanced_service = EnhancedProcessingService(llm_service, ocr_service)
                logger.info("Enhanced processing service initialized for batch processing")
            except Exception as e:
                logger.error(f"Failed to initialize enhanced processing service: {str(e)}")
                return ErrorResponse.service_unavailable(
                    message="Enhanced processing service could not be initialized"
                ).to_dict(), 503
        
        # Initialize results
        batch_results = {
            'guide_processing': None,
            'submission_processing': {},
            'grading_results': {},
            'summary': {
                'total_submissions': len(submission_ids),
                'successful_processing': 0,
                'successful_grading': 0,
                'failed_processing': 0,
                'failed_grading': 0
            }
        }
        
        # Step 1: Process marking guide if requested
        if 'guide' in process_steps:
            try:
                guide_result, guide_error = current_enhanced_service.process_marking_guide(
                    guide_id=marking_guide_id,
                    file_path=guide.file_path or '',
                    raw_content=guide.content_text or guide.content or ''
                )
                
                if guide_error:
                    batch_results['guide_processing'] = {
                        'success': False,
                        'error': guide_error
                    }
                else:
                    batch_results['guide_processing'] = {
                        'success': True,
                        'questions_extracted': len(guide_result.get('questions', [])),
                        'total_marks': guide_result.get('total_marks', 0)
                    }
            except Exception as e:
                logger.error(f"Error processing guide in batch: {str(e)}")
                batch_results['guide_processing'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Step 2: Process submissions if requested
        if 'submissions' in process_steps:
            for submission_id in submission_ids:
                try:
                    submission = next(s for s in submissions if s.id == submission_id)
                    result, submission_error = current_enhanced_service.process_submission(
                        submission_id=submission_id,
                        file_path=submission.file_path or '',
                        marking_guide_id=marking_guide_id
                    )
                    
                    if submission_error:
                        batch_results['submission_processing'][submission_id] = {
                            'success': False,
                            'error': submission_error
                        }
                        batch_results['summary']['failed_processing'] += 1
                    else:
                        batch_results['submission_processing'][submission_id] = {
                            'success': True,
                            'answers_mapped': len(result.get('mappings', []))
                        }
                        batch_results['summary']['successful_processing'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing submission {submission_id}: {str(e)}")
                    batch_results['submission_processing'][submission_id] = {
                        'success': False,
                        'error': str(e)
                    }
                    batch_results['summary']['failed_processing'] += 1
        
        # Step 3: Process grading if requested (this is the main step we want)
        if 'grading' in process_steps:
            for submission_id in submission_ids:
                try:
                    result, grading_error = current_enhanced_service.process_grading(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        max_questions_to_answer=max_questions_to_answer
                    )
                    
                    if grading_error:
                        batch_results['grading_results'][submission_id] = {
                            'success': False,
                            'error': grading_error
                        }
                        batch_results['summary']['failed_grading'] += 1
                    else:
                        batch_results['grading_results'][submission_id] = {
                            'success': True,
                            'total_score': result.get('total_score', 0),
                            'max_possible_score': result.get('max_possible_score', 0),
                            'percentage': result.get('percentage', 0),
                            'grade_level': calculate_grade_level(result.get('percentage', 0)),
                            'questions_graded': result.get('selected_questions', 0)
                        }
                        batch_results['summary']['successful_grading'] += 1
                    
                except Exception as e:
                    logger.error(f"Error grading submission {submission_id}: {str(e)}")
                    batch_results['grading_results'][submission_id] = {
                        'success': False,
                        'error': str(e)
                    }
                    batch_results['summary']['failed_grading'] += 1
        
        return APIResponse.success(
            data=batch_results,
            message="Enhanced batch processing completed"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error in enhanced batch processing: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to process enhanced batch request"
        ).to_dict(), 500
@unified_api_bp.route('/processing/status/<int:submission_id>/<int:marking_guide_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 200, 'window_seconds': 3600}
)
def get_enhanced_processing_status(submission_id: int, marking_guide_id: int):
    """Get current processing status for a submission.
    
    Args:
        submission_id: Submission ID
        marking_guide_id: Marking guide ID
    
    Returns:
        APIResponse with processing status
    """
    try:
        # Validate submission ownership through guide
        submission = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id == submission_id,
            MarkingGuide.user_id == current_user.id
        ).first()
        
        if not submission:
            return ErrorResponse.not_found(
                message="Submission not found"
            ).to_dict(), 404
        
        # Get processing status
        if enhanced_processing_service:
            status_info = enhanced_processing_service.get_processing_status(
                submission_id=submission_id,
                marking_guide_id=marking_guide_id
            )
            
            return APIResponse.success(
                data=status_info,
                message="Processing status retrieved successfully"
            ).to_dict()
        else:
            return ErrorResponse.service_unavailable(
                message="Processing service is not available"
            ).to_dict(), 503
        
    except Exception as e:
        logger.error(f"Error getting enhanced processing status: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to get processing status"
         ).to_dict(), 500


# File Management Endpoints

@unified_api_bp.route('/files/upload', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True
)
def upload_file():
    """Generic file upload endpoint that routes to appropriate handler."""
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Get upload type
        upload_type = request.form.get('type', 'submission')  # Default to submission
        
        if upload_type == 'submission':
            # Route to submission upload
            return upload_submission_file()
        elif upload_type == 'guide':
            # Route to guide upload
            return upload_marking_guide_file()
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid upload type: {upload_type}',
                'code': 'INVALID_TYPE'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in generic upload endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@unified_api_bp.route('/files/upload/submission', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 50, 'window_seconds': 3600}
)
def upload_submission_file():
    """Upload a submission file with validation and duplicate detection.
    
    Form Data:
        file: The uploaded file (required)
        marking_guide_id: ID of the marking guide (required)
        student_name: Name of the student (required)
        student_id: Student ID (required)
        check_duplicates: Whether to check for duplicates (optional, default: true)
    
    Returns:
        APIResponse with upload result
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return ErrorResponse.validation_error(
                message="No file provided",
                details=[{
                    "field": "file",
                    "message": "File is required"
                }]
            ).to_dict(), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return ErrorResponse.validation_error(
                message="No file selected",
                details=[{
                    "field": "file",
                    "message": "Valid file must be selected"
                }]
            ).to_dict(), 400
        
        # Get form data
        marking_guide_id = request.form.get('marking_guide_id')
        student_name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        check_duplicates = request.form.get('check_duplicates', 'true').lower() == 'true'
        
        # Validate required fields
        validation_errors = []
        if not marking_guide_id:
            validation_errors.append({
                "field": "marking_guide_id",
                "message": "Marking guide ID is required"
            })
        if not student_name:
            validation_errors.append({
                "field": "student_name",
                "message": "Student name is required"
            })
        if not student_id:
            validation_errors.append({
                "field": "student_id",
                "message": "Student ID is required"
            })
        
        if validation_errors:
            return ErrorResponse.validation_error(
                message="Missing required fields",
                details=validation_errors
            ).to_dict(), 400
        
        # Verify marking guide exists and belongs to user
        marking_guide = MarkingGuide.query.filter_by(
            id=marking_guide_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not marking_guide:
            return ErrorResponse.not_found(
                message="Marking guide not found or access denied"
            ).to_dict(), 404
        
        # Upload submission
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        result = upload_service.upload_submission(
            file=file,
            user_id=str(current_user.id),
            marking_guide_id=marking_guide_id,
            student_name=student_name,
            student_id=student_id,
            check_duplicates=check_duplicates
        )
        
        # Handle response based on result
        if result['success']:
            return APIResponse.success(
                data={
                    'submission_id': result.get('submission_id'),
                    'filename': result.get('filename'),
                    'file_size': result.get('file_size'),
                    'student_name': student_name,
                    'student_id': student_id,
                    'duplicate_check_performed': check_duplicates
                },
                message=result.get('message', 'Submission uploaded successfully')
            ).to_dict(), 201
        elif result.get('code') == 'DUPLICATE_CONTENT':
            return ErrorResponse.validation_error(
                message=result.get('error', 'Duplicate content detected'),
                details=[{
                    "field": "file",
                    "message": result.get('error', 'This file appears to be a duplicate'),
                    "code": "DUPLICATE_CONTENT"
                }]
            ).to_dict(), 409
        else:
            return ErrorResponse.processing_error(
                message=result.get('error', 'Upload failed')
            ).to_dict(), 500
        
    except Exception as e:
        logger.error(f"Error uploading submission: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to upload submission"
        ).to_dict(), 500


@unified_api_bp.route('/files/upload/guide', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 20, 'window_seconds': 3600}
)
def upload_marking_guide_file():
    """Upload a marking guide file with validation and duplicate detection.
    
    Form Data:
        file: The uploaded file (required)
        title: Title for the marking guide (required)
        check_duplicates: Whether to check for duplicates (optional, default: true)
    
    Returns:
        APIResponse with upload result
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return ErrorResponse.validation_error(
                message="No file provided",
                details=[{
                    "field": "file",
                    "message": "File is required"
                }]
            ).to_dict(), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return ErrorResponse.validation_error(
                message="No file selected",
                details=[{
                    "field": "file",
                    "message": "Valid file must be selected"
                }]
            ).to_dict(), 400
        
        # Get form data
        title = request.form.get('title', '').strip()
        check_duplicates = request.form.get('check_duplicates', 'true').lower() == 'true'
        
        # Validate required fields
        if not title:
            return ErrorResponse.validation_error(
                message="Title is required",
                details=[{
                    "field": "title",
                    "message": "Title is required for marking guide"
                }]
            ).to_dict(), 400
        
        # Upload marking guide
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        result = upload_service.upload_marking_guide(
            file=file,
            user_id=str(current_user.id),
            title=title,
            check_duplicates=check_duplicates
        )
        
        # Handle response based on result
        if result['success']:
            return APIResponse.success(
                data={
                    'guide_id': result.get('guide_id'),
                    'filename': result.get('filename'),
                    'file_size': result.get('file_size'),
                    'title': title,
                    'duplicate_check_performed': check_duplicates
                },
                message=result.get('message', 'Marking guide uploaded successfully')
            ).to_dict(), 201
        elif result.get('code') == 'DUPLICATE_CONTENT':
            return ErrorResponse.validation_error(
                message=result.get('error', 'Duplicate content detected'),
                details=[{
                    "field": "file",
                    "message": result.get('error', 'This file appears to be a duplicate'),
                    "code": "DUPLICATE_CONTENT"
                }]
            ).to_dict(), 409
        else:
            return ErrorResponse.processing_error(
                message=result.get('error', 'Upload failed')
            ).to_dict(), 500
        
    except Exception as e:
        logger.error(f"Error uploading marking guide: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to upload marking guide"
        ).to_dict(), 500


@unified_api_bp.route('/files/validate', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def validate_file():
    """Validate uploaded file without saving or checking duplicates.
    
    Form Data:
        file: The file to validate (required)
    
    Returns:
        APIResponse with validation result
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return ErrorResponse.validation_error(
                message="No file provided",
                details=[{
                    "field": "file",
                    "message": "File is required for validation"
                }]
            ).to_dict(), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return ErrorResponse.validation_error(
                message="No file selected",
                details=[{
                    "field": "file",
                    "message": "Valid file must be selected"
                }]
            ).to_dict(), 400
        
        # Validate file
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        result = upload_service.validate_file_upload(file)
        
        if result['valid']:
            return APIResponse.success(
                data={
                    'filename': result.get('filename'),
                    'file_size': result.get('file_size'),
                    'file_type': result.get('file_type'),
                    'validation_details': result.get('details', {})
                },
                message="File validation successful"
            ).to_dict()
        else:
            return ErrorResponse.validation_error(
                message="File validation failed",
                details=[{
                    "field": "file",
                    "message": result.get('error', 'File is not valid'),
                    "code": result.get('code', 'INVALID_FILE')
                }]
            ).to_dict(), 400
        
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to validate file"
        ).to_dict(), 500


@unified_api_bp.route('/files/check-duplicate', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 50, 'window_seconds': 3600}
)
def check_file_duplicate():
    """Check if uploaded content would be a duplicate without saving.
    
    Form Data:
        file: The file to check (required)
        file_type: Type of file ('submission' or 'guide') (required)
        marking_guide_id: Required for submission type (optional)
    
    Returns:
        APIResponse with duplicate check result
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return ErrorResponse.validation_error(
                message="No file provided",
                details=[{
                    "field": "file",
                    "message": "File is required for duplicate check"
                }]
            ).to_dict(), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return ErrorResponse.validation_error(
                message="No file selected",
                details=[{
                    "field": "file",
                    "message": "Valid file must be selected"
                }]
            ).to_dict(), 400
        
        file_type = request.form.get('file_type', '').strip().lower()
        marking_guide_id = request.form.get('marking_guide_id')
        
        # Validate file type
        if file_type not in ['submission', 'guide']:
            return ErrorResponse.validation_error(
                message="Invalid file type",
                details=[{
                    "field": "file_type",
                    "message": "File type must be 'submission' or 'guide'"
                }]
            ).to_dict(), 400
        
        # Validate marking guide ID for submissions
        if file_type == 'submission' and not marking_guide_id:
            return ErrorResponse.validation_error(
                message="Marking guide ID required for submissions",
                details=[{
                    "field": "marking_guide_id",
                    "message": "Marking guide ID is required when checking submission duplicates"
                }]
            ).to_dict(), 400
        
        # Perform duplicate check
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        # First validate the file
        validation_result = upload_service.validate_file_upload(file)
        if not validation_result['valid']:
            return ErrorResponse.validation_error(
                message="File validation failed",
                details=[{
                    "field": "file",
                    "message": validation_result.get('error', 'File is not valid'),
                    "code": validation_result.get('code', 'INVALID_FILE')
                }]
            ).to_dict(), 400
        
        # Check for duplicates
        result = upload_service.content_validator.validate_and_check_duplicates(
            file_path=file.filename,
            file_type=file_type,
            user_id=str(current_user.id),
            check_type=file_type,
            marking_guide_id=marking_guide_id
        )
        
        return APIResponse.success(
            data={
                'is_duplicate': result.get('is_duplicate', False),
                'duplicate_details': result.get('duplicate_info', {}),
                'filename': validation_result.get('filename'),
                'file_size': validation_result.get('file_size')
            },
            message="Duplicate check completed"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error checking file duplicate: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to check file duplicate"
        ).to_dict(), 500


@unified_api_bp.route('/files/supported-formats', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=False,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def get_supported_file_formats():
    """Get list of supported file formats and upload limits.
    
    Returns:
        APIResponse with supported formats information
    """
    try:
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        return APIResponse.success(
            data={
                'supported_formats': list(upload_service.allowed_extensions),
                'max_file_size_mb': 50,
                'format_descriptions': {
                    'pdf': 'Portable Document Format',
                    'docx': 'Microsoft Word Document (2007+)',
                    'doc': 'Microsoft Word Document (Legacy)',
                    'txt': 'Plain Text File',
                    'jpg': 'JPEG Image',
                    'jpeg': 'JPEG Image',
                    'png': 'PNG Image',
                    'tiff': 'TIFF Image',
                    'bmp': 'Bitmap Image'
                },
                'upload_guidelines': [
                    'Files must be under 50MB in size',
                    'Only supported file formats are allowed',
                    'Files should contain readable text or clear images',
                    'Duplicate content detection is performed automatically'
                ]
            },
            message="Supported file formats retrieved successfully"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to get supported formats"
        ).to_dict(), 500


@unified_api_bp.route('/files/cleanup-temp', methods=['POST'])
@api_endpoint(
    methods=['POST'],
    auth_required=True,
    rate_limit_config={'max_requests': 10, 'window_seconds': 3600}
)
def cleanup_temporary_files():
    """Clean up temporary files (admin functionality).
    
    Request Body:
        max_age_hours (int): Maximum age of files to keep in hours (optional, default: 24)
    
    Returns:
        APIResponse with cleanup result
    """
    try:
        # Note: In a real application, you'd want proper admin role checking
        # For now, we'll allow any authenticated user to clean their own temp files
        
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        
        # Validate max_age_hours
        if not isinstance(max_age_hours, int) or max_age_hours < 1:
            return ErrorResponse.validation_error(
                message="Invalid max_age_hours",
                details=[{
                    "field": "max_age_hours",
                    "message": "max_age_hours must be a positive integer"
                }]
            ).to_dict(), 400
        
        if not upload_service:
            return ErrorResponse.service_unavailable(
                message="Upload service is not available"
            ).to_dict(), 503
        
        result = upload_service.cleanup_temp_files(max_age_hours)
        
        return APIResponse.success(
            data={
                'files_cleaned': result.get('files_cleaned', 0),
                'space_freed_mb': result.get('space_freed_mb', 0),
                'max_age_hours': max_age_hours
            },
            message=f"Temporary files cleanup completed. {result.get('files_cleaned', 0)} files removed."
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to cleanup temporary files"
        ).to_dict(), 500


@unified_api_bp.route('/files/download/submission/<int:submission_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def download_submission_file(submission_id: int):
    """Download a submission file.
    
    Args:
        submission_id: ID of the submission to download
    
    Returns:
        File download or APIResponse with error
    """
    try:
        # Validate submission ownership through guide
        submission = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id == submission_id,
            MarkingGuide.user_id == current_user.id
        ).first()
        
        if not submission:
            return ErrorResponse.not_found(
                message="Submission not found or access denied"
            ).to_dict(), 404
        
        # Check if file exists
        if not submission.file_path or not os.path.exists(submission.file_path):
            return ErrorResponse.not_found(
                message="Submission file not found on disk"
            ).to_dict(), 404
        
        # Send file
        from flask import send_file
        return send_file(
            submission.file_path,
            as_attachment=True,
            download_name=submission.filename or f"submission_{submission_id}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error downloading submission file: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to download submission file"
        ).to_dict(), 500


@unified_api_bp.route('/files/download/guide/<int:guide_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 100, 'window_seconds': 3600}
)
def download_marking_guide_file(guide_id: int):
    """Download a marking guide file.
    
    Args:
        guide_id: ID of the marking guide to download
    
    Returns:
        File download or APIResponse with error
    """
    try:
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not guide:
            return ErrorResponse.not_found(
                message="Marking guide not found or access denied"
            ).to_dict(), 404
        
        # Check if file exists
        if not guide.file_path or not os.path.exists(guide.file_path):
            return ErrorResponse.not_found(
                message="Marking guide file not found on disk"
            ).to_dict(), 404
        
        # Send file
        from flask import send_file
        return send_file(
            guide.file_path,
            as_attachment=True,
            download_name=guide.filename or f"guide_{guide_id}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error downloading marking guide file: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to download marking guide file"
        ).to_dict(), 500


@unified_api_bp.route('/files/info/<file_type>/<int:file_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 200, 'window_seconds': 3600}
)
def get_file_info(file_type: str, file_id: int):
    """Get file information without downloading.
    
    Args:
        file_type: Type of file ('submission' or 'guide')
        file_id: ID of the file
    
    Returns:
        APIResponse with file information
    """
    try:
        if file_type not in ['submission', 'guide']:
            return ErrorResponse.validation_error(
                message="Invalid file type",
                details=[{
                    "field": "file_type",
                    "message": "File type must be 'submission' or 'guide'"
                }]
            ).to_dict(), 400
        
        if file_type == 'submission':
            # Validate submission ownership through guide
            file_obj = db.session.query(Submission).join(
                MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
            ).filter(
                Submission.id == file_id,
                MarkingGuide.user_id == current_user.id
            ).first()
        else:  # guide
            # Validate guide ownership
            file_obj = MarkingGuide.query.filter_by(
                id=file_id,
                user_id=current_user.id,
                is_active=True
            ).first()
        
        if not file_obj:
            return ErrorResponse.not_found(
                message=f"{file_type.title()} not found or access denied"
            ).to_dict(), 404
        
        # Get file stats if file exists
        file_stats = {}
        if file_obj.file_path and os.path.exists(file_obj.file_path):
            stat = os.stat(file_obj.file_path)
            file_stats = {
                'file_size': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'file_exists': True
            }
        else:
            file_stats = {
                'file_exists': False,
                'file_size': 0,
                'file_size_mb': 0
            }
        
        # Prepare response data
        response_data = {
            'id': file_obj.id,
            'filename': file_obj.filename,
            'file_path': file_obj.file_path,
            'created_at': file_obj.created_at.isoformat() if file_obj.created_at else None,
            'updated_at': file_obj.updated_at.isoformat() if file_obj.updated_at else None,
            **file_stats
        }
        
        # Add type-specific information
        if file_type == 'submission':
            response_data.update({
                'student_name': file_obj.student_name,
                'student_id': file_obj.student_id,
                'marking_guide_id': file_obj.marking_guide_id,
                'processed': file_obj.processed,
                'graded': file_obj.graded
            })
        else:  # guide
            response_data.update({
                'title': file_obj.title,
                'description': file_obj.description,
                'total_marks': file_obj.total_marks,
                'questions_count': len(file_obj.questions) if file_obj.questions else 0
            })
        
        return APIResponse.success(
            data=response_data,
            message=f"{file_type.title()} information retrieved successfully"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to get file information"
        ).to_dict(), 500


@unified_api_bp.route('/files/progress/<task_id>', methods=['GET'])
@api_endpoint(
    methods=['GET'],
    auth_required=True,
    rate_limit_config={'max_requests': 200, 'window_seconds': 3600}
)
def get_file_operation_progress(task_id: str):
    """Get progress of file operation (upload, processing, etc.).
    
    Args:
        task_id: ID of the file operation task
    
    Returns:
        APIResponse with progress information
    """
    try:
        # This would integrate with a task queue system like Celery
        # For now, we'll return a basic response structure
        
        # In a real implementation, you'd query your task queue/progress tracker
        # progress_info = task_queue.get_task_progress(task_id)
        
        # Mock response for demonstration
        progress_info = {
            'task_id': task_id,
            'status': 'completed',  # pending, processing, completed, failed
            'progress_percentage': 100,
            'current_step': 'File processing completed',
            'total_steps': 3,
            'completed_steps': 3,
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'result': {
                'success': True,
                'message': 'File operation completed successfully'
            }
        }
        
        return APIResponse.success(
            data=progress_info,
            message="File operation progress retrieved successfully"
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error getting file operation progress: {str(e)}")
        return ErrorResponse.processing_error(
            message="Failed to get file operation progress"
        ).to_dict(), 500
