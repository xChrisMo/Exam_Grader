"""
Unified API Layer - Consolidated REST API

This module provides a single, unified API that replaces the fragmented
endpoint structure with a clean, RESTful interface.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from flask import Blueprint, request, jsonify, current_app, g
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from sqlalchemy.exc import SQLAlchemyError

from src.services.core_service import core_service, ProcessingRequest
from src.database.models import db, MarkingGuide, Submission, GradingResult, User
from src.models.api_responses import APIResponse, ErrorResponse
from utils.logger import logger

# Create unified API blueprint
api = Blueprint('core_api', __name__, url_prefix='/api/v1')

def api_response(data: Any = None, message: str = None, status: int = 200) -> tuple:
    """Standardized API response format."""
    response = {
        'success': status < 400,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'request_id': getattr(g, 'request_id', None)
    }
    
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    if status >= 400:
        response['error'] = message or 'An error occurred'
    
    return jsonify(response), status

def handle_api_error(error):
    """Global API error handler."""
    logger.error(f"API Error: {error}")
    
    if isinstance(error, BadRequest):
        return api_response(message="Invalid request data", status=400)
    elif isinstance(error, NotFound):
        return api_response(message="Resource not found", status=404)
    elif isinstance(error, SQLAlchemyError):
        return api_response(message="Database error", status=500)
    else:
        return api_response(message="Internal server error", status=500)

@api.before_request
def before_request():
    """Set up request context."""
    g.request_id = f"req_{int(time.time())}_{id(request)}"
    g.start_time = time.time()

@api.after_request
def after_request(response):
    """Log request completion."""
    duration = time.time() - g.start_time
    logger.info(f"API Request completed: {request.method} {request.path} - {response.status_code} ({duration:.3f}s)")
    return response

# ============================================================================
# MARKING GUIDES API
# ============================================================================

@api.route('/guides', methods=['GET'])
@login_required
def get_guides():
    """Get all marking guides for current user."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        guides = MarkingGuide.query.filter_by(
            user_id=current_user.id
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        data = {
            'guides': [{
                'id': guide.id,
                'title': guide.title,
                'description': guide.description,
                'created_at': guide.created_at.isoformat(),
                'updated_at': guide.updated_at.isoformat(),
                'question_count': len(guide.content.get('questions', [])) if guide.content else 0
            } for guide in guides.items],
            'pagination': {
                'page': guides.page,
                'pages': guides.pages,
                'per_page': guides.per_page,
                'total': guides.total
            }
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get guides: {e}")
        return api_response(message="Failed to retrieve guides", status=500)

@api.route('/guides/<guide_id>', methods=['GET'])
@login_required
def get_guide(guide_id):
    """Get specific marking guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, 
            user_id=current_user.id
        ).first()
        
        if not guide:
            return api_response(message="Guide not found", status=404)
        
        data = {
            'id': guide.id,
            'title': guide.title,
            'description': guide.description,
            'content': guide.content,
            'created_at': guide.created_at.isoformat(),
            'updated_at': guide.updated_at.isoformat()
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get guide {guide_id}: {e}")
        return api_response(message="Failed to retrieve guide", status=500)

@api.route('/guides', methods=['POST'])
@login_required
def create_guide():
    """Create new marking guide."""
    try:
        data = request.get_json()
        
        if not data or not data.get('title'):
            return api_response(message="Title is required", status=400)
        
        guide = MarkingGuide(
            id=f"guide_{int(time.time())}_{current_user.id}",
            title=data['title'],
            description=data.get('description', ''),
            content=data.get('content', {}),
            user_id=current_user.id
        )
        
        db.session.add(guide)
        db.session.commit()
        
        return api_response({
            'id': guide.id,
            'title': guide.title,
            'description': guide.description,
            'created_at': guide.created_at.isoformat()
        }, message="Guide created successfully", status=201)
        
    except Exception as e:
        logger.error(f"Failed to create guide: {e}")
        db.session.rollback()
        return api_response(message="Failed to create guide", status=500)

@api.route('/guides/<guide_id>', methods=['PUT'])
@login_required
def update_guide(guide_id):
    """Update marking guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, 
            user_id=current_user.id
        ).first()
        
        if not guide:
            return api_response(message="Guide not found", status=404)
        
        data = request.get_json()
        
        if 'title' in data:
            guide.title = data['title']
        if 'description' in data:
            guide.description = data['description']
        if 'content' in data:
            guide.content = data['content']
        
        db.session.commit()
        
        return api_response({
            'id': guide.id,
            'title': guide.title,
            'description': guide.description,
            'updated_at': guide.updated_at.isoformat()
        }, message="Guide updated successfully")
        
    except Exception as e:
        logger.error(f"Failed to update guide {guide_id}: {e}")
        db.session.rollback()
        return api_response(message="Failed to update guide", status=500)

@api.route('/guides/<guide_id>', methods=['DELETE'])
@login_required
def delete_guide(guide_id):
    """Delete marking guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, 
            user_id=current_user.id
        ).first()
        
        if not guide:
            return api_response(message="Guide not found", status=404)
        
        db.session.delete(guide)
        db.session.commit()
        
        return api_response(message="Guide deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete guide {guide_id}: {e}")
        db.session.rollback()
        return api_response(message="Failed to delete guide", status=500)

@api.route('/delete-guide', methods=['POST'])
@login_required
def delete_guide_post():
    """Delete marking guide via POST (for frontend compatibility)."""
    try:
        data = request.get_json()
        if not data or 'guide_id' not in data:
            return api_response(message="Guide ID is required", status=400)
        
        guide_id = data['guide_id']
        guide = MarkingGuide.query.filter_by(
            id=guide_id, 
            user_id=current_user.id
        ).first()
        
        if not guide:
            return api_response(message="Guide not found", status=404)
        
        db.session.delete(guide)
        db.session.commit()
        
        return api_response(message="Guide deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete guide: {e}")
        db.session.rollback()
        return api_response(message="Failed to delete guide", status=500)

# ============================================================================
# SUBMISSIONS API
# ============================================================================

@api.route('/submissions', methods=['GET'])
@login_required
def get_submissions():
    """Get all submissions for current user."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        submissions = Submission.query.filter_by(
            user_id=current_user.id
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        data = {
            'submissions': [{
                'id': sub.id,
                'filename': sub.filename,
                'status': sub.status,
                'created_at': sub.created_at.isoformat(),
                'updated_at': sub.updated_at.isoformat(),
                'has_results': bool(sub.grading_results)
            } for sub in submissions.items],
            'pagination': {
                'page': submissions.page,
                'pages': submissions.pages,
                'per_page': submissions.per_page,
                'total': submissions.total
            }
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get submissions: {e}")
        return api_response(message="Failed to retrieve submissions", status=500)

@api.route('/submissions/<submission_id>', methods=['GET'])
@login_required
def get_submission(submission_id):
    """Get specific submission."""
    try:
        submission = Submission.query.filter_by(
            id=submission_id, 
            user_id=current_user.id
        ).first()
        
        if not submission:
            return api_response(message="Submission not found", status=404)
        
        data = {
            'id': submission.id,
            'filename': submission.filename,
            'status': submission.status,
            'extracted_text': submission.extracted_text,
            'created_at': submission.created_at.isoformat(),
            'updated_at': submission.updated_at.isoformat()
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get submission {submission_id}: {e}")
        return api_response(message="Failed to retrieve submission", status=500)

# ============================================================================
# PROCESSING API
# ============================================================================

@api.route('/process', methods=['POST'])
@login_required
def process_submission():
    """Process submission with marking guide."""
    try:
        data = request.get_json()
        
        guide_id = data.get('guide_id')
        submission_id = data.get('submission_id')
        
        if not guide_id or not submission_id:
            return api_response(
                message="Both guide_id and submission_id are required", 
                status=400
            )
        
        # Verify ownership
        guide = MarkingGuide.query.filter_by(
            id=guide_id, 
            user_id=current_user.id
        ).first()
        submission = Submission.query.filter_by(
            id=submission_id, 
            user_id=current_user.id
        ).first()
        
        if not guide or not submission:
            return api_response(
                message="Guide or submission not found", 
                status=404
            )
        
        # Create processing request
        processing_request = ProcessingRequest(
            guide_id=guide_id,
            submission_id=submission_id,
            user_id=current_user.id,
            options=data.get('options', {})
        )
        
        # Process asynchronously (in a real app, you'd use Celery or similar)
        import asyncio
        result = asyncio.run(core_service.process_submission(processing_request))
        
        if result.success:
            return api_response({
                'result_id': result.result_id,
                'score': result.score,
                'feedback': result.feedback,
                'processing_time': result.processing_time,
                'metadata': result.metadata
            }, message="Processing completed successfully")
        else:
            return api_response(
                message=f"Processing failed: {result.error}", 
                status=500
            )
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return api_response(message="Processing failed", status=500)

# ============================================================================
# RESULTS API
# ============================================================================

@api.route('/results', methods=['GET'])
@login_required
def get_results():
    """Get grading results for current user."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        results = GradingResult.query.filter_by(
            user_id=current_user.id
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        data = {
            'results': [{
                'id': result.id,
                'submission_id': result.submission_id,
                'guide_id': result.marking_guide_id,
                'total_score': result.total_score,
                'max_score': result.max_score,
                'percentage': (result.total_score / result.max_score * 100) if result.max_score > 0 else 0,
                'feedback': result.feedback,
                'created_at': result.created_at.isoformat()
            } for result in results.items],
            'pagination': {
                'page': results.page,
                'pages': results.pages,
                'per_page': results.per_page,
                'total': results.total
            }
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        return api_response(message="Failed to retrieve results", status=500)

@api.route('/results/<result_id>', methods=['GET'])
@login_required
def get_result(result_id):
    """Get specific grading result."""
    try:
        result = GradingResult.query.filter_by(
            id=result_id, 
            user_id=current_user.id
        ).first()
        
        if not result:
            return api_response(message="Result not found", status=404)
        
        data = {
            'id': result.id,
            'submission_id': result.submission_id,
            'guide_id': result.marking_guide_id,
            'total_score': result.total_score,
            'max_score': result.max_score,
            'percentage': (result.total_score / result.max_score * 100) if result.max_score > 0 else 0,
            'feedback': result.feedback,
            'detailed_results': result.detailed_results,
            'processing_metadata': result.processing_metadata,
            'created_at': result.created_at.isoformat()
        }
        
        return api_response(data)
        
    except Exception as e:
        logger.error(f"Failed to get result {result_id}: {e}")
        return api_response(message="Failed to retrieve result", status=500)

# ============================================================================
# CACHE STATS API
# ============================================================================

@api.route('/cache/stats', methods=['GET'])
@login_required
def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = {}
        
        if hasattr(core_service, 'get_cache_stats'):
            stats.update(core_service.get_cache_stats())
        
        try:
            from src.performance.query_cache import get_cache_stats as get_query_cache_stats
            stats['query_cache'] = get_query_cache_stats()
        except ImportError:
            pass
        
        try:
            from src.performance.optimization_manager import OptimizationManager
            opt_manager = OptimizationManager()
            stats['optimization'] = opt_manager.get_cache_stats() if hasattr(opt_manager, 'get_cache_stats') else {}
        except ImportError:
            pass
        
        if not stats:
            stats = {
                'memory_cache': {'hits': 0, 'misses': 0, 'size': 0},
                'query_cache': {'hits': 0, 'misses': 0, 'size': 0},
                'hit_rate': 0.0,
                'total_requests': 0
            }
        
        return api_response(data=stats, message="Cache statistics retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return api_response(message="Failed to retrieve cache statistics", status=500)

# ============================================================================
# HEALTH CHECK API
# ============================================================================

@api.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Check core service
        service_health = core_service.get_health_status()
        
        return api_response({
            'api': 'healthy',
            'database': 'healthy',
            'core_service': service_health,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return api_response(
            message="Service unhealthy", 
            status=503
        )

# Register error handlers
api.register_error_handler(400, handle_api_error)
api.register_error_handler(404, handle_api_error)
api.register_error_handler(500, handle_api_error)
api.register_error_handler(SQLAlchemyError, handle_api_error)