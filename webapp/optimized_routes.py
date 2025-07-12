"""Optimized Flask routes with enhanced async processing and real-time progress tracking."""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional

from flask import Blueprint, request, jsonify, session
from flask_socketio import emit

from src.services.optimized_background_tasks import (
    process_optimized_full_pipeline,
    process_batch_submissions_optimized,
    get_task_status
)
from src.database.models import Submission, MarkingGuide, GradingResult
from src.database.models import db
from utils.logger import logger
from utils import is_guide_in_use
try:
    from src.services.realtime_service import socketio
except ImportError:
    # Fallback if realtime_service is not available
    socketio = None

# Create blueprint for optimized routes
optimized_bp = Blueprint('optimized', __name__, url_prefix='/api/optimized')


@optimized_bp.route('/process-submissions', methods=['POST'])
def process_submissions_optimized():
    """Start optimized processing of submissions with real-time progress."""
    
    try:
        data = request.get_json()
        
        # Validate input
        submission_ids = data.get('submission_ids', [])
        batch_processing = data.get('batch_processing', True)
        batch_size = data.get('batch_size', 5)
        
        if not submission_ids:
            return jsonify({
                'success': False,
                'error': 'No submission IDs provided'
            }), 400
        
        # Get the currently selected guide from session instead of request
        marking_guide_id = session.get('guide_id')
        if not marking_guide_id:
            return jsonify({
                'success': False,
                'error': 'No marking guide selected. Please select a guide using \'Use Guide\' button first.',
                'code': 'NO_GUIDE_SELECTED'
            }), 400
        
        # Validate submissions exist
        submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
        if len(submissions) != len(submission_ids):
            return jsonify({
                'success': False,
                'error': 'Some submissions not found'
            }), 404
        
        # Validate marking guide exists
        marking_guide = MarkingGuide.query.get(marking_guide_id)
        if not marking_guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found'
            }), 404
            
        # Verify guide is not currently in use
        if is_guide_in_use(marking_guide_id):
            logger.warning(f"Attempted to process guide {marking_guide_id} while it's in use")
            return jsonify({
                'success': False,
                'error': 'Marking guide is currently being used for processing. Please wait for current operations to complete.',
                'code': 'GUIDE_IN_USE'
            }), 409
        
        # Start appropriate task based on processing mode
        if batch_processing and len(submission_ids) > batch_size:
            task = process_batch_submissions_optimized.delay(
                submission_ids, marking_guide_id, batch_size
            )
        else:
            task = process_optimized_full_pipeline.delay(
                submission_ids, marking_guide_id
            )
        
        # Store task info in session
        session['current_task_id'] = task.id
        session['task_start_time'] = time.time()
        session['processing_submissions'] = submission_ids
        
        logger.info(f"Started optimized processing task {task.id} for {len(submission_ids)} submissions")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': f'Started processing {len(submission_ids)} submissions',
            'estimated_time': len(submission_ids) * 10,  # Rough estimate: 10s per submission
            'batch_processing': batch_processing
        })
        
    except Exception as e:
        logger.error(f"Failed to start optimized processing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@optimized_bp.route('/task-status/<task_id>', methods=['GET'])
def get_task_status_route(task_id: str):
    """Get detailed status of a processing task."""
    
    try:
        # Get task status
        status_result = get_task_status.delay(task_id).get(timeout=5)
        
        # Add additional context if this is the current session task
        if session.get('current_task_id') == task_id:
            status_result['is_current_task'] = True
            status_result['start_time'] = session.get('task_start_time')
            status_result['submission_ids'] = session.get('processing_submissions', [])
        
        return jsonify(status_result)
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        return jsonify({
            'task_id': task_id,
            'status': 'ERROR',
            'error': str(e)
        }), 500


@optimized_bp.route('/results/<task_id>', methods=['GET'])
def get_processing_results(task_id: str):
    """Get results of completed processing task."""
    
    try:
        # Get task status and results
        status_result = get_task_status.delay(task_id).get(timeout=5)
        
        if status_result.get('status') != 'SUCCESS':
            return jsonify({
                'success': False,
                'error': 'Task not completed successfully',
                'status': status_result.get('status')
            }), 400
        
        task_result = status_result.get('result', {})
        
        if not task_result.get('success'):
            return jsonify({
                'success': False,
                'error': task_result.get('error', 'Unknown error'),
                'task_result': task_result
            }), 500
        
        # Get detailed grading results from database
        submission_ids = [r.get('submission_id') for r in task_result.get('results', []) if r.get('success')]
        
        grading_results = []
        if submission_ids:
            results = GradingResult.query.filter(
                GradingResult.submission_id.in_(submission_ids)
            ).order_by(GradingResult.created_at.desc()).all()
            
            for result in results:
                grading_results.append({
                    'submission_id': result.submission_id,
                    'total_score': result.total_score,
                    'max_possible_score': result.max_possible_score,
                    'percentage': result.percentage,
                    'letter_grade': result.letter_grade,
                    'detailed_feedback': json.loads(result.detailed_feedback) if result.detailed_feedback else [],
                    'summary': json.loads(result.summary) if result.summary else {},
                    'created_at': result.created_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'summary': task_result.get('summary', {}),
            'total_submissions': task_result.get('total_submissions', 0),
            'successful_count': task_result.get('successful_count', 0),
            'failed_count': task_result.get('failed_count', 0),
            'grading_results': grading_results,
            'processing_time': task_result.get('summary', {}).get('processing_time', 0)
        })
        
    except Exception as e:
        logger.error(f"Failed to get results for task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@optimized_bp.route('/cancel-task/<task_id>', methods=['POST'])
def cancel_processing_task(task_id: str):
    """Cancel a running processing task."""
    
    try:
        from src.services.optimized_background_tasks import celery_app
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        # Clear session if this was the current task
        if session.get('current_task_id') == task_id:
            session.pop('current_task_id', None)
            session.pop('task_start_time', None)
            session.pop('processing_submissions', None)
        
        logger.info(f"Cancelled processing task {task_id}")
        
        return jsonify({
            'success': True,
            'message': f'Task {task_id} cancelled'
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@optimized_bp.route('/performance-stats', methods=['GET'])
def get_performance_stats():
    """Get performance statistics for the optimized services."""
    
    try:
        from src.services.optimized_ocr_service import OptimizedOCRService
        from src.services.optimized_grading_service import OptimizedGradingService
        
        # Initialize services to get stats
        ocr_service = OptimizedOCRService()
        grading_service = OptimizedGradingService()
        
        stats = {
            'ocr_cache': ocr_service.get_cache_stats(),
            'grading_config': grading_service.get_grading_stats(),
            'recent_tasks': _get_recent_task_stats(),
            'system_info': {
                'max_workers': ocr_service.max_workers,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _get_recent_task_stats() -> Dict:
    """Get statistics about recent processing tasks."""
    try:
        # Get recent grading results (last 24 hours)
        from datetime import timedelta
        
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_results = GradingResult.query.filter(
            GradingResult.created_at >= recent_cutoff
        ).all()
        
        if not recent_results:
            return {
                'total_processed': 0,
                'average_score': 0,
                'processing_time_avg': 0
            }
        
        total_processed = len(recent_results)
        average_score = sum(r.percentage for r in recent_results) / total_processed
        
        return {
            'total_processed': total_processed,
            'average_score': round(average_score, 2),
            'score_distribution': _calculate_score_distribution(recent_results),
            'last_24h': True
        }
        
    except Exception as e:
        logger.warning(f"Failed to get recent task stats: {e}")
        return {'error': str(e)}


def _calculate_score_distribution(results: List) -> Dict:
    """Calculate score distribution for results."""
    distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    
    for result in results:
        grade = result.letter_grade
        if grade in distribution:
            distribution[grade] += 1
    
    return distribution


# WebSocket event handlers for real-time updates
@socketio.on('join_task_room')
def handle_join_task_room(data):
    """Join a room for task-specific updates."""
    task_id = data.get('task_id')
    if task_id:
        from flask_socketio import join_room
        join_room(f"task_{task_id}")
        emit('joined_task_room', {'task_id': task_id})


@socketio.on('leave_task_room')
def handle_leave_task_room(data):
    """Leave a task-specific room."""
    task_id = data.get('task_id')
    if task_id:
        from flask_socketio import leave_room
        leave_room(f"task_{task_id}")
        emit('left_task_room', {'task_id': task_id})


@socketio.on('request_task_status')
def handle_task_status_request(data):
    """Handle real-time task status requests."""
    task_id = data.get('task_id')
    if task_id:
        try:
            status_result = get_task_status.delay(task_id).get(timeout=3)
            emit('task_status_update', {
                'task_id': task_id,
                'status': status_result
            })
        except Exception as e:
            emit('task_status_error', {
                'task_id': task_id,
                'error': str(e)
            })


# Error handlers
@optimized_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@optimized_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500