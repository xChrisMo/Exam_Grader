"""Upload API endpoints with content validation and duplicate detection.

This module provides REST API endpoints for file uploads with integrated
content validation, duplicate detection, and enhanced error handling.
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_wtf.csrf import validate_csrf
from werkzeug.utils import secure_filename
import os
from typing import Dict, Any

from src.services.enhanced_upload_service import EnhancedUploadService
from src.services.consolidated_ocr_service import ConsolidatedOCRService as OCRService
from src.database.models import db, User, MarkingGuide
from utils.logger import logger
from utils.input_sanitizer import InputSanitizer

# Create blueprint
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# Initialize services
ocr_service = None
upload_service = None
input_sanitizer = InputSanitizer()

def init_upload_services(app):
    """Initialize upload services with app context.
    
    Args:
        app: Flask application instance
    """
    global ocr_service, upload_service
    
    with app.app_context():
        try:
            # Initialize OCR service
            ocr_service = OCRService()
            
            # Initialize upload service
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            upload_service = EnhancedUploadService(upload_folder, ocr_service)
            
            logger.info("Upload services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize upload services: {e}")
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

@upload_bp.route('/submission', methods=['POST'])
def upload_submission():
    """Upload a submission file with duplicate detection.
    
    Expected form data:
    - file: The uploaded file
    - marking_guide_id: ID of the marking guide
    - student_name: Name of the student
    - student_id: Student ID
    - check_duplicates: Optional, whether to check for duplicates (default: true)
    
    Returns:
        JSON response with upload result
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
        
        # Validate CSRF token
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({
                'success': False,
                'error': 'CSRF token validation failed',
                'code': 'CSRF_ERROR'
            }), 400
        
        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'code': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400
        
        # Get form data
        marking_guide_id = request.form.get('marking_guide_id')
        student_name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        check_duplicates = request.form.get('check_duplicates', 'true').lower() == 'true'
        
        # Validate required fields
        if not marking_guide_id:
            return jsonify({
                'success': False,
                'error': 'Marking guide ID is required',
                'code': 'MISSING_GUIDE_ID'
            }), 400
        
        if not student_name:
            return jsonify({
                'success': False,
                'error': 'Student name is required',
                'code': 'MISSING_STUDENT_NAME'
            }), 400
        
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'Student ID is required',
                'code': 'MISSING_STUDENT_ID'
            }), 400
        
        # Sanitize inputs
        student_name = input_sanitizer.sanitize_text(student_name)
        student_id = input_sanitizer.sanitize_text(student_id)
        
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
        
        # Upload submission
        result = upload_service.upload_submission(
            file=file,
            user_id=user_id,
            marking_guide_id=marking_guide_id,
            student_name=student_name,
            student_id=student_id,
            check_duplicates=check_duplicates
        )
        
        # Determine response status code
        if result['success']:
            status_code = 201  # Created
        elif result.get('code') == 'DUPLICATE_CONTENT':
            status_code = 409  # Conflict
        elif result.get('code') in ['NO_FILE', 'INVALID_FILE_TYPE', 'FILE_TOO_LARGE']:
            status_code = 400  # Bad Request
        else:
            status_code = 500  # Internal Server Error
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in upload_submission endpoint: {e}")
        
        # Check if it's a network-related error from OCR service
        error_message = str(e)
        if any(keyword in error_message.lower() for keyword in ['network error', 'connection', 'timeout', 'aborted']):
            return jsonify({
                'success': False,
                'error': f'Network error during document processing: {error_message}',
                'code': 'NETWORK_ERROR',
                'details': 'Please check your internet connection and try again. The OCR service may be temporarily unavailable.'
            }), 400
        elif 'ocr' in error_message.lower():
            return jsonify({
                'success': False,
                'error': f'Document processing failed: {error_message}',
                'code': 'OCR_ERROR',
                'details': 'There was an issue processing your document. Please try again or contact support if the problem persists.'
            }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'code': 'INTERNAL_ERROR'
            }), 500

@upload_bp.route('/marking-guide', methods=['POST'])
def upload_marking_guide():
    """Upload a marking guide file with duplicate detection.
    
    Expected form data:
    - file: The uploaded file
    - title: Title for the marking guide
    - check_duplicates: Optional, whether to check for duplicates (default: true)
    
    Returns:
        JSON response with upload result
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
        
        # Validate CSRF token
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({
                'success': False,
                'error': 'CSRF token validation failed',
                'code': 'CSRF_ERROR'
            }), 400
        
        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'code': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400
        
        # Get form data
        title = request.form.get('title', '').strip()
        check_duplicates = request.form.get('check_duplicates', 'true').lower() == 'true'
        
        # Validate required fields
        if not title:
            return jsonify({
                'success': False,
                'error': 'Title is required',
                'code': 'MISSING_TITLE'
            }), 400
        
        # Sanitize inputs
        title = input_sanitizer.sanitize_text(title)
        
        # Upload marking guide
        result = upload_service.upload_marking_guide(
            file=file,
            user_id=user_id,
            title=title,
            check_duplicates=check_duplicates
        )
        
        # Determine response status code
        if result['success']:
            status_code = 201  # Created
        elif result.get('code') == 'DUPLICATE_CONTENT':
            status_code = 409  # Conflict
        elif result.get('code') in ['NO_FILE', 'INVALID_FILE_TYPE', 'FILE_TOO_LARGE']:
            status_code = 400  # Bad Request
        else:
            status_code = 500  # Internal Server Error
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in upload_marking_guide endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@upload_bp.route('/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if uploaded content would be a duplicate without saving.
    
    Expected form data:
    - file: The file to check
    - type: 'submission' or 'marking_guide'
    - marking_guide_id: Required for submission type
    
    Returns:
        JSON response with duplicate check result
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
        
        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'code': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400
        
        # Get form data
        check_type = request.form.get('type', '').strip().lower()
        marking_guide_id = request.form.get('marking_guide_id')
        
        # Validate type
        if check_type not in ['submission', 'marking_guide']:
            return jsonify({
                'success': False,
                'error': 'Type must be "submission" or "marking_guide"',
                'code': 'INVALID_TYPE'
            }), 400
        
        # Validate file
        validation_result = upload_service.validate_file_upload(file)
        if not validation_result['success']:
            return jsonify(validation_result), 400
        
        file_type = validation_result['file_type']
        
        # Save file temporarily for content extraction
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Check for duplicates
            result = upload_service.content_validator.validate_and_check_duplicates(
                temp_path, file_type, user_id, check_type, marking_guide_id
            )
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return jsonify(result), 200
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        logger.error(f"Error in check_duplicate endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@upload_bp.route('/validate-file', methods=['POST'])
def validate_file():
    """Validate uploaded file without saving or checking duplicates.
    
    Expected form data:
    - file: The file to validate
    
    Returns:
        JSON response with validation result
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
        
        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'code': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400
        
        # Validate file
        result = upload_service.validate_file_upload(file)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error in validate_file endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@upload_bp.route('/cleanup-temp', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary files (admin only).
    
    Returns:
        JSON response with cleanup result
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
        
        # Check if user is admin (you may want to implement proper role checking)
        user = db.session.query(User).filter(User.id == user_id).first()
        if not user or not getattr(user, 'is_admin', False):
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        # Get max age parameter
        max_age_hours = request.json.get('max_age_hours', 24) if request.is_json else 24
        
        # Clean up temp files
        result = upload_service.cleanup_temp_files(max_age_hours)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in cleanup_temp_files endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Get list of supported file formats.
    
    Returns:
        JSON response with supported formats
    """
    try:
        return jsonify({
            'success': True,
            'supported_formats': list(upload_service.allowed_extensions),
            'max_file_size_mb': 50,
            'description': {
                'pdf': 'Portable Document Format',
                'docx': 'Microsoft Word Document (2007+)',
                'doc': 'Microsoft Word Document (Legacy)',
                'txt': 'Plain Text File',
                'jpg': 'JPEG Image',
                'jpeg': 'JPEG Image',
                'png': 'PNG Image',
                'tiff': 'TIFF Image',
                'bmp': 'Bitmap Image'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_supported_formats endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

# Error handlers
@upload_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': 'File size exceeds maximum allowed size (50MB)',
        'code': 'FILE_TOO_LARGE'
    }), 413

@upload_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request error."""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'code': 'BAD_REQUEST'
    }), 400

@upload_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server error."""
    logger.error(f"Internal server error in upload endpoints: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500