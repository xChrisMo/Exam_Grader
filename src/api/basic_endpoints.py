"""Basic API endpoints for marking guides and submissions.

This module provides basic REST API endpoints that are expected by the frontend
but may not exist in the current system.
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_login import login_required, current_user
from src.database.models import MarkingGuide, Submission, db
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


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


# Create blueprint
basic_api_bp = Blueprint('basic_api', __name__, url_prefix='/api')


@basic_api_bp.route('/marking-guides', methods=['GET'])
@login_required
def get_marking_guides():
    """Get all marking guides for the current user.
    
    Returns:
        JSON response with list of marking guides
    """
    try:
        # Get all marking guides for the current user
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
        
        guides_data = []
        for guide in guides:
            # Count questions if available
            questions_count = 0
            if guide.questions:
                try:
                    import json
                    questions_data = json.loads(guide.questions) if isinstance(guide.questions, str) else guide.questions
                    if isinstance(questions_data, list):
                        questions_count = len(questions_data)
                    elif isinstance(questions_data, dict) and 'questions' in questions_data:
                        questions_count = len(questions_data['questions'])
                except (json.JSONDecodeError, TypeError):
                    questions_count = 0
            
            guides_data.append({
                'id': guide.id,
                'title': guide.title,
                'filename': guide.filename,
                'questions_count': questions_count,
                'total_marks': guide.total_marks,
                'created_at': guide.created_at.isoformat() if guide.created_at else None,
                'updated_at': guide.updated_at.isoformat() if guide.updated_at else None,
                'questions': guide.questions is not None
            })
        
        return jsonify({
            'success': True,
            'guides': guides_data
        })
        
    except Exception as e:
        logger.error(f"Error getting marking guides: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve marking guides'
        }), 500


@basic_api_bp.route('/marking-guides/<string:guide_id>', methods=['GET'])
@login_required
def get_marking_guide(guide_id):
    """Get a specific marking guide by ID.
    
    Args:
        guide_id: ID of the marking guide
        
    Returns:
        JSON response with marking guide details
    """
    try:
        # Get the marking guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found'
            }), 404
        
        # Count questions if available
        questions_count = 0
        if guide.questions:
            try:
                import json
                questions_data = json.loads(guide.questions) if isinstance(guide.questions, str) else guide.questions
                if isinstance(questions_data, list):
                    questions_count = len(questions_data)
                elif isinstance(questions_data, dict) and 'questions' in questions_data:
                    questions_count = len(questions_data['questions'])
            except (json.JSONDecodeError, TypeError):
                questions_count = 0
        
        guide_data = {
            'id': guide.id,
            'title': guide.title,
            'filename': guide.filename,
            'questions_count': questions_count,
            'total_marks': guide.total_marks,
            'created_at': guide.created_at.isoformat() if guide.created_at else None,
            'updated_at': guide.updated_at.isoformat() if guide.updated_at else None,
            'questions': guide.questions,
            'content_text': guide.content_text
        }
        
        return jsonify({
            'success': True,
            'guide': guide_data
        })
        
    except Exception as e:
        logger.error(f"Error getting marking guide {guide_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve marking guide'
        }), 500


@basic_api_bp.route('/submissions', methods=['GET'])
@login_required
def get_submissions():
    """Get submissions, optionally filtered by marking guide.
    
    Query parameters:
        marking_guide_id: Optional, filter by marking guide ID
        
    Returns:
        JSON response with list of submissions
    """
    try:
        # Get query parameters
        marking_guide_id = request.args.get('marking_guide_id')
        
        # Build query
        query = Submission.query.filter_by(user_id=current_user.id)
        
        if marking_guide_id:
            query = query.filter_by(marking_guide_id=marking_guide_id)
        
        submissions = query.all()
        
        submissions_data = []
        for submission in submissions:
            # Determine processing status
            processing_status = 'Pending'
            if hasattr(submission, 'content_text') and submission.content_text:
                processing_status = 'Processed'
            
            submissions_data.append({
                'id': submission.id,
                'student_name': submission.student_name,
                'filename': submission.filename,
                'marking_guide_id': submission.marking_guide_id,
                'created_at': submission.created_at.isoformat() if submission.created_at else None,
                'updated_at': submission.updated_at.isoformat() if submission.updated_at else None,
                'processing_status': processing_status,
                'content_available': hasattr(submission, 'content_text') and submission.content_text is not None,
                'answers_available': False  # Will be set properly after checking database
            })
        
        return jsonify({
            'success': True,
            'submissions': submissions_data
        })
        
    except Exception as e:
        logger.error(f"Error getting submissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve submissions'
        }), 500


@basic_api_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def get_submission(submission_id):
    """Get a specific submission by ID.
    
    Args:
        submission_id: ID of the submission
        
    Returns:
        JSON response with submission details
    """
    try:
        # Get the submission
        submission = Submission.query.filter_by(
            id=submission_id,
            user_id=current_user.id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found'
            }), 404
        
        # Determine processing status
        processing_status = 'Pending'
        if hasattr(submission, 'content_text') and submission.content_text:
            processing_status = 'Processed'
        
        submission_data = {
            'id': submission.id,
            'student_name': submission.student_name,
            'filename': submission.filename,
            'marking_guide_id': submission.marking_guide_id,
            'created_at': submission.created_at.isoformat() if submission.created_at else None,
            'updated_at': submission.updated_at.isoformat() if submission.updated_at else None,
            'processing_status': processing_status,
            'content_text': getattr(submission, 'content_text', None),
            'grading_results': []  # Simplified to avoid serialization issues
        }
        
        return jsonify({
            'success': True,
            'submission': submission_data
        })
        
    except Exception as e:
        logger.error(f"Error getting submission {submission_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve submission'
        }), 500


@basic_api_bp.route('/v1/processing/batch-enhanced', methods=['POST'])
@login_required
def process_batch_enhanced():
    """Process multiple submissions with the complete enhanced pipeline.
    
    Request Body:
        submission_ids (list): List of submission IDs (required)
        marking_guide_id (int): Marking guide ID (required)
        max_questions_to_answer (int): Maximum questions to grade (optional)
        process_steps (list): Steps to execute ['grading'] (optional)
    
    Returns:
        JSON response with batch processing result
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400
        
        submission_ids = data.get('submission_ids', [])
        marking_guide_id = data.get('marking_guide_id')
        max_questions_to_answer = data.get('max_questions_to_answer')
        process_steps = data.get('process_steps', ['grading'])
        
        if not submission_ids:
            return jsonify({
                'status': 'error',
                'message': 'submission_ids is required'
            }), 400
        
        if not marking_guide_id:
            return jsonify({
                'status': 'error',
                'message': 'marking_guide_id is required'
            }), 400
        
        # Validate guide ownership
        guide = MarkingGuide.query.filter_by(
            id=marking_guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return jsonify({
                'status': 'error',
                'message': 'Marking guide not found'
            }), 404
        
        # Validate submissions ownership
        submissions = db.session.query(Submission).join(
            MarkingGuide, Submission.marking_guide_id == MarkingGuide.id
        ).filter(
            Submission.id.in_(submission_ids),
            MarkingGuide.user_id == current_user.id
        ).all()
        
        if len(submissions) != len(submission_ids):
            return jsonify({
                'status': 'error',
                'message': 'Some submissions not found or access denied'
            }), 400
        
        # Initialize enhanced processing service
        try:
            from src.services.enhanced_processing_service import EnhancedProcessingService
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            from src.services.consolidated_ocr_service import ConsolidatedOCRService
            
            llm_service = ConsolidatedLLMService()
            ocr_service = ConsolidatedOCRService()
            enhanced_service = EnhancedProcessingService(llm_service, ocr_service)
            logger.info("Enhanced processing service initialized for batch processing")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced processing service: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Enhanced processing service could not be initialized'
            }), 503
        
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
        
        # Process grading (main step)
        if 'grading' in process_steps:
            for submission_id in submission_ids:
                try:
                    result, grading_error = enhanced_service.process_grading(
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
                        percentage = result.get('percentage', 0)
                        batch_results['grading_results'][submission_id] = {
                            'success': True,
                            'total_score': result.get('total_score', 0),
                            'max_possible_score': result.get('max_possible_score', 0),
                            'percentage': percentage,
                            'grade_level': calculate_grade_level(percentage),
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
        
        return jsonify({
            'status': 'success',
            'data': batch_results,
            'message': 'Enhanced batch processing completed'
        })
        
    except Exception as e:
        logger.error(f"Error in enhanced batch processing: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to process enhanced batch request'
        }), 500


def init_basic_api_services(app):
    """Initialize basic API services.
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        logger.info("Basic API services initialized")