"""Flask routes for the refactored AI processing system.

Provides endpoints for:
- Refactored AI processing interface
- Integration with the new pipeline
- Form data population
- Session management
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from src.database.models import Submission, MarkingGuide, GradingSession, GradingResult
from src.database import db
from src.services.unified_ai_service import UnifiedAIService
from datetime import datetime
import logging

# Create blueprint
refactored_bp = Blueprint('refactored', __name__, url_prefix='/refactored')
logger = logging.getLogger(__name__)

# Initialize services
ai_service = UnifiedAIService()

# Import ProgressTracker
from src.services.progress_tracker import ProgressTracker
progress_tracker = ProgressTracker()

@refactored_bp.route('/ai-processing')
@login_required
def ai_processing():
    """Render the refactored AI processing interface."""
    try:
        # Get user's submissions
        submissions = Submission.query.filter_by(
            user_id=current_user.id
        ).order_by(Submission.created_at.desc()).all()
        
        # Get available marking guides
        marking_guides = MarkingGuide.query.filter_by(
            user_id=current_user.id
        ).order_by(MarkingGuide.created_at.desc()).all()
        
        # Get recent processing sessions for this user
        recent_sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id
        ).order_by(GradingSession.created_at.desc()).limit(10).all()
        
        return render_template(
            'refactored_ai_processing.html',
            submissions=submissions,
            marking_guides=marking_guides,
            recent_sessions=recent_sessions,
            page_title='Refactored AI Processing'
        )
        
    except Exception as e:
        logger.error(f"Error loading AI processing page: {str(e)}")
        return render_template(
            'error.html',
            error_message="Failed to load AI processing interface",
            error_details=str(e)
        ), 500

@refactored_bp.route('/api/submissions')
@login_required
def get_submissions():
    """Get user's submissions for the form dropdown."""
    try:
        # Get marking_guide_id from query parameters
        marking_guide_id = request.args.get('marking_guide_id')
        
        # Build query
        query = Submission.query.filter_by(user_id=current_user.id)
        
        # Filter by marking guide if provided
        if marking_guide_id:
            query = query.filter_by(marking_guide_id=marking_guide_id)
        
        submissions = query.order_by(Submission.created_at.desc()).all()
        
        submissions_data = []
        for submission in submissions:
            submissions_data.append({
                'id': submission.id,
                'filename': submission.filename,
                'student_name': submission.student_name,
                'created_at': submission.created_at.isoformat(),
                'processing_status': submission.processing_status,
                'has_content_text': bool(submission.content_text)
            })
        
        return jsonify({
            'success': True,
            'submissions': submissions_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching submissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@refactored_bp.route('/api/marking-guides')
@login_required
def get_marking_guides():
    """Get user's marking guides for the form dropdown."""
    try:
        guides = MarkingGuide.query.filter_by(
            user_id=current_user.id
        ).order_by(MarkingGuide.created_at.desc()).all()
        
        guides_data = []
        for guide in guides:
            # Safely calculate questions count and total marks
            questions_count = 0
            total_marks = 0
            
            if guide.questions and isinstance(guide.questions, list):
                questions_count = len(guide.questions)
                try:
                    # Safely calculate total marks, handling potential data corruption
                    for q in guide.questions:
                        if isinstance(q, dict) and 'marks' in q:
                            marks = q.get('marks', 0)
                            if isinstance(marks, (int, float)):
                                total_marks += marks
                except (TypeError, AttributeError) as e:
                    logger.warning(f"Error calculating total marks for guide {guide.id}: {str(e)}")
                    total_marks = guide.total_marks or 0
            else:
                # Fallback to stored total_marks if questions data is corrupted
                total_marks = guide.total_marks or 0
            
            guides_data.append({
                'id': guide.id,
                'title': guide.title,
                'created_at': guide.created_at.isoformat(),
                'max_questions_to_answer': guide.max_questions_to_answer,
                'questions_count': questions_count,
                'total_marks': total_marks
            })
        
        return jsonify({
            'success': True,
            'guides': guides_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching marking guides: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@refactored_bp.route('/api/sessions')
@login_required
def get_user_sessions():
    """Get user's processing sessions."""
    try:
        sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id
        ).order_by(GradingSession.created_at.desc()).limit(20).all()
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'submission_id': session.submission_id,
                'guide_id': session.guide_id,
                'status': session.status,
                'current_step': session.current_step,
                'progress_percentage': session.progress_percentage,
                'total_questions_mapped': session.total_questions_mapped,
                'total_questions_graded': session.total_questions_graded,
                'max_questions_limit': session.max_questions_limit,
                'created_at': session.created_at.isoformat(),
                'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                'error_message': session.error_message
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@refactored_bp.route('/api/session/<session_id>/details')
@login_required
def get_session_details(session_id):
    """Get detailed information about a specific session."""
    try:
        session_obj = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            GradingSession.id == session_id,
            Submission.user_id == current_user.id
        ).first()
        
        if not session_obj:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get submission and guide details
        submission = Submission.query.get(session_obj.submission_id)
        guide = MarkingGuide.query.get(session_obj.guide_id)
        
        session_data = {
            'id': session_obj.id,
            'submission': {
                'id': submission.id,
                'filename': submission.filename,
                'created_at': submission.created_at.isoformat()
            },
            'guide': {
                'id': guide.id,
                'title': guide.title,
                'max_questions_to_answer': guide.max_questions_to_answer
            },
            'status': session_obj.status,
            'current_step': session_obj.current_step,
            'progress_percentage': session_obj.progress_percentage,
            'total_questions_mapped': session_obj.total_questions_mapped,
            'total_questions_graded': session_obj.total_questions_graded,
            'max_questions_limit': session_obj.max_questions_limit,
            'created_at': session_obj.created_at.isoformat(),
            'started_at': session_obj.started_at.isoformat() if session_obj.started_at else None,
            'completed_at': session_obj.completed_at.isoformat() if session_obj.completed_at else None,
            'processing_time_seconds': session_obj.processing_time_seconds,
            'error_message': session_obj.error_message,
            'session_data': session_obj.session_data
        }
        
        return jsonify({
            'success': True,
            'session': session_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching session details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@refactored_bp.route('/api/validate-selection', methods=['POST'])
@login_required
def validate_selection():
    """Validate submission and guide selection before processing."""
    try:
        data = request.get_json()
        submission_id = data.get('submission_id')
        guide_id = data.get('guide_id')
        
        if not submission_id or not guide_id:
            return jsonify({
                'success': False,
                'error': 'Both submission and guide must be selected'
            }), 400
        
        # Validate submission belongs to user
        submission = Submission.query.filter_by(
            id=submission_id,
            user_id=current_user.id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found or access denied'
            }), 404
        
        # Validate guide belongs to user
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied'
            }), 404
        
        # Check if submission has content text
        if not submission.content_text:
            return jsonify({
                'success': False,
                'error': 'Submission does not have content text. Please process OCR first.'
            }), 400
        
        # Check if guide has questions
        if not guide.questions:
            return jsonify({
                'success': False,
                'error': 'Marking guide does not have questions defined'
            }), 400
        
        # Check for existing active session
        existing_session = GradingSession.query.filter_by(
            submission_id=submission_id,
            guide_id=guide_id,
            status='in_progress'
        ).first()
        
        # Safely calculate questions count
        questions_count = 0
        if guide.questions and isinstance(guide.questions, list):
            questions_count = len(guide.questions)
        elif guide.questions and isinstance(guide.questions, dict):
            questions_count = len(guide.questions.get('questions', []))
        
        validation_result = {
            'submission': {
                'id': submission.id,
                'filename': submission.filename,
                'has_content_text': bool(submission.content_text)
            },
            'guide': {
                'id': guide.id,
                'title': guide.title,
                'max_questions_to_answer': guide.max_questions_to_answer,
                'question_count': questions_count
            },
            'existing_session': {
                'id': existing_session.id,
                'status': existing_session.status,
                'current_step': existing_session.current_step,
                'progress_percentage': existing_session.progress_percentage
            } if existing_session else None
        }
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"Error validating selection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@refactored_bp.route('/dashboard')
@login_required
def dashboard():
    """Refactored AI processing dashboard."""
    try:
        # Get summary statistics
        total_submissions = Submission.query.filter_by(user_id=current_user.id).count()
        total_guides = MarkingGuide.query.filter_by(user_id=current_user.id).count()
        
        # Get recent sessions
        recent_sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id
        ).order_by(GradingSession.created_at.desc()).limit(5).all()
        
        # Get session statistics
        completed_sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id,
            GradingSession.status == 'completed'
        ).count()
        
        failed_sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id,
            GradingSession.status == 'failed'
        ).count()
        
        in_progress_sessions = GradingSession.query.join(
            Submission, GradingSession.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id,
            GradingSession.status == 'in_progress'
        ).count()
        
        dashboard_data = {
            'total_submissions': total_submissions,
            'total_guides': total_guides,
            'completed_sessions': completed_sessions,
            'failed_sessions': failed_sessions,
            'in_progress_sessions': in_progress_sessions,
            'recent_sessions': recent_sessions
        }
        
        # Get additional context data
        from flask_wtf.csrf import generate_csrf
        from flask import session
        
        # Get submissions for the user
        submissions = Submission.query.filter_by(user_id=current_user.id).all()
        
        # Calculate last score from recent grading results
        last_grading_result = GradingResult.query.join(
            Submission, GradingResult.submission_id == Submission.id
        ).filter(
            Submission.user_id == current_user.id
        ).order_by(GradingResult.created_at.desc()).first()
        
        last_score = last_grading_result.score if last_grading_result else 0
        
        # Create recent activity from sessions
        recent_activity = []
        for session_item in recent_sessions[:5]:
            recent_activity.append({
                'type': 'grading_session',
                'icon': 'check' if session_item.status == 'completed' else 'document',
                'message': f'Grading session {session_item.status}',
                'timestamp': session_item.created_at,
                'id': session_item.id
            })
        
        return render_template(
            'dashboard.html',
            total_submissions=dashboard_data['total_submissions'],
            processed_submissions=dashboard_data['completed_sessions'],
            guide_uploaded=dashboard_data['total_guides'] > 0,
            last_score=last_score,
            avg_score=0,
            recent_activity=recent_activity,
            submissions=submissions,
            service_status={'ocr_status': True, 'llm_status': True, 'storage_status': True},
            guide_storage_available=True,
            submission_storage_available=True,
            page_title='Dashboard',
            csrf_token=generate_csrf(),
            max_file_size=16,
            app_version='1.0.0',
            current_year=2025
        )
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template(
            'error.html',
            error_message="Failed to load dashboard",
            error_details=str(e)
        ), 500

@refactored_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for refactored routes."""
    return render_template(
        'error.html',
        error_message="Page not found",
        error_details="The requested page could not be found."
    ), 404

@refactored_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for refactored routes."""
    logger.error(f"Internal error in refactored routes: {str(error)}")
    return render_template(
        'error.html',
        error_message="Internal server error",
        error_details="An unexpected error occurred. Please try again later."
    ), 500

# Note: Progress tracking setup is handled in the main app initialization