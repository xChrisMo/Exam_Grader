"""Enhanced Processing API endpoints for LLM-driven pipeline.

This module provides REST API endpoints for the new enhanced processing pipeline:
1. Marking Guide Processing - LLM extracts structured questions/answers
2. Submission Processing - OCR + LLM mapping to guide questions
3. Grading Process - LLM grades with max_questions_to_answer logic
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_required, current_user
import os
from typing import Dict, Any

from src.services.enhanced_processing_service import EnhancedProcessingService
from src.services.consolidated_llm_service import ConsolidatedLLMService as LLMService
from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService
from src.database.models import db, User, MarkingGuide, Submission, GradingSession
from utils.logger import logger
from utils.input_sanitizer import InputSanitizer

# Create blueprint
enhanced_processing_bp = Blueprint('enhanced_processing', __name__, url_prefix='/api/enhanced')

# Initialize services
processing_service = None
input_sanitizer = InputSanitizer()

def init_enhanced_processing_services(app):
    """Initialize enhanced processing services with app context.
    
    Args:
        app: Flask application instance
    """
    global processing_service
    
    with app.app_context():
        try:
            # Initialize services
            llm_service = LLMService()
            ocr_service = OCRService()
            processing_service = EnhancedProcessingService(llm_service, ocr_service)
            
            logger.info("Enhanced processing services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced processing services: {e}")
            raise

def require_auth():
    """Check if user is authenticated.
    
    Returns:
        User ID if authenticated, None otherwise
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    # Verify user exists in database
    user = db.session.query(User).filter(User.id == user_id).first()
    return user.id if user else None

@enhanced_processing_bp.route('/process-guide', methods=['POST'])
def process_marking_guide():
    """Process marking guide using LLM to extract structured content.
    
    Expected JSON data:
    - guide_id: ID of the marking guide to process
    
    Returns:
        JSON response with processing result
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'code': 'NO_DATA'
            }), 400
        
        guide_id = data.get('guide_id')
        if not guide_id:
            return jsonify({
                'success': False,
                'error': 'Guide ID is required',
                'code': 'MISSING_GUIDE_ID'
            }), 400
        
        # Verify marking guide exists and belongs to user
        marking_guide = db.session.query(MarkingGuide).filter(
            MarkingGuide.id == guide_id,
            MarkingGuide.user_id == user_id,
            MarkingGuide.is_active == True
        ).first()
        
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied',
                'code': 'GUIDE_NOT_FOUND'
            }), 404
        
        # Check if guide has raw content to process
        if not marking_guide.content_text:
            return jsonify({
                'success': False,
                'error': 'No content available for processing',
                'code': 'NO_CONTENT'
            }), 400
        
        # Process the marking guide
        result, error = processing_service.process_marking_guide(
            guide_id=guide_id,
            file_path=marking_guide.file_path or '',
            raw_content=marking_guide.content_text
        )
        
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'code': 'PROCESSING_ERROR'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Marking guide processed successfully',
            'data': {
                'guide_id': guide_id,
                'structured_content': result,
                'questions_extracted': len(result.get('questions', [])),
                'total_marks': result.get('total_marks', 0)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in process_marking_guide endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@enhanced_processing_bp.route('/process-submission', methods=['POST'])
def process_submission():
    """Process student submission using OCR and LLM mapping.
    
    Expected JSON data:
    - submission_id: ID of the submission to process
    - marking_guide_id: ID of the associated marking guide
    
    Returns:
        JSON response with processing result
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'code': 'NO_DATA'
            }), 400
        
        submission_id = data.get('submission_id')
        marking_guide_id = data.get('marking_guide_id')
        
        if not submission_id:
            return jsonify({
                'success': False,
                'error': 'Submission ID is required',
                'code': 'MISSING_SUBMISSION_ID'
            }), 400
        
        if not marking_guide_id:
            return jsonify({
                'success': False,
                'error': 'Marking guide ID is required',
                'code': 'MISSING_GUIDE_ID'
            }), 400
        
        # Verify submission exists and belongs to user
        submission = db.session.query(Submission).filter(
            Submission.id == submission_id,
            Submission.user_id == user_id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found or access denied',
                'code': 'SUBMISSION_NOT_FOUND'
            }), 404
        
        # Verify marking guide exists and belongs to user
        marking_guide = db.session.query(MarkingGuide).filter(
            MarkingGuide.id == marking_guide_id,
            MarkingGuide.user_id == user_id,
            MarkingGuide.is_active == True
        ).first()
        
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied',
                'code': 'GUIDE_NOT_FOUND'
            }), 404
        
        # Check if marking guide has been processed
        if not marking_guide.questions:
            return jsonify({
                'success': False,
                'error': 'Marking guide must be processed first',
                'code': 'GUIDE_NOT_PROCESSED'
            }), 400
        
        # Process the submission
        result, error = processing_service.process_submission(
            submission_id=submission_id,
            file_path=submission.file_path or '',
            marking_guide_id=marking_guide_id
        )
        
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'code': 'PROCESSING_ERROR'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Submission processed successfully',
            'data': {
                'submission_id': submission_id,
                'mapping_result': result,
                'answers_mapped': len(result.get('mappings', [])),
                'processing_status': 'completed'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in process_submission endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@enhanced_processing_bp.route('/process-grading', methods=['POST'])
def process_grading():
    """Process grading with max_questions_to_answer logic.
    
    Expected JSON data:
    - submission_id: ID of the submission to grade
    - marking_guide_id: ID of the marking guide
    - max_questions_to_answer: Optional maximum number of questions to grade
    
    Returns:
        JSON response with grading result
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'code': 'NO_DATA'
            }), 400
        
        submission_id = data.get('submission_id')
        marking_guide_id = data.get('marking_guide_id')
        max_questions_to_answer = data.get('max_questions_to_answer')
        
        if not submission_id:
            return jsonify({
                'success': False,
                'error': 'Submission ID is required',
                'code': 'MISSING_SUBMISSION_ID'
            }), 400
        
        if not marking_guide_id:
            return jsonify({
                'success': False,
                'error': 'Marking guide ID is required',
                'code': 'MISSING_GUIDE_ID'
            }), 400
        
        # Verify submission exists and belongs to user
        submission = db.session.query(Submission).filter(
            Submission.id == submission_id,
            Submission.user_id == user_id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found or access denied',
                'code': 'SUBMISSION_NOT_FOUND'
            }), 404
        
        # Verify marking guide exists and belongs to user
        marking_guide = db.session.query(MarkingGuide).filter(
            MarkingGuide.id == marking_guide_id,
            MarkingGuide.user_id == user_id,
            MarkingGuide.is_active == True
        ).first()
        
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied',
                'code': 'GUIDE_NOT_FOUND'
            }), 404
        
        # Check if submission has been processed (mapped)
        if not submission.processed:
            return jsonify({
                'success': False,
                'error': 'Submission must be processed first',
                'code': 'SUBMISSION_NOT_PROCESSED'
            }), 400
        
        # Process grading
        result, error = processing_service.process_grading(
            submission_id=submission_id,
            marking_guide_id=marking_guide_id,
            max_questions_to_answer=max_questions_to_answer
        )
        
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'code': 'GRADING_ERROR'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Grading completed successfully',
            'data': {
                'submission_id': submission_id,
                'grading_result': result,
                'total_score': result.get('total_score', 0),
                'percentage': result.get('percentage', 0),
                'grade_level': result.get('grade_level', 'F'),
                'questions_graded': result.get('selected_questions', 0)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in process_grading endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@enhanced_processing_bp.route('/batch-process', methods=['POST'])
def batch_process():
    """Process multiple submissions in batch with the complete pipeline.
    
    Expected JSON data:
    - submission_ids: List of submission IDs to process
    - marking_guide_id: ID of the marking guide
    - max_questions_to_answer: Optional maximum number of questions to grade
    - process_steps: List of steps to execute ['guide', 'submissions', 'grading']
    
    Returns:
        JSON response with batch processing result
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'code': 'NO_DATA'
            }), 400
        
        submission_ids = data.get('submission_ids', [])
        marking_guide_id = data.get('marking_guide_id')
        max_questions_to_answer = data.get('max_questions_to_answer')
        process_steps = data.get('process_steps', ['guide', 'submissions', 'grading'])
        
        if not submission_ids:
            return jsonify({
                'success': False,
                'error': 'Submission IDs are required',
                'code': 'MISSING_SUBMISSION_IDS'
            }), 400
        
        if not marking_guide_id:
            return jsonify({
                'success': False,
                'error': 'Marking guide ID is required',
                'code': 'MISSING_GUIDE_ID'
            }), 400
        
        # Verify marking guide exists and belongs to user
        marking_guide = db.session.query(MarkingGuide).filter(
            MarkingGuide.id == marking_guide_id,
            MarkingGuide.user_id == user_id,
            MarkingGuide.is_active == True
        ).first()
        
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied',
                'code': 'GUIDE_NOT_FOUND'
            }), 404
        
        # Verify submissions exist and belong to user
        submissions = db.session.query(Submission).filter(
            Submission.id.in_(submission_ids),
            Submission.user_id == user_id
        ).all()
        
        if len(submissions) != len(submission_ids):
            return jsonify({
                'success': False,
                'error': 'Some submissions not found or access denied',
                'code': 'SUBMISSIONS_NOT_FOUND'
            }), 404
        
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
            logger.info(f"Processing marking guide {marking_guide_id}")
            guide_result, guide_error = processing_service.process_marking_guide(
                guide_id=marking_guide_id,
                file_path=marking_guide.file_path or '',
                raw_content=marking_guide.content_text or ''
            )
            
            if guide_error:
                return jsonify({
                    'success': False,
                    'error': f"Failed to process marking guide: {guide_error}",
                    'code': 'GUIDE_PROCESSING_ERROR'
                }), 500
            
            batch_results['guide_processing'] = {
                'success': True,
                'questions_extracted': len(guide_result.get('questions', [])),
                'total_marks': guide_result.get('total_marks', 0)
            }
        
        # Step 2: Process submissions if requested
        if 'submissions' in process_steps:
            logger.info(f"Processing {len(submission_ids)} submissions")
            for submission_id in submission_ids:
                try:
                    result, error = processing_service.process_submission(
                        submission_id=submission_id,
                        file_path=next(s.file_path for s in submissions if s.id == submission_id) or '',
                        marking_guide_id=marking_guide_id
                    )
                    
                    if error:
                        batch_results['submission_processing'][submission_id] = {
                            'success': False,
                            'error': error
                        }
                        batch_results['summary']['failed_processing'] += 1
                    else:
                        batch_results['submission_processing'][submission_id] = {
                            'success': True,
                            'answers_mapped': len(result.get('mappings', []))
                        }
                        batch_results['summary']['successful_processing'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing submission {submission_id}: {e}")
                    batch_results['submission_processing'][submission_id] = {
                        'success': False,
                        'error': str(e)
                    }
                    batch_results['summary']['failed_processing'] += 1
        
        # Step 3: Process grading if requested
        if 'grading' in process_steps:
            logger.info(f"Grading {len(submission_ids)} submissions")
            for submission_id in submission_ids:
                try:
                    result, error = processing_service.process_grading(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        max_questions_to_answer=max_questions_to_answer
                    )
                    
                    if error:
                        batch_results['grading_results'][submission_id] = {
                            'success': False,
                            'error': error
                        }
                        batch_results['summary']['failed_grading'] += 1
                    else:
                        batch_results['grading_results'][submission_id] = {
                            'success': True,
                            'total_score': result.get('total_score', 0),
                            'percentage': result.get('percentage', 0),
                            'grade_level': result.get('grade_level', 'F'),
                            'questions_graded': result.get('selected_questions', 0)
                        }
                        batch_results['summary']['successful_grading'] += 1
                        
                except Exception as e:
                    logger.error(f"Error grading submission {submission_id}: {e}")
                    batch_results['grading_results'][submission_id] = {
                        'success': False,
                        'error': str(e)
                    }
                    batch_results['summary']['failed_grading'] += 1
        
        return jsonify({
            'success': True,
            'message': 'Batch processing completed',
            'data': batch_results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch_process endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@enhanced_processing_bp.route('/status/<submission_id>/<marking_guide_id>', methods=['GET'])
def get_processing_status(submission_id, marking_guide_id):
    """Get current processing status for a submission.
    
    Returns:
        JSON response with processing status
    """
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Verify submission belongs to user
        submission = db.session.query(Submission).filter(
            Submission.id == submission_id,
            Submission.user_id == user_id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found or access denied',
                'code': 'SUBMISSION_NOT_FOUND'
            }), 404
        
        # Get processing status
        status_info = processing_service.get_processing_status(
            submission_id=submission_id,
            marking_guide_id=marking_guide_id
        )
        
        return jsonify({
            'success': True,
            'data': status_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_processing_status endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500