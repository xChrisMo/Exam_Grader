"""Refactored AI Processing API Endpoints.

Provides Flask routes and SocketIO events for the refactored unified AI processing pipeline
with detailed step-by-step progress tracking.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room

from src.database.models import db, Submission, MarkingGuide, GradingSession
from src.services.refactored_unified_ai_service import RefactoredUnifiedAIService
from utils.logger import logger

# Create blueprint
refactored_ai_bp = Blueprint('refactored_ai', __name__, url_prefix='/api/refactored-ai')

# Global service instance (will be initialized in app factory)
refactored_ai_service: Optional[RefactoredUnifiedAIService] = None


def init_refactored_ai_service(llm_service, mapping_service, grading_service):
    """Initialize the refactored AI service with dependencies."""
    global refactored_ai_service
    refactored_ai_service = RefactoredUnifiedAIService(
        llm_service=llm_service,
        mapping_service=mapping_service,
        grading_service=grading_service
    )
    logger.info("Refactored AI service initialized")


class ProgressTracker:
    """Manages real-time progress updates via SocketIO."""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.active_sessions = {}
        
    def start_tracking(self, session_id: str, user_id: str, room_id: str):
        """Start tracking progress for a session."""
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'room_id': room_id,
            'start_time': datetime.now().isoformat()
        }
        logger.info(f"Started progress tracking for session {session_id}")
        
    def update_progress(self, progress_data: Dict[str, Any]):
        """Send progress update via SocketIO."""
        session_id = progress_data.get('session_id')
        if session_id in self.active_sessions:
            room_id = self.active_sessions[session_id]['room_id']
            
            # Emit to specific room
            self.socketio.emit('progress_update', progress_data, room=room_id)
            
            # Also emit to general progress room for dashboard updates
            self.socketio.emit('ai_progress', progress_data, room=f"user_{self.active_sessions[session_id]['user_id']}")
            
            logger.debug(f"Progress update sent for session {session_id}: {progress_data.get('status')}")
            
    def stop_tracking(self, session_id: str):
        """Stop tracking progress for a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Stopped progress tracking for session {session_id}")


# Global progress tracker (will be initialized with SocketIO)
progress_tracker: Optional[ProgressTracker] = None


def init_progress_tracker(socketio_instance):
    """Initialize the progress tracker with SocketIO instance."""
    global progress_tracker
    progress_tracker = ProgressTracker(socketio_instance)
    logger.info("Progress tracker initialized")


@refactored_ai_bp.route('/process', methods=['POST'])
@login_required
def process_submission():
    """Start refactored AI processing for a submission."""
    try:
        if not refactored_ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not initialized'
            }), 500
            
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        submission_id = data.get('submission_id')
        guide_id = data.get('guide_id')
        
        if not submission_id or not guide_id:
            return jsonify({
                'success': False,
                'error': 'submission_id and guide_id are required'
            }), 400
            
        # Validate submission exists and belongs to user
        submission = db.session.query(Submission).filter_by(
            id=submission_id,
            user_id=current_user.id
        ).first()
        
        if not submission:
            return jsonify({
                'success': False,
                'error': 'Submission not found or access denied'
            }), 404
            
        # Validate marking guide exists and belongs to user
        marking_guide = db.session.query(MarkingGuide).filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found or access denied'
            }), 404
            
        # Check if already processing
        existing_session = db.session.query(GradingSession).filter_by(
            submission_id=submission_id,
            marking_guide_id=guide_id,
            status='in_progress'
        ).first()
        
        if existing_session:
            return jsonify({
                'success': False,
                'error': 'Processing already in progress for this submission',
                'session_id': existing_session.id
            }), 409
            
        # Generate room ID for real-time updates
        room_id = f"processing_{uuid.uuid4()}"
        
        # Set up progress callback
        def progress_callback(progress_data):
            if progress_tracker:
                progress_tracker.update_progress(progress_data)
                
        refactored_ai_service.set_progress_callback(progress_callback)
        
        # Start processing (this should be async in production)
        result = refactored_ai_service.process_submission(
            submission_id=submission_id,
            guide_id=guide_id,
            user_id=current_user.id
        )
        
        # Start progress tracking
        if progress_tracker and result.get('session_id'):
            progress_tracker.start_tracking(
                result['session_id'],
                current_user.id,
                room_id
            )
            
        # Add room_id to response for frontend to join
        result['room_id'] = room_id
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_submission endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Processing failed: {str(e)}'
        }), 500


@refactored_ai_bp.route('/status/<session_id>', methods=['GET'])
@login_required
def get_session_status(session_id: str):
    """Get current status of a processing session."""
    try:
        if not refactored_ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not initialized'
            }), 500
            
        # Validate session belongs to current user
        grading_session = db.session.query(GradingSession).filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not grading_session:
            return jsonify({
                'success': False,
                'error': 'Session not found or access denied'
            }), 404
            
        status = refactored_ai_service.get_session_status(session_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Session status not available'
            }), 404
            
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error in get_session_status endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get status: {str(e)}'
        }), 500


@refactored_ai_bp.route('/sessions', methods=['GET'])
@login_required
def list_user_sessions():
    """List all processing sessions for the current user."""
    try:
        sessions = db.session.query(GradingSession).filter_by(
            user_id=current_user.id
        ).order_by(GradingSession.created_at.desc()).limit(50).all()
        
        session_list = []
        for session in sessions:
            session_data = session.to_dict()
            
            # Add submission and guide info
            if session.submission:
                session_data['submission_filename'] = session.submission.filename
                session_data['student_name'] = session.submission.student_name
                
            if session.marking_guide:
                session_data['guide_title'] = session.marking_guide.title
                session_data['guide_filename'] = session.marking_guide.filename
                
            session_list.append(session_data)
            
        return jsonify({
            'success': True,
            'sessions': session_list
        })
        
    except Exception as e:
        logger.error(f"Error in list_user_sessions endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to list sessions: {str(e)}'
        }), 500


@refactored_ai_bp.route('/progress/<progress_id>', methods=['GET'])
@login_required
def get_progress(progress_id: str):
    """Get progress for a specific progress ID (for polling fallback)."""
    try:
        # Find session by progress_id
        grading_session = db.session.query(GradingSession).filter_by(
            progress_id=progress_id,
            user_id=current_user.id
        ).first()
        
        if not grading_session:
            return jsonify({
                'success': False,
                'error': 'Progress session not found'
            }), 404
            
        # Convert to progress format expected by frontend
        progress_data = {
            'session_id': grading_session.id,
            'status': grading_session.status,
            'current_step': grading_session.current_step,
            'steps': {
                'text_retrieval': 'completed' if grading_session.current_step in ['mapping', 'grading', 'saving'] or grading_session.status == 'completed' else ('in_progress' if grading_session.current_step == 'text_retrieval' else 'pending'),
                'mapping': 'completed' if grading_session.current_step in ['grading', 'saving'] or grading_session.status == 'completed' else ('in_progress' if grading_session.current_step == 'mapping' else 'pending'),
                'grading': 'completed' if grading_session.current_step in ['saving'] or grading_session.status == 'completed' else ('in_progress' if grading_session.current_step == 'grading' else 'pending'),
                'saving': 'completed' if grading_session.status == 'completed' else ('in_progress' if grading_session.current_step == 'saving' else 'pending')
            },
            'questions_mapped': grading_session.total_questions_mapped,
            'questions_graded': grading_session.total_questions_graded,
            'max_questions_limit': grading_session.max_questions_limit,
            'error_message': grading_session.error_message,
            'timestamp': grading_session.updated_at.isoformat()
        }
        
        # Calculate progress percentage
        if grading_session.status == 'completed':
            progress_data['progress_percentage'] = 100.0
        elif grading_session.status == 'failed':
            progress_data['progress_percentage'] = 0.0
        else:
            step_percentages = {
                'text_retrieval': 25,
                'mapping': 50,
                'grading': 75,
                'saving': 100
            }
            progress_data['progress_percentage'] = step_percentages.get(grading_session.current_step, 0)
            
        return jsonify({
            'success': True,
            'progress': progress_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_progress endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get progress: {str(e)}'
        }), 500


# SocketIO Event Handlers
def register_socketio_events(socketio):
    """Register SocketIO event handlers for real-time progress updates."""
    
    @socketio.on('join_progress_room')
    def handle_join_progress_room(data):
        """Join a progress tracking room."""
        room_id = data.get('room_id')
        if room_id:
            join_room(room_id)
            emit('joined_room', {'room_id': room_id})
            logger.debug(f"User joined progress room: {room_id}")
            
    @socketio.on('leave_progress_room')
    def handle_leave_progress_room(data):
        """Leave a progress tracking room."""
        room_id = data.get('room_id')
        if room_id:
            leave_room(room_id)
            emit('left_room', {'room_id': room_id})
            logger.debug(f"User left progress room: {room_id}")
            
    @socketio.on('subscribe_user_progress')
    def handle_subscribe_user_progress():
        """Subscribe to user-specific progress updates."""
        if current_user.is_authenticated:
            user_room = f"user_{current_user.id}"
            join_room(user_room)
            emit('subscribed_user_progress', {'user_id': current_user.id})
            logger.debug(f"User {current_user.id} subscribed to progress updates")
            
    @socketio.on('unsubscribe_user_progress')
    def handle_unsubscribe_user_progress():
        """Unsubscribe from user-specific progress updates."""
        if current_user.is_authenticated:
            user_room = f"user_{current_user.id}"
            leave_room(user_room)
            emit('unsubscribed_user_progress', {'user_id': current_user.id})
            logger.debug(f"User {current_user.id} unsubscribed from progress updates")
            
    @socketio.on('get_session_status')
    def handle_get_session_status(data):
        """Get session status via SocketIO."""
        session_id = data.get('session_id')
        if session_id and refactored_ai_service:
            status = refactored_ai_service.get_session_status(session_id)
            emit('session_status', {
                'session_id': session_id,
                'status': status
            })


# Sample JSON structures for documentation
SAMPLE_PROGRESS_UPDATE = {
    "session_id": "uuid-string",
    "status": "grading",  # not_started, text_retrieval, mapping, grading, saving, completed, failed
    "steps": {
        "text_retrieval": "completed",  # pending, in_progress, completed, failed
        "mapping": "completed",
        "grading": "in_progress",
        "saving": "pending"
    },
    "current_operation": "Grading mapped answers",
    "progress_percentage": 65.0,
    "questions_mapped": 8,
    "questions_graded": 5,
    "max_questions_limit": 10,
    "timestamp": "2024-01-15T10:30:45.123Z"
}

SAMPLE_PROCESS_REQUEST = {
    "submission_id": "uuid-string",
    "guide_id": "uuid-string"
}

SAMPLE_PROCESS_RESPONSE = {
    "success": True,
    "session_id": "uuid-string",
    "submission_id": "uuid-string",
    "guide_id": "uuid-string",
    "room_id": "processing_uuid-string",
    "processing_time": 45.67,
    "questions_mapped": 12,
    "questions_graded": 10,
    "questions_selected": 10,
    "max_questions_limit": 10,
    "mappings_saved": 10,
    "results_saved": 10,
    "status": "completed",
    "steps": {
        "text_retrieval": "completed",
        "mapping": "completed",
        "grading": "completed",
        "saving": "completed"
    }
}

SAMPLE_ERROR_RESPONSE = {
    "success": False,
    "error": "LLM mapping failed: Connection timeout",
    "session_id": "uuid-string",
    "submission_id": "uuid-string",
    "guide_id": "uuid-string",
    "status": "failed",
    "steps": {
        "text_retrieval": "completed",
        "mapping": "failed",
        "grading": "pending",
        "saving": "pending"
    },
    "questions_mapped": 0,
    "questions_graded": 0,
    "max_questions_limit": 10
}