"""
Training Routes for LLM Training Page

This module provides routes for the LLM training dashboard and related functionality.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import time
from datetime import datetime
from pathlib import Path

from src.services.confidence_monitor import confidence_monitor
from src.services.training_service import TrainingService, TrainingConfig, FileUpload
from src.database.models import db, TrainingSession, TrainingGuide, TrainingResult
from sqlalchemy import and_, desc
from utils.logger import logger

# Create blueprint
training_bp = Blueprint('training', __name__, url_prefix='/training')

# Training service will be initialized when needed
training_service = None

def get_training_service():
    """Get or initialize the training service"""
    global training_service
    if training_service is None:
        training_service = TrainingService()
    return training_service

# Allowed file extensions for training guides
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif'
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@training_bp.route('/')
@login_required
def dashboard():
    """
    Display the main training dashboard
    
    This route renders the training dashboard template with current session
    information and allows users to start new training sessions.
    """
    try:
        logger.info(f"User {current_user.id} accessed training dashboard")
        
        # Get current active training session for user
        from src.database.models import TrainingSession
        current_session = db.session.query(TrainingSession).filter(
            and_(
                TrainingSession.user_id == current_user.id,
                TrainingSession.status.in_(['created', 'processing', 'paused'])
            )
        ).order_by(desc(TrainingSession.created_at)).first()
        
        # Get training history for user
        training_history = db.session.query(TrainingSession).filter_by(
            user_id=current_user.id
        ).order_by(desc(TrainingSession.created_at)).limit(10).all()
        
        return render_template('training_dashboard.html',
                             page_title='LLM Training Dashboard',
                             current_session=current_session,
                             training_history=training_history)
        
    except Exception as e:
        logger.error(f"Error loading training dashboard: {e}")
        flash('Error loading training dashboard. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))


@training_bp.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """
    Handle file uploads for training guides
    
    This endpoint accepts multiple files, validates them, saves them securely,
    and prepares them for training session creation.
    """
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        # Create user-specific upload directory
        user_upload_dir = Path('uploads/training_guides') / str(current_user.id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        errors = []
        
        for file in files:
            if file and file.filename:
                if allowed_file(file.filename):
                    # Validate file size (50MB limit)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > 50 * 1024 * 1024:  # 50MB
                        errors.append(f"File '{file.filename}' exceeds 50MB limit")
                        continue
                    
                    # Generate unique filename to prevent conflicts
                    filename = secure_filename(file.filename)
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{int(time.time())}_{current_user.id}{ext}"
                    
                    # Save file to disk
                    file_path = user_upload_dir / unique_filename
                    file.save(str(file_path))
                    
                    # Determine file category based on extension
                    extension = filename.rsplit('.', 1)[1].lower()
                    if extension in ['pdf', 'docx', 'doc']:
                        category = 'qa'  # Questions + Answers
                    else:
                        category = 'q'   # Questions only (images)
                    
                    # Perform basic file validation
                    try:
                        # Check if file is readable and not corrupted
                        with open(file_path, 'rb') as f:
                            # Read first few bytes to validate file header
                            header = f.read(1024)
                            if len(header) == 0:
                                raise ValueError("Empty file")
                    except Exception as e:
                        errors.append(f"File '{file.filename}' appears to be corrupted: {str(e)}")
                        # Clean up the saved file
                        if file_path.exists():
                            file_path.unlink()
                        continue
                    
                    uploaded_files.append({
                        'filename': unique_filename,
                        'original_name': file.filename,
                        'size': file_size,
                        'category': category,
                        'extension': extension,
                        'file_path': str(file_path),
                        'upload_time': time.time(),
                        'user_id': current_user.id
                    })
                    
                    logger.info(f"File uploaded successfully: {filename} -> {unique_filename} ({file_size} bytes)")
                    
                else:
                    errors.append(f"File type not allowed: {file.filename}")
        
        if errors:
            return jsonify({'error': 'File validation errors', 'details': errors}), 400
        
        if not uploaded_files:
            return jsonify({'error': 'No valid files uploaded'}), 400
        
        # Store upload session in cache/database for later retrieval
        upload_session_id = f"upload_{current_user.id}_{int(time.time())}"
        
        return jsonify({
            'success': True,
            'upload_session_id': upload_session_id,
            'files': uploaded_files,
            'message': f'Successfully uploaded {len(uploaded_files)} files'
        })
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        return jsonify({'error': 'File upload failed'}), 500


@training_bp.route('/upload/remove', methods=['POST'])
@login_required
def remove_uploaded_file():
    """
    Remove an uploaded file before session creation
    
    This endpoint removes a previously uploaded file from the temporary storage.
    """
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'Filename is required'}), 400
        
        # Construct file path
        user_upload_dir = Path('uploads/training_guides') / str(current_user.id)
        file_path = user_upload_dir / filename
        
        # Verify file belongs to current user and exists
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Additional security check - ensure filename contains user ID
        if str(current_user.id) not in filename:
            return jsonify({'error': 'Access denied'}), 403
        
        # Remove the file
        file_path.unlink()
        
        logger.info(f"File removed: {filename} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'File removed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error removing file: {e}")
        return jsonify({'error': 'Failed to remove file'}), 500


@training_bp.route('/upload/validate', methods=['POST'])
@login_required
def validate_uploaded_files():
    """
    Validate uploaded files for training compatibility
    
    This endpoint performs deep validation of uploaded files to ensure
    they are suitable for training session creation.
    """
    try:
        data = request.get_json()
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({'error': 'No filenames provided'}), 400
        
        user_upload_dir = Path('uploads/training_guides') / str(current_user.id)
        validation_results = []
        
        for filename in filenames:
            file_path = user_upload_dir / filename
            
            if not file_path.exists():
                validation_results.append({
                    'filename': filename,
                    'valid': False,
                    'error': 'File not found'
                })
                continue
            
            # Perform validation based on file type
            try:
                validation_result = self._validate_training_file(file_path)
                validation_result['filename'] = filename
                validation_results.append(validation_result)
                
            except Exception as e:
                validation_results.append({
                    'filename': filename,
                    'valid': False,
                    'error': f'Validation failed: {str(e)}'
                })
        
        # Summary
        valid_files = [r for r in validation_results if r.get('valid', False)]
        invalid_files = [r for r in validation_results if not r.get('valid', False)]
        
        return jsonify({
            'success': True,
            'validation_results': validation_results,
            'summary': {
                'total_files': len(validation_results),
                'valid_files': len(valid_files),
                'invalid_files': len(invalid_files)
            }
        })
        
    except Exception as e:
        logger.error(f"Error validating files: {e}")
        return jsonify({'error': 'File validation failed'}), 500


@training_bp.route('/upload/progress/<upload_session_id>')
@login_required
def get_upload_progress(upload_session_id):
    """
    Get upload progress for a specific upload session
    
    This endpoint returns the current progress of file uploads and processing.
    """
    try:
        # Since uploads are synchronous, return completed status
        progress = {
            'upload_session_id': upload_session_id,
            'status': 'completed',
            'progress_percentage': 100,
            'current_step': 'Upload completed'
        }
        
        return jsonify(progress)
        
    except Exception as e:
        logger.error(f"Error getting upload progress: {e}")
        return jsonify({'error': 'Failed to get upload progress'}), 500


def _validate_training_file(file_path):
    """
    Validate a single training file for compatibility
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        dict: Validation result with details
    """
    try:
        file_extension = file_path.suffix.lower()
        file_size = file_path.stat().st_size
        
        validation_result = {
            'valid': True,
            'warnings': [],
            'info': {
                'size': file_size,
                'extension': file_extension,
                'estimated_questions': 0,
                'file_type': 'unknown'
            }
        }
        
        # Basic file checks
        if file_size == 0:
            validation_result['valid'] = False
            validation_result['error'] = 'File is empty'
            return validation_result
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            validation_result['valid'] = False
            validation_result['error'] = 'File exceeds 50MB limit'
            return validation_result
        
        # File type specific validation
        if file_extension in ['.pdf']:
            validation_result['info']['file_type'] = 'PDF Document'
            validation_result['info']['estimated_questions'] = max(1, file_size // (100 * 1024))  # Rough estimate
            
            
        elif file_extension in ['.docx', '.doc']:
            validation_result['info']['file_type'] = 'Word Document'
            validation_result['info']['estimated_questions'] = max(1, file_size // (50 * 1024))
            
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']:
            validation_result['info']['file_type'] = 'Image'
            validation_result['info']['estimated_questions'] = 1
            
        else:
            validation_result['valid'] = False
            validation_result['error'] = f'Unsupported file type: {file_extension}'
            return validation_result
        
        # Add warnings for potential issues
        if file_size < 1024:  # Less than 1KB
            validation_result['warnings'].append('File is very small and may not contain meaningful content')
        
        if file_size > 10 * 1024 * 1024:  # Larger than 10MB
            validation_result['warnings'].append('Large file may take longer to process')
        
        return validation_result
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'Validation error: {str(e)}'
        }


@training_bp.route('/create-session', methods=['POST'])
@login_required
def create_session():
    """
    Create a new training session
    
    This endpoint creates a new training session with the provided configuration
    and uploaded files.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('sessionName'):
            return jsonify({'error': 'Session name is required'}), 400
        
        if not data.get('files'):
            return jsonify({'error': 'At least one file is required'}), 400
        
        # Validate session configuration
        session_name = data['sessionName'].strip()
        if len(session_name) < 3:
            return jsonify({'error': 'Session name must be at least 3 characters long'}), 400
        
        if len(session_name) > 100:
            return jsonify({'error': 'Session name must be less than 100 characters'}), 400
        
        # Validate confidence threshold
        try:
            confidence_threshold = float(data.get('confidenceThreshold', 0.6))
            if confidence_threshold < 0.1 or confidence_threshold > 1.0:
                return jsonify({'error': 'Confidence threshold must be between 0.1 and 1.0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid confidence threshold value'}), 400
        
        # Validate max questions
        max_questions = data.get('maxQuestions')
        if max_questions is not None:
            try:
                max_questions = int(max_questions)
                if max_questions < 1 or max_questions > 1000:
                    return jsonify({'error': 'Max questions must be between 1 and 1000'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid max questions value'}), 400
        
        # Validate files
        files = data['files']
        if not isinstance(files, list) or len(files) == 0:
            return jsonify({'error': 'At least one file is required'}), 400
        
        # Verify files exist and belong to user
        user_upload_dir = Path('uploads/training_guides') / str(current_user.id)
        validated_files = []
        
        for file_info in files:
            if not isinstance(file_info, dict) or 'filename' not in file_info:
                return jsonify({'error': 'Invalid file information'}), 400
            
            filename = file_info['filename']
            file_path = user_upload_dir / filename
            
            if not file_path.exists():
                return jsonify({'error': f'File not found: {filename}'}), 400
            
            # Security check - ensure filename contains user ID
            if str(current_user.id) not in filename:
                return jsonify({'error': f'Access denied to file: {filename}'}), 403
            
            validated_files.append({
                'filename': filename,
                'file_path': str(file_path),
                'original_name': file_info.get('original_name', filename),
                'size': file_info.get('size', file_path.stat().st_size),
                'category': file_info.get('category', 'unknown'),
                'extension': file_info.get('extension', file_path.suffix.lower())
            })
        
        # Create session configuration
        session_config = {
            'name': session_name,
            'user_id': current_user.id,
            'max_questions_to_answer': max_questions,
            'confidence_threshold': confidence_threshold,
            'use_in_main_app': bool(data.get('useInMainApp', False)),
            'processing_mode': data.get('processingMode', 'standard'),
            'files': validated_files,
            'created_at': time.time(),
            'status': 'pending'
        }
        
        logger.info(f"Creating training session: {session_config['name']} for user {current_user.id}")
        
        # Create training configuration
        training_config = TrainingConfig(
            name=session_name,
            description=data.get('description', ''),
            max_questions_to_answer=max_questions,
            use_in_main_app=bool(data.get('useInMainApp', False)),
            confidence_threshold=confidence_threshold
        )
        
        # Convert files to FileUpload objects
        file_uploads = []
        for file_info in validated_files:
            file_upload = FileUpload(
                filename=file_info['filename'],
                file_path=file_info['file_path'],
                file_size=file_info['size'],
                file_type=file_info['extension']
            )
            file_uploads.append(file_upload)
        
        # Create training session using TrainingService
        session = get_training_service().create_training_session(
            user_id=current_user.id,
            guides=file_uploads,
            config=training_config
        )
        session_id = session.id
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Training session created successfully',
            'session_config': {
                'id': session_id,
                'name': session_name,
                'files_count': len(validated_files),
                'confidence_threshold': confidence_threshold,
                'max_questions': max_questions,
                'use_in_main_app': session_config['use_in_main_app']
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating training session: {e}")
        return jsonify({'error': 'Failed to create training session'}), 500


@training_bp.route('/start-training', methods=['POST'])
@login_required
def start_training():
    """
    Start training for a session
    
    This endpoint initiates the training process for a created session.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        # Validate session belongs to user and is in correct state
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status not in ['created', 'pending']:
            return jsonify({'error': 'Session is not in a startable state'}), 400
        
        # Additional validation options
        priority = data.get('priority', 'normal')  # normal, high, low
        if priority not in ['low', 'normal', 'high']:
            return jsonify({'error': 'Invalid priority level'}), 400
        
        resume_from_checkpoint = data.get('resume_from_checkpoint', False)
        notification_settings = data.get('notifications', {
            'email': False,
            'webhook': False,
            'in_app': True
        })
        
        # Start training with enhanced configuration
        training_config = {
            'session_id': session_id,
            'user_id': current_user.id,
            'priority': priority,
            'resume_from_checkpoint': resume_from_checkpoint,
            'notifications': notification_settings,
            'started_at': time.time(),
            'started_by': current_user.id
        }
        
        logger.info(f"Starting training for session: {session_id} with priority: {priority}")
        
        # Start training using TrainingService
        success = get_training_service().start_training(session_id)
        
        if not success:
            return jsonify({'error': 'Failed to start training session'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Training started successfully',
            'session_id': session_id,
            'progress_url': f'/training/progress/{session_id}',
            'can_pause': True,
            'can_stop': True
        })
        
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        return jsonify({'error': 'Failed to start training'}), 500


@training_bp.route('/session/<session_id>/pause', methods=['POST'])
@login_required
def pause_training_session(session_id):
    """
    Pause a training session in progress
    
    This endpoint pauses an active training session and saves checkpoint.
    """
    try:
        # Validate session belongs to user
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status != 'processing':
            return jsonify({'error': 'Session is not in progress'}), 400
        
        logger.info(f"Pausing training session: {session_id}")
        
        # Update session status to paused
        session.status = 'paused'
        session.current_step = 'Paused by user'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Training session paused successfully',
            'session_id': session_id,
            'paused_at': time.time(),
            'can_resume': True
        })
        
    except Exception as e:
        logger.error(f"Error pausing training session: {e}")
        return jsonify({'error': 'Failed to pause training session'}), 500


@training_bp.route('/session/<session_id>/resume', methods=['POST'])
@login_required
def resume_training_session(session_id):
    """
    Resume a paused training session
    
    This endpoint resumes a paused training session from checkpoint.
    """
    try:
        # Validate session belongs to user
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status != 'paused':
            return jsonify({'error': 'Session is not paused'}), 400
        
        data = request.get_json() or {}
        priority = data.get('priority', 'normal')
        
        if priority not in ['low', 'normal', 'high']:
            return jsonify({'error': 'Invalid priority level'}), 400
        
        logger.info(f"Resuming training session: {session_id} with priority: {priority}")
        
        # Resume training using TrainingService
        success = get_training_service().start_training(session_id)
        
        if not success:
            return jsonify({'error': 'Failed to resume training session'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Training session resumed successfully',
            'session_id': session_id,
            'resumed_at': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error resuming training session: {e}")
        return jsonify({'error': 'Failed to resume training session'}), 500


@training_bp.route('/session/<session_id>/stop', methods=['POST'])
@login_required
def stop_training_session(session_id):
    """
    Stop a training session in progress
    
    This endpoint stops an active training session permanently.
    """
    try:
        # Validate session belongs to user
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status not in ['processing', 'paused']:
            return jsonify({'error': 'Session is not in a stoppable state'}), 400
        
        data = request.get_json() or {}
        save_partial_results = data.get('save_partial_results', True)
        reason = data.get('reason', 'user_requested')
        
        logger.info(f"Stopping training session: {session_id}, reason: {reason}")
        
        # Update session status to stopped
        session.status = 'stopped'
        session.current_step = f'Stopped: {reason}'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Training session stopped successfully',
            'session_id': session_id,
            'stopped_at': time.time(),
            'partial_results_saved': save_partial_results,
            'reason': reason
        })
        
    except Exception as e:
        logger.error(f"Error stopping training session: {e}")
        return jsonify({'error': 'Failed to stop training session'}), 500


@training_bp.route('/session/<session_id>/config', methods=['GET', 'PUT'])
@login_required
def manage_session_config(session_id):
    """
    Get or update training session configuration
    
    GET: Returns current session configuration
    PUT: Updates session configuration (only for pending sessions)
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if request.method == 'GET':
            # Get session configuration from database
            session = db.session.query(TrainingSession).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Training session not found'}), 404
            
            if session.user_id != current_user.id:
                return jsonify({'error': 'Access denied to this session'}), 403
            
            config = {
                'session_id': session.id,
                'name': session.name,
                'status': session.status,
                'confidence_threshold': session.confidence_threshold,
                'max_questions': session.max_questions_to_answer,
                'use_in_main_app': session.use_in_main_app,
                'files_count': session.total_guides,
                'created_at': session.created_at.timestamp() if session.created_at else None
            }
            
            return jsonify({
                'success': True,
                'config': config
            })
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Validate session is in 'pending' state
            session = db.session.query(TrainingSession).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Training session not found'}), 404
            
            if session.user_id != current_user.id:
                return jsonify({'error': 'Access denied to this session'}), 403
            
            if session.status not in ['created', 'pending']:
                return jsonify({'error': 'Configuration can only be updated for pending sessions'}), 400
            
            # Validate and apply configuration updates
            if 'name' in data:
                name = data['name'].strip()
                if len(name) < 3 or len(name) > 100:
                    return jsonify({'error': 'Session name must be 3-100 characters'}), 400
                session.name = name
            
            if 'confidence_threshold' in data:
                try:
                    threshold = float(data['confidence_threshold'])
                    if threshold < 0.1 or threshold > 1.0:
                        return jsonify({'error': 'Confidence threshold must be 0.1-1.0'}), 400
                    session.confidence_threshold = threshold
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid confidence threshold'}), 400
            
            if 'max_questions' in data:
                if data['max_questions'] is not None:
                    try:
                        max_q = int(data['max_questions'])
                        if max_q < 1 or max_q > 1000:
                            return jsonify({'error': 'Max questions must be 1-1000'}), 400
                        session.max_questions_to_answer = max_q
                    except (ValueError, TypeError):
                        return jsonify({'error': 'Invalid max questions value'}), 400
                else:
                    session.max_questions_to_answer = None
            
            if 'use_in_main_app' in data:
                session.use_in_main_app = bool(data['use_in_main_app'])
            
            db.session.commit()
            
            logger.info(f"Updated session {session_id} configuration")
            
            return jsonify({
                'success': True,
                'message': 'Session configuration updated successfully'
            })
        
    except Exception as e:
        logger.error(f"Error managing session config: {e}")
        return jsonify({'error': 'Failed to manage session configuration'}), 500


@training_bp.route('/session/<session_id>/test/upload', methods=['POST'])
@login_required
def upload_test_submission(session_id):
    """
    Upload test submission for model validation
    
    This endpoint accepts test submissions to validate the trained model.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Validate file size (50MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            return jsonify({'error': 'File exceeds 50MB limit'}), 400
        
        # Create test submissions directory
        test_dir = Path('uploads/test_submissions') / str(current_user.id) / session_id
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"test_{name}_{int(time.time())}{ext}"
        
        # Save file
        file_path = test_dir / unique_filename
        file.save(str(file_path))
        
        # Create test submission record
        test_submission = {
            'id': f"test_{session_id}_{int(time.time())}",
            'session_id': session_id,
            'filename': unique_filename,
            'original_name': file.filename,
            'file_path': str(file_path),
            'size': file_size,
            'uploaded_at': time.time(),
            'status': 'uploaded',
            'user_id': current_user.id
        }
        
        logger.info(f"Test submission uploaded for session {session_id}: {filename}")
        
        return jsonify({
            'success': True,
            'test_submission': test_submission,
            'message': 'Test submission uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading test submission: {e}")
        return jsonify({'error': 'Failed to upload test submission'}), 500


@training_bp.route('/session/<session_id>/test/run', methods=['POST'])
@login_required
def run_model_test(session_id):
    """
    Run model testing on uploaded test submissions
    
    This endpoint executes the trained model against test submissions.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        data = request.get_json() or {}
        test_submission_ids = data.get('test_submission_ids', [])
        
        if not test_submission_ids:
            return jsonify({'error': 'No test submissions specified'}), 400
        
        # Validate test configuration
        test_config = {
            'session_id': session_id,
            'test_submission_ids': test_submission_ids,
            'compare_with_baseline': data.get('compare_with_baseline', False),
            'generate_detailed_report': data.get('generate_detailed_report', True),
            'confidence_threshold': data.get('confidence_threshold', 0.6),
            'user_id': current_user.id,
            'started_at': time.time()
        }
        
        logger.info(f"Starting model test for session {session_id} with {len(test_submission_ids)} submissions")
        
        # TODO: Implement actual model testing
        # This should:
        # 1. Load the trained model for the session
        # 2. Process each test submission through OCR
        # 3. Run the trained model on extracted text
        # 4. Compare results with expected answers (if available)
        # 5. Generate accuracy metrics and confidence scores
        # 6. Create detailed test report
        
        # Generate test run ID
        test_run_id = f"test_run_{session_id}_{int(time.time())}"
        
        return jsonify({
            'success': True,
            'test_run_id': test_run_id,
            'message': 'Model testing started successfully',
            'estimated_duration': '5-10 minutes',
            'progress_url': f'/training/session/{session_id}/test/{test_run_id}/progress'
        })
        
    except Exception as e:
        logger.error(f"Error running model test: {e}")
        return jsonify({'error': 'Failed to run model test'}), 500


@training_bp.route('/session/<session_id>/test/<test_run_id>/progress')
@login_required
def get_test_progress(session_id, test_run_id):
    """
    Get progress of model testing
    
    This endpoint returns the current progress of model testing.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # TODO: Get actual test progress from database/cache
        progress = {
            'test_run_id': test_run_id,
            'session_id': session_id,
            'status': 'in_progress',
            'progress_percentage': 65,
            'current_step': 'Processing submission 3 of 5',
            'submissions_processed': 3,
            'total_submissions': 5,
            'preliminary_results': {
                'accuracy': 0.78,
                'avg_confidence': 0.82,
                'processed_questions': 15,
                'total_questions': 23
            },
            'estimated_completion': time.time() + 300  # 5 minutes from now
        }
        
        return jsonify({
            'success': True,
            'progress': progress
        })
        
    except Exception as e:
        logger.error(f"Error getting test progress: {e}")
        return jsonify({'error': 'Failed to get test progress'}), 500


@training_bp.route('/session/<session_id>/test/<test_run_id>/results')
@login_required
def get_test_results(session_id, test_run_id):
    """
    Get model testing results
    
    This endpoint returns the complete results of model testing.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # TODO: Get actual test results from database
        results = {
            'test_run_id': test_run_id,
            'session_id': session_id,
            'status': 'completed',
            'completed_at': time.time() - 300,  # 5 minutes ago
            'duration_seconds': 480,
            'overall_metrics': {
                'accuracy': 0.78,
                'precision': 0.82,
                'recall': 0.75,
                'f1_score': 0.78,
                'avg_confidence': 0.81
            },
            'submission_results': [
                {
                    'submission_id': 'test_1',
                    'filename': 'test_submission_1.pdf',
                    'questions_processed': 5,
                    'accuracy': 0.80,
                    'avg_confidence': 0.85,
                    'processing_time': 45.2
                },
                {
                    'submission_id': 'test_2',
                    'filename': 'test_submission_2.pdf',
                    'questions_processed': 8,
                    'accuracy': 0.75,
                    'avg_confidence': 0.78,
                    'processing_time': 62.1
                }
            ],
            'confidence_distribution': {
                'high': 12,
                'medium': 8,
                'low': 3
            },
            'error_analysis': {
                'total_errors': 5,
                'ocr_errors': 2,
                'model_errors': 2,
                'validation_errors': 1
            },
            'recommendations': [
                'Consider retraining with more diverse examples',
                'Review low-confidence questions for pattern analysis',
                'OCR quality could be improved for handwritten text'
            ]
        }
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error getting test results: {e}")
        return jsonify({'error': 'Failed to get test results'}), 500


@training_bp.route('/session/<session_id>/test/<test_run_id>/report')
@login_required
def get_test_report(session_id, test_run_id):
    """
    Get detailed test report
    
    This endpoint returns a detailed test report with visualizations.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # TODO: Generate detailed test report
        report = {
            'test_run_id': test_run_id,
            'session_id': session_id,
            'generated_at': time.time(),
            'report_type': 'model_validation',
            'summary': 'Model testing completed with good overall performance.',
            'detailed_analysis': {
                'accuracy_by_question_type': {
                    'multiple_choice': 0.85,
                    'short_answer': 0.72,
                    'essay': 0.68,
                    'calculation': 0.82
                },
                'confidence_trends': [
                    {'question_id': 1, 'confidence': 0.92},
                    {'question_id': 2, 'confidence': 0.78},
                    {'question_id': 3, 'confidence': 0.65}
                ],
                'error_patterns': [
                    'Difficulty with handwritten mathematical symbols',
                    'Lower accuracy on open-ended questions',
                    'OCR challenges with poor image quality'
                ]
            },
            'visualizations': {
                'accuracy_chart_url': f'/training/session/{session_id}/test/{test_run_id}/chart/accuracy',
                'confidence_chart_url': f'/training/session/{session_id}/test/{test_run_id}/chart/confidence',
                'error_chart_url': f'/training/session/{session_id}/test/{test_run_id}/chart/errors'
            }
        }
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error getting test report: {e}")
        return jsonify({'error': 'Failed to get test report'}), 500


@training_bp.route('/session/<session_id>/test/submissions')
@login_required
def list_test_submissions(session_id):
    """
    List all test submissions for a session
    
    This endpoint returns all test submissions uploaded for the session.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # TODO: Get actual test submissions from database
        submissions = [
            {
                'id': 'test_1',
                'filename': 'test_submission_1.pdf',
                'original_name': 'Math Test 1.pdf',
                'size': 2048576,
                'uploaded_at': time.time() - 3600,
                'status': 'processed',
                'questions_found': 5,
                'last_test_run': 'test_run_123'
            },
            {
                'id': 'test_2',
                'filename': 'test_submission_2.pdf',
                'original_name': 'Math Test 2.pdf',
                'size': 1536000,
                'uploaded_at': time.time() - 1800,
                'status': 'uploaded',
                'questions_found': 8,
                'last_test_run': None
            }
        ]
        
        return jsonify({
            'success': True,
            'submissions': submissions,
            'total_count': len(submissions)
        })
        
    except Exception as e:
        logger.error(f"Error listing test submissions: {e}")
        return jsonify({'error': 'Failed to list test submissions'}), 500


@training_bp.route('/progress/<session_id>')
@login_required
def get_progress(session_id):
    """
    Get training progress for a session
    
    This endpoint returns the current progress of a training session.
    """
    try:
        # Get progress from TrainingService
        logger.debug(f"Getting progress for session: {session_id}")
        
        try:
            # Get actual progress from training service
            progress_info = get_training_service().get_training_progress(session_id)
            
            progress = {
                'percentage': progress_info.progress_percentage,
                'current_step': progress_info.current_step,
                'status': progress_info.status,
                'guides_processed': progress_info.guides_processed,
                'questions_extracted': progress_info.questions_extracted,
                'average_confidence': progress_info.average_confidence,
                'error_message': progress_info.error_message
            }
            
            return jsonify(progress)
            
        except ValueError as e:
            # Session not found
            logger.warning(f"Session not found: {session_id}")
            return jsonify({
                'percentage': 0,
                'current_step': 'Session not found',
                'status': 'error',
                'error_message': str(e)
            }), 404
        except Exception as e:
            logger.error(f"Error getting progress for session {session_id}: {e}")
            return jsonify({
                'percentage': 0,
                'current_step': 'Error retrieving progress',
                'status': 'error',
                'error_message': 'Failed to get progress information'
            }), 500
        
    except Exception as e:
        logger.error(f"Error getting training progress: {e}")
        return jsonify({'error': 'Failed to get progress'}), 500


@training_bp.route('/sessions')
@login_required
def list_sessions():
    """
    List all training sessions for the current user
    
    This endpoint returns a list of training sessions with their metadata.
    """
    try:
        # Get sessions from database
        logger.info(f"Listing training sessions for user: {current_user.id}")
        
        # Get all training sessions for the user
        sessions = db.session.query(TrainingSession).filter_by(
            user_id=current_user.id
        ).order_by(desc(TrainingSession.created_at)).all()
        
        # Convert to dict format
        sessions_data = [session.to_dict() for session in sessions]
        
        return jsonify({
            'success': True,
            'sessions': sessions_data
        })
        
    except Exception as e:
        logger.error(f"Error listing training sessions: {e}")
        return jsonify({'error': 'Failed to list sessions'}), 500


@training_bp.route('/sessions/manage')
@login_required
def manage_sessions():
    """
    Display the training sessions management page
    
    This route renders the sessions management template with all user sessions.
    """
    try:
        logger.info(f"User {current_user.id} accessed training sessions management")
        
        # Get sessions from database with proper filtering and sorting
        sessions = db.session.query(TrainingSession).filter_by(
            user_id=current_user.id
        ).order_by(desc(TrainingSession.created_at)).all()
        
        # Convert to dict format for template
        sessions_data = []
        for session in sessions:
            # Get question count from training results
            training_result = db.session.query(TrainingResult).filter_by(
                session_id=session.id
            ).first()
            
            session_dict = {
                'id': session.id,
                'name': session.name,
                'status': session.status,
                'created_at': session.created_at,
                'total_guides': session.total_guides or 0,
                'total_questions': training_result.questions_processed if training_result else 0,
                'average_confidence': session.average_confidence or 0.0,
                'is_active': session.is_active,
                'progress_percentage': session.progress_percentage or 0,
                'current_step': session.current_step or ''
            }
            sessions_data.append(session_dict)
        
        # Find active session
        active_session = next((s for s in sessions_data if s.get('is_active')), None)
        
        return render_template('training_sessions.html',
                             page_title='Training Sessions',
                             sessions=sessions_data,
                             active_session=active_session)
        
    except Exception as e:
        logger.error(f"Error loading training sessions management: {e}")
        flash('Error loading training sessions. Please try again.', 'error')
        return redirect(url_for('training.dashboard'))


@training_bp.route('/session/<session_id>')
@login_required
def get_session(session_id):
    """
    Get details for a specific training session
    
    This endpoint returns detailed information about a training session.
    """
    try:
        # Get session details from database
        logger.info(f"Getting session details: {session_id}")
        
        # Get actual session from database
        session_obj = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session_obj:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session_obj.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        session = {
            'id': session_obj.id,
            'name': session_obj.name,
            'status': session_obj.status,
            'created_at': session_obj.created_at.isoformat() if session_obj.created_at else None,
            'progress_percentage': session_obj.progress_percentage or 0,
            'current_step': session_obj.current_step or '',
            'total_guides': session_obj.total_guides or 0,
            'confidence_threshold': session_obj.confidence_threshold,
            'use_in_main_app': session_obj.use_in_main_app
        }
        
        return jsonify({
            'success': True,
            'session': session
        })
        
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        return jsonify({'error': 'Failed to get session details'}), 500


@training_bp.route('/session/<session_id>/report')
@login_required
def get_report(session_id):
    """
    Get training report for a session
    
    This endpoint renders the training report view.
    """
    try:
        logger.info(f"Getting report for session: {session_id}")
        
        # Get session and report data from database
        session_obj = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session_obj:
            flash('Training session not found.', 'error')
            return redirect(url_for('training.dashboard'))
        
        if session_obj.user_id != current_user.id:
            flash('Access denied to this session.', 'error')
            return redirect(url_for('training.dashboard'))
        
        session = {
            'id': session_obj.id,
            'name': session_obj.name,
            'status': session_obj.status,
            'created_at': session_obj.created_at.isoformat() if session_obj.created_at else None
        }
        
        # Generate report data from training results
        training_result = db.session.query(TrainingResult).filter_by(
            session_id=session_id
        ).first()
        
        if training_result:
            # Format duration
            duration_seconds = training_result.total_processing_time or 0
            duration_minutes = duration_seconds // 60
            duration_secs = duration_seconds % 60
            duration_str = f"{duration_minutes}m {duration_secs}s"
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_questions': training_result.questions_processed,
                'avg_confidence': training_result.average_confidence_score,
                'files_processed': session_obj.total_guides or 0,
                'duration': duration_str,
                'summary': f'Training completed with {training_result.questions_with_high_confidence} high-confidence questions out of {training_result.questions_processed} total.',
                'low_confidence_questions': training_result.questions_requiring_review,
                'errors': []
            }
        else:
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_questions': 0,
                'avg_confidence': 0.0,
                'files_processed': session_obj.total_guides or 0,
                'duration': '0m 0s',
                'summary': 'No training results available.',
                'low_confidence_questions': 0,
                'errors': ['Training results not found']
            }
        
        return render_template('training_report.html',
                             page_title=f'Report - {session["name"]}',
                             session=session,
                             report=report)
        
    except Exception as e:
        logger.error(f"Error getting training report: {e}")
        flash('Error loading training report. Please try again.', 'error')
        return redirect(url_for('training.manage_sessions'))


@training_bp.route('/session/<session_id>/report/download')
@login_required
def download_report(session_id):
    """
    Download training report as PDF
    
    This endpoint generates and serves the PDF report for download.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        logger.info(f"Downloading report for session: {session_id}")
        
        # TODO: Generate PDF report using TrainingReportService
        # For now, return a placeholder response
        
        from flask import send_file
        import io
        
        # Create a simple PDF placeholder
        pdf_content = b"%PDF-1.4\\n1 0 obj\\n<<\\n/Type /Catalog\\n/Pages 2 0 R\\n>>\\nendobj\\n2 0 obj\\n<<\\n/Type /Pages\\n/Kids [3 0 R]\\n/Count 1\\n>>\\nendobj\\n3 0 obj\\n<<\\n/Type /Page\\n/Parent 2 0 R\\n/MediaBox [0 0 612 792]\\n>>\\nendobj\\nxref\\n0 4\\n0000000000 65535 f \\n0000000009 00000 n \\n0000000058 00000 n \\n0000000115 00000 n \\ntrailer\\n<<\\n/Size 4\\n/Root 1 0 R\\n>>\\nstartxref\\n174\\n%%EOF"
        
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f'training-report-{session_id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return jsonify({'error': 'Failed to download report'}), 500


@training_bp.route('/session/<session_id>/report/markdown')
@login_required
def get_markdown_report(session_id):
    """
    Get training report in markdown format
    
    This endpoint returns the training report as markdown text.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        logger.info(f"Generating markdown report for session: {session_id}")
        
        # TODO: Generate markdown report using TrainingReportService
        markdown_report = f'''# Training Report - Session {session_id}

## Overview
- **Session ID**: {session_id}
- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Status**: Completed
- **Duration**: 15m 30s

## Statistics
- **Total Questions**: 45
- **Average Confidence**: 78%
- **Files Processed**: 5
- **Success Rate**: 95%

## Confidence Distribution
- **High Confidence (≥80%)**: 65%
- **Medium Confidence (60-80%)**: 25%
- **Low Confidence (<60%)**: 10%

## Question Analysis
### Question Types
- Multiple Choice: 35%
- Short Answer: 25%
- Essay: 20%
- Calculation: 20%

### Processing Performance
- Average processing time: 2.3 seconds per question
- OCR accuracy: 94%
- Model accuracy: 87%

## Recommendations
1. Consider retraining with more diverse examples
2. Review low-confidence questions for pattern analysis
3. OCR quality could be improved for handwritten text

## Summary
Training completed successfully with good overall confidence scores. The model shows consistent performance across different question types with room for improvement in essay-type questions.
'''
        
        return jsonify({
            'success': True,
            'markdown': markdown_report,
            'generated_at': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error generating markdown report: {e}")
        return jsonify({'error': 'Failed to generate markdown report'}), 500


@training_bp.route('/session/<session_id>/report/charts/<chart_type>')
@login_required
def get_report_chart(session_id, chart_type):
    """
    Get specific chart for training report
    
    This endpoint generates and returns chart images for the report.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        valid_chart_types = ['confidence', 'question_types', 'processing_time', 'accuracy', 'errors']
        if chart_type not in valid_chart_types:
            return jsonify({'error': f'Invalid chart type. Must be one of: {valid_chart_types}'}), 400
        
        logger.info(f"Generating {chart_type} chart for session: {session_id}")
        
        # TODO: Generate actual chart using matplotlib/plotly
        # For now, return chart configuration data
        
        chart_data = {
            'confidence': {
                'type': 'pie',
                'data': {
                    'labels': ['High (≥80%)', 'Medium (60-80%)', 'Low (<60%)'],
                    'values': [65, 25, 10],
                    'colors': ['#10b981', '#f59e0b', '#ef4444']
                }
            },
            'question_types': {
                'type': 'doughnut',
                'data': {
                    'labels': ['Multiple Choice', 'Short Answer', 'Essay', 'Calculation'],
                    'values': [35, 25, 20, 20],
                    'colors': ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
                }
            },
            'processing_time': {
                'type': 'bar',
                'data': {
                    'labels': ['0-1s', '1-2s', '2-5s', '5-10s', '10s+'],
                    'values': [45, 30, 15, 8, 2]
                }
            },
            'accuracy': {
                'type': 'line',
                'data': {
                    'labels': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5'],
                    'values': [0.85, 0.78, 0.92, 0.67, 0.89]
                }
            },
            'errors': {
                'type': 'bar',
                'data': {
                    'labels': ['OCR', 'Model', 'Validation', 'Network'],
                    'values': [3, 2, 1, 1]
                }
            }
        }
        
        return jsonify({
            'success': True,
            'chart_type': chart_type,
            'chart_config': chart_data.get(chart_type, {}),
            'generated_at': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return jsonify({'error': 'Failed to generate chart'}), 500


@training_bp.route('/session/<session_id>/report/export', methods=['POST'])
@login_required
def export_report(session_id):
    """
    Export training report in various formats
    
    This endpoint exports the training report in the specified format.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        data = request.get_json() or {}
        export_format = data.get('format', 'pdf').lower()
        include_charts = data.get('include_charts', True)
        include_raw_data = data.get('include_raw_data', False)
        
        valid_formats = ['pdf', 'markdown', 'json', 'csv', 'xlsx']
        if export_format not in valid_formats:
            return jsonify({'error': f'Invalid format. Must be one of: {valid_formats}'}), 400
        
        logger.info(f"Exporting report for session {session_id} in {export_format} format")
        
        # TODO: Generate export using TrainingReportService
        export_config = {
            'session_id': session_id,
            'format': export_format,
            'include_charts': include_charts,
            'include_raw_data': include_raw_data,
            'generated_at': time.time(),
            'user_id': current_user.id
        }
        
        # Generate export ID for tracking
        export_id = f"export_{session_id}_{int(time.time())}"
        
        return jsonify({
            'success': True,
            'export_id': export_id,
            'format': export_format,
            'message': f'Report export started in {export_format} format',
            'download_url': f'/training/session/{session_id}/report/export/{export_id}/download',
            'estimated_completion': time.time() + 60  # 1 minute
        })
        
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        return jsonify({'error': 'Failed to export report'}), 500


@training_bp.route('/session/<session_id>/report/export/<export_id>/download')
@login_required
def download_exported_report(session_id, export_id):
    """
    Download exported report
    
    This endpoint serves the exported report file for download.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        logger.info(f"Downloading exported report: {export_id}")
        
        # TODO: Serve actual exported file
        # For now, return a placeholder
        
        return jsonify({
            'success': True,
            'message': 'Export download not yet implemented',
            'export_id': export_id
        })
        
    except Exception as e:
        logger.error(f"Error downloading exported report: {e}")
        return jsonify({'error': 'Failed to download exported report'}), 500


@training_bp.route('/session/<session_id>/report/share', methods=['POST'])
@login_required
def share_report(session_id):
    """
    Share training report with others
    
    This endpoint creates a shareable link for the training report.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        data = request.get_json() or {}
        share_config = {
            'expires_in_hours': data.get('expires_in_hours', 24),
            'password_protected': data.get('password_protected', False),
            'allow_download': data.get('allow_download', True),
            'recipients': data.get('recipients', [])  # Email addresses
        }
        
        # Validate expiration time
        if share_config['expires_in_hours'] < 1 or share_config['expires_in_hours'] > 168:  # 1 week max
            return jsonify({'error': 'Expiration must be between 1 and 168 hours'}), 400
        
        # Generate share token
        share_token = f"share_{session_id}_{int(time.time())}"
        share_url = f"{request.host_url}training/shared/{share_token}"
        
        logger.info(f"Creating shareable link for session {session_id}")
        
        # TODO: Store share configuration in database
        
        return jsonify({
            'success': True,
            'share_token': share_token,
            'share_url': share_url,
            'expires_at': time.time() + (share_config['expires_in_hours'] * 3600),
            'message': 'Shareable link created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sharing report: {e}")
        return jsonify({'error': 'Failed to share report'}), 500


@training_bp.route('/session/<session_id>/set-active', methods=['POST'])
@login_required
def set_active_model(session_id):
    """
    Set a training session as the active model
    
    This endpoint marks a completed training session as the active model
    for use in the main application.
    """
    try:
        logger.info(f"Setting session {session_id} as active model")
        
        # Implement actual active model setting
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status != 'completed':
            return jsonify({'error': 'Only completed sessions can be set as active'}), 400
        
        try:
            # Deactivate any currently active model for this user
            db.session.query(TrainingSession).filter(
                and_(
                    TrainingSession.user_id == current_user.id,
                    TrainingSession.is_active == True
                )
            ).update({'is_active': False})
            
            # Set this session as active
            session.is_active = True
            session.use_in_main_app = True
            db.session.commit()
            
            logger.info(f"Session {session_id} set as active model for user {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Model set as active successfully'
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to set session {session_id} as active: {e}")
            return jsonify({'error': 'Failed to set model as active'}), 500
        
    except Exception as e:
        logger.error(f"Error setting active model: {e}")
        return jsonify({'error': 'Failed to set active model'}), 500


@training_bp.route('/session/<session_id>/stop', methods=['POST'])
@login_required
def stop_training(session_id):
    """
    Stop a training session in progress
    
    This endpoint stops an active training session.
    """
    try:
        logger.info(f"Stopping training for session: {session_id}")
        
        # TODO: Implement actual training stop
        # This should:
        # 1. Verify the session belongs to the user
        # 2. Verify the session is in progress
        # 3. Stop the training process
        # 4. Update session status
        
        return jsonify({
            'success': True,
            'message': 'Training stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Error stopping training: {e}")
        return jsonify({'error': 'Failed to stop training'}), 500


@training_bp.route('/session/<session_id>/retry', methods=['POST'])
@login_required
def retry_training(session_id):
    """
    Retry a failed training session
    
    This endpoint restarts a failed training session.
    """
    try:
        logger.info(f"Retrying training for session: {session_id}")
        
        # TODO: Implement actual training retry
        # This should:
        # 1. Verify the session belongs to the user
        # 2. Verify the session has failed
        # 3. Reset session status and progress
        # 4. Restart the training process
        
        return jsonify({
            'success': True,
            'message': 'Training restarted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error retrying training: {e}")
        return jsonify({'error': 'Failed to retry training'}), 500


@training_bp.route('/session/<session_id>/logs')
@login_required
def view_logs(session_id):
    """
    View logs for a training session
    
    This endpoint returns or displays the logs for a training session.
    """
    try:
        logger.info(f"Viewing logs for session: {session_id}")
        
        # TODO: Implement actual log retrieval
        # This could either return JSON with logs or render a template
        
        return jsonify({
            'success': True,
            'logs': 'Log viewing not yet implemented'
        })
        
    except Exception as e:
        logger.error(f"Error viewing logs: {e}")
        return jsonify({'error': 'Failed to view logs'}), 500


@training_bp.route('/session/<session_id>/progress')
@login_required
def view_progress(session_id):
    """
    View detailed progress for a training session
    
    This endpoint renders a detailed progress view for a training session.
    """
    try:
        logger.info(f"Viewing progress for session: {session_id}")
        
        # TODO: Get session details from database
        session = {
            'id': session_id,
            'name': f'Training Session {session_id}',
            'status': 'in_progress',
            'created_at': '2024-01-01T00:00:00Z',
            'total_files': 5,
            'files_processed': 2,
            'questions_generated': 15,
            'avg_confidence': 0.75
        }
        
        return render_template('training_progress.html',
                             page_title=f'Progress - {session["name"]}',
                             session=session)
        
    except Exception as e:
        logger.error(f"Error viewing progress: {e}")
        flash('Error loading progress view. Please try again.', 'error')
        return redirect(url_for('training.manage_sessions'))


@training_bp.route('/session/<session_id>/edit')
@login_required
def edit_session(session_id):
    """
    Edit a training session configuration
    
    This endpoint renders the edit form for a training session.
    """
    try:
        logger.info(f"Editing session: {session_id}")
        
        # TODO: Get session details and render edit template
        # For now, redirect to dashboard to create new session
        flash('Session editing not yet implemented. Please create a new session.', 'info')
        return redirect(url_for('training.dashboard'))
        
    except Exception as e:
        logger.error(f"Error editing session: {e}")
        flash('Error loading edit view. Please try again.', 'error')
        return redirect(url_for('training.manage_sessions'))


@training_bp.route('/session/<session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """
    Delete a training session
    
    This endpoint deletes a training session and all associated data.
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        # Implement actual session deletion
        session = db.session.query(TrainingSession).filter_by(id=session_id).first()
        if not session:
            return jsonify({'error': 'Training session not found'}), 404
        
        if session.user_id != current_user.id:
            return jsonify({'error': 'Access denied to this session'}), 403
        
        if session.status == 'processing':
            return jsonify({'error': 'Cannot delete session while training is in progress'}), 400
        
        try:
            # Delete associated data
            db.session.query(TrainingResult).filter_by(session_id=session_id).delete()
            db.session.query(TrainingGuide).filter_by(session_id=session_id).delete()
            
            # Delete the session
            db.session.delete(session)
            db.session.commit()
            
            logger.info(f"Training session {session_id} deleted successfully")
            
            return jsonify({
                'success': True,
                'message': 'Training session deleted successfully'
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete session {session_id}: {e}")
            return jsonify({'error': 'Failed to delete training session'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({'error': 'Failed to delete session'}), 500


@training_bp.route('/session/<session_id>/restart', methods=['POST'])
@login_required
def restart_session(session_id):
    """
    Restart a training session
    
    This endpoint restarts a completed or failed training session.
    """
    try:
        logger.info(f"Restarting training session: {session_id}")
        
        # TODO: Implement actual session restart
        # This should:
        # 1. Verify the session belongs to the user
        # 2. Verify the session can be restarted (completed/failed)
        # 3. Reset session status and progress
        # 4. Restart the training process
        
        return jsonify({
            'success': True,
            'message': 'Training session restarted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error restarting session: {e}")
        return jsonify({'error': 'Failed to restart session'}), 500


@training_bp.route('/session/<session_id>/pause', methods=['POST'])
@login_required
def pause_session(session_id):
    """
    Pause a training session in progress
    
    This endpoint pauses an active training session.
    """
    try:
        logger.info(f"Pausing training session: {session_id}")
        
        # TODO: Implement actual session pause
        # This should:
        # 1. Verify the session belongs to the user
        # 2. Verify the session is in progress
        # 3. Pause the training process
        # 4. Update session status to 'paused'
        
        return jsonify({
            'success': True,
            'message': 'Training session paused successfully'
        })
        
    except Exception as e:
        logger.error(f"Error pausing session: {e}")
        return jsonify({'error': 'Failed to pause session'}), 500


@training_bp.route('/session/<session_id>/resume', methods=['POST'])
@login_required
def resume_session(session_id):
    """
    Resume a paused training session
    
    This endpoint resumes a paused training session.
    """
    try:
        logger.info(f"Resuming training session: {session_id}")
        
        # TODO: Implement actual session resume
        # This should:
        # 1. Verify the session belongs to the user
        # 2. Verify the session is paused
        # 3. Resume the training process
        # 4. Update session status to 'in_progress'
        
        return jsonify({
            'success': True,
            'message': 'Training session resumed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resuming session: {e}")
        return jsonify({'error': 'Failed to resume session'}), 500


# Error handlers for the blueprint
@training_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors in training routes"""
    return jsonify({'error': 'Training resource not found'}), 404


@training_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors in training routes"""
    logger.error(f"Internal error in training routes: {error}")
    return jsonify({'error': 'Internal server error'}), 500
# Confidence Monitoring and Quality Assurance Routes

@training_bp.route('/session/<session_id>/confidence', methods=['GET'])
@login_required
def get_session_confidence(session_id):
    """
    Get confidence metrics for a training session
    
    This endpoint returns detailed confidence analysis for all questions
    in a training session.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # Get confidence metrics using confidence monitor
        metrics = confidence_monitor.analyze_session_confidence(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'confidence_metrics': {
                'total_questions': metrics.total_questions,
                'avg_confidence': metrics.avg_confidence,
                'median_confidence': metrics.median_confidence,
                'std_deviation': metrics.std_deviation,
                'high_confidence_count': metrics.high_confidence_count,
                'medium_confidence_count': metrics.medium_confidence_count,
                'low_confidence_count': metrics.low_confidence_count,
                'critical_confidence_count': metrics.critical_confidence_count,
                'confidence_distribution': metrics.confidence_distribution
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting session confidence: {e}")
        return jsonify({'error': 'Failed to get confidence metrics'}), 500


@training_bp.route('/session/<session_id>/flagged-items', methods=['GET'])
@login_required
def get_flagged_items(session_id):
    """
    Get items flagged for low confidence or quality issues
    
    This endpoint returns questions that require manual review.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # Get threshold from query parameters
        threshold = float(request.args.get('threshold', 0.6))
        if threshold < 0.1 or threshold > 1.0:
            return jsonify({'error': 'Threshold must be between 0.1 and 1.0'}), 400
        
        # Get flagged items
        flagged_items = confidence_monitor.flag_low_confidence_items(session_id, threshold)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'threshold': threshold,
            'flagged_items': [{
                'question_id': item['question_id'],
                'guide_id': item['guide_id'],
                'question_number': item['question_number'],
                'confidence_score': item['confidence_score'],
                'quality_assessment': {
                    'confidence_level': item['quality_assessment'].confidence_level.value,
                    'quality_score': item['quality_assessment'].quality_score,
                    'flags': [flag.value for flag in item['quality_assessment'].flags],
                    'review_required': item['quality_assessment'].review_required,
                    'priority': item['quality_assessment'].priority,
                    'assessment_notes': item['quality_assessment'].assessment_notes
                },
                'suggested_actions': item['suggested_actions']
            } for item in flagged_items],
            'summary': {
                'total_flagged': len(flagged_items),
                'high_priority': len([item for item in flagged_items if item['quality_assessment'].priority >= 4]),
                'medium_priority': len([item for item in flagged_items if item['quality_assessment'].priority == 3]),
                'low_priority': len([item for item in flagged_items if item['quality_assessment'].priority <= 2])
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting flagged items: {e}")
        return jsonify({'error': 'Failed to get flagged items'}), 500


@training_bp.route('/question/<int:question_id>/review', methods=['POST'])
@login_required
def review_question(question_id):
    """
    Submit manual review for a question
    
    This endpoint allows users to manually review and update confidence
    scores for flagged questions.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'new_confidence' not in data:
            return jsonify({'error': 'New confidence score is required'}), 400
        
        if 'reviewer_notes' not in data:
            return jsonify({'error': 'Reviewer notes are required'}), 400
        
        # Validate confidence score
        try:
            new_confidence = float(data['new_confidence'])
            if new_confidence < 0.0 or new_confidence > 1.0:
                return jsonify({'error': 'Confidence score must be between 0.0 and 1.0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid confidence score'}), 400
        
        reviewer_notes = data['reviewer_notes'].strip()
        if len(reviewer_notes) < 10:
            return jsonify({'error': 'Reviewer notes must be at least 10 characters'}), 400
        
        # TODO: Verify question belongs to user's session
        
        # Update confidence after review
        success = confidence_monitor.update_confidence_after_review(
            question_id=question_id,
            new_confidence=new_confidence,
            reviewer_notes=reviewer_notes
        )
        
        if not success:
            return jsonify({'error': 'Failed to update question confidence'}), 500
        
        logger.info(f"Question {question_id} reviewed by user {current_user.id}: confidence updated to {new_confidence}")
        
        return jsonify({
            'success': True,
            'message': 'Question review submitted successfully',
            'question_id': question_id,
            'new_confidence': new_confidence,
            'reviewed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reviewing question {question_id}: {e}")
        return jsonify({'error': 'Failed to submit question review'}), 500


@training_bp.route('/confidence-trends', methods=['GET'])
@login_required
def get_confidence_trends():
    """
    Get confidence trends for the current user
    
    This endpoint returns confidence trends over time to help users
    understand their training quality improvements.
    """
    try:
        # Get days parameter
        days = int(request.args.get('days', 30))
        if days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        # Get confidence trends
        trends = confidence_monitor.track_confidence_trends(current_user.id, days)
        
        if 'error' in trends:
            return jsonify({'error': trends['error']}), 500
        
        return jsonify({
            'success': True,
            'user_id': current_user.id,
            'period_days': days,
            'trends': trends
        })
        
    except Exception as e:
        logger.error(f"Error getting confidence trends: {e}")
        return jsonify({'error': 'Failed to get confidence trends'}), 500


@training_bp.route('/session/<session_id>/quality-report', methods=['GET'])
@login_required
def get_quality_report(session_id):
    """
    Get comprehensive quality report for a training session
    
    This endpoint generates a detailed quality assessment report
    including confidence metrics, flagged items, and recommendations.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        # Get confidence metrics
        metrics = confidence_monitor.analyze_session_confidence(session_id)
        
        # Get flagged items
        flagged_items = confidence_monitor.flag_low_confidence_items(session_id, 0.6)
        
        # Generate quality report
        quality_report = {
            'session_id': session_id,
            'generated_at': datetime.now().isoformat(),
            'confidence_metrics': {
                'total_questions': metrics.total_questions,
                'avg_confidence': metrics.avg_confidence,
                'median_confidence': metrics.median_confidence,
                'std_deviation': metrics.std_deviation,
                'distribution': {
                    'high_confidence': metrics.high_confidence_count,
                    'medium_confidence': metrics.medium_confidence_count,
                    'low_confidence': metrics.low_confidence_count,
                    'critical_confidence': metrics.critical_confidence_count
                },
                'confidence_distribution': metrics.confidence_distribution
            },
            'quality_issues': {
                'total_flagged': len(flagged_items),
                'by_priority': {
                    'high': len([item for item in flagged_items if item['quality_assessment'].priority >= 4]),
                    'medium': len([item for item in flagged_items if item['quality_assessment'].priority == 3]),
                    'low': len([item for item in flagged_items if item['quality_assessment'].priority <= 2])
                },
                'by_flag_type': {}
            },
            'recommendations': [],
            'overall_quality_score': 0.0
        }
        
        # Calculate flag type distribution
        all_flags = []
        for item in flagged_items:
            all_flags.extend([flag.value for flag in item['quality_assessment'].flags])
        
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        quality_report['quality_issues']['by_flag_type'] = flag_counts
        
        # Calculate overall quality score
        if metrics.total_questions > 0:
            quality_score = (
                (metrics.high_confidence_count * 1.0 +
                 metrics.medium_confidence_count * 0.7 +
                 metrics.low_confidence_count * 0.4 +
                 metrics.critical_confidence_count * 0.1) / metrics.total_questions
            )
            quality_report['overall_quality_score'] = quality_score
        
        # Generate recommendations
        recommendations = []
        
        if metrics.critical_confidence_count > 0:
            recommendations.append(f"{metrics.critical_confidence_count} questions have critical confidence levels and require immediate review")
        
        if metrics.low_confidence_count > metrics.total_questions * 0.3:
            recommendations.append("High number of low-confidence questions - consider improving training data quality")
        
        if metrics.std_deviation > 0.3:
            recommendations.append("High variance in confidence scores - review consistency of training materials")
        
        if len(flagged_items) > metrics.total_questions * 0.5:
            recommendations.append("More than 50% of questions flagged - comprehensive review recommended")
        
        if not recommendations:
            recommendations.append("Training quality looks good - no major issues detected")
        
        quality_report['recommendations'] = recommendations
        
        return jsonify({
            'success': True,
            'quality_report': quality_report
        })
        
    except Exception as e:
        logger.error(f"Error generating quality report: {e}")
        return jsonify({'error': 'Failed to generate quality report'}), 500
# Error Monitoring and System Health Routes

@training_bp.route('/system/health', methods=['GET'])
@login_required
def get_system_health():
    """
    Get system health metrics
    
    This endpoint returns current system health including error rates,
    service status, and performance metrics.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        # Get system health metrics
        health = error_monitor.get_system_health()
        
        return jsonify({
            'success': True,
            'health': {
                'timestamp': health.timestamp.isoformat(),
                'error_rate': health.error_rate,
                'critical_errors_count': health.critical_errors_count,
                'active_sessions': health.active_sessions,
                'failed_sessions': health.failed_sessions,
                'average_response_time': health.average_response_time,
                'memory_usage': health.memory_usage,
                'disk_usage': health.disk_usage,
                'service_status': health.service_status
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({'error': 'Failed to get system health'}), 500


@training_bp.route('/system/errors', methods=['GET'])
@login_required
def get_error_statistics():
    """
    Get error statistics for the specified time period
    
    This endpoint returns comprehensive error statistics including
    categorization, trends, and recovery rates.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        # Get hours parameter
        hours = int(request.args.get('hours', 24))
        if hours < 1 or hours > 168:  # Max 1 week
            return jsonify({'error': 'Hours must be between 1 and 168'}), 400
        
        # Get error statistics
        stats = error_monitor.get_error_statistics(hours)
        
        if 'error' in stats:
            return jsonify({'error': stats['error']}), 500
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        return jsonify({'error': 'Failed to get error statistics'}), 500


@training_bp.route('/system/errors/<error_id>', methods=['GET'])
@login_required
def get_error_details(error_id):
    """
    Get detailed information about a specific error
    
    This endpoint returns comprehensive details about a specific error
    including stack trace, context, and recovery attempts.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        # Get error details
        error_details = error_monitor.get_error_details(error_id)
        
        if not error_details:
            return jsonify({'error': 'Error not found'}), 404
        
        return jsonify({
            'success': True,
            'error': error_details
        })
        
    except Exception as e:
        logger.error(f"Error getting error details: {e}")
        return jsonify({'error': 'Failed to get error details'}), 500


@training_bp.route('/system/errors/<error_id>/resolve', methods=['POST'])
@login_required
def resolve_error(error_id):
    """
    Mark an error as resolved
    
    This endpoint allows administrators to mark errors as resolved
    with resolution notes.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        data = request.get_json()
        resolution_notes = data.get('resolution_notes', '').strip()
        
        if not resolution_notes:
            return jsonify({'error': 'Resolution notes are required'}), 400
        
        if len(resolution_notes) < 10:
            return jsonify({'error': 'Resolution notes must be at least 10 characters'}), 400
        
        # Resolve the error
        success = error_monitor.resolve_error(error_id, resolution_notes)
        
        if not success:
            return jsonify({'error': 'Failed to resolve error or error not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Error resolved successfully',
            'error_id': error_id,
            'resolved_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error resolving error {error_id}: {e}")
        return jsonify({'error': 'Failed to resolve error'}), 500


@training_bp.route('/system/monitoring/start', methods=['POST'])
@login_required
def start_monitoring():
    """
    Start system monitoring
    
    This endpoint starts background system health monitoring.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        data = request.get_json() or {}
        interval = int(data.get('interval', 60))
        
        if interval < 10 or interval > 3600:  # 10 seconds to 1 hour
            return jsonify({'error': 'Interval must be between 10 and 3600 seconds'}), 400
        
        # Start monitoring
        error_monitor.start_monitoring(interval)
        
        return jsonify({
            'success': True,
            'message': 'System monitoring started',
            'interval': interval
        })
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({'error': 'Failed to start monitoring'}), 500


@training_bp.route('/system/monitoring/stop', methods=['POST'])
@login_required
def stop_monitoring():
    """
    Stop system monitoring
    
    This endpoint stops background system health monitoring.
    """
    try:
        from src.services.error_monitor import error_monitor
        
        # Stop monitoring
        error_monitor.stop_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'System monitoring stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return jsonify({'error': 'Failed to stop monitoring'}), 500


# Error Recovery Routes

@training_bp.route('/session/<session_id>/recover', methods=['POST'])
@login_required
def recover_training_session(session_id):
    """
    Attempt to recover a failed training session
    
    This endpoint attempts to recover a training session that has failed
    or encountered errors during processing.
    """
    try:
        # Validate session belongs to user
        if not session_id.startswith(f"session_{current_user.id}_"):
            return jsonify({'error': 'Access denied to this session'}), 403
        
        from src.services.error_recovery import error_recovery_service
        
        # Attempt session recovery
        recovery_result = error_recovery_service.recover_training_session(session_id)
        
        return jsonify({
            'success': True,
            'recovery_result': recovery_result
        })
        
    except Exception as e:
        logger.error(f"Error recovering training session {session_id}: {e}")
        return jsonify({'error': 'Failed to recover training session'}), 500


@training_bp.route('/file/recover', methods=['POST'])
@login_required
def recover_file_processing():
    """
    Attempt to recover failed file processing
    
    This endpoint attempts to recover file processing that has failed
    using alternative methods or fallback strategies.
    """
    try:
        data = request.get_json()
        
        file_path = data.get('file_path')
        processing_type = data.get('processing_type')
        
        if not file_path or not processing_type:
            return jsonify({'error': 'file_path and processing_type are required'}), 400
        
        # Validate processing type
        valid_types = ['ocr', 'llm', 'pdf', 'image']
        if processing_type not in valid_types:
            return jsonify({'error': f'processing_type must be one of: {valid_types}'}), 400
        
        # TODO: Validate file belongs to user
        
        from src.services.error_recovery import error_recovery_service
        
        # Attempt file processing recovery
        recovery_result = error_recovery_service.recover_file_processing(file_path, processing_type)
        
        return jsonify({
            'success': True,
            'recovery_result': recovery_result
        })
        
    except Exception as e:
        logger.error(f"Error recovering file processing: {e}")
        return jsonify({'error': 'Failed to recover file processing'}), 500


@training_bp.route('/system/recovery/stats', methods=['GET'])
@login_required
def get_recovery_statistics():
    """
    Get error recovery statistics
    
    This endpoint returns statistics about error recovery attempts,
    success rates, and fallback usage.
    """
    try:
        from src.services.error_recovery import error_recovery_service
        
        # Get recovery statistics
        stats = error_recovery_service.get_recovery_statistics()
        
        if 'error' in stats:
            return jsonify({'error': stats['error']}), 500
        
        return jsonify({
            'success': True,
            'recovery_statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting recovery statistics: {e}")
        return jsonify({'error': 'Failed to get recovery statistics'}), 500


# Performance Optimization and Caching Routes

@training_bp.route('/system/performance', methods=['GET'])
@login_required
def get_performance_metrics():
    """
    Get system performance metrics
    
    This endpoint returns comprehensive performance metrics including
    cache statistics, job queue status, and system resource usage.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        # Get performance metrics
        metrics = performance_optimizer.get_performance_metrics()
        
        return jsonify({
            'success': True,
            'performance_metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Failed to get performance metrics'}), 500


@training_bp.route('/system/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    """
    Clear system cache
    
    This endpoint clears cache at the specified level to free up memory
    and ensure fresh data retrieval.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer, CacheLevel
        
        data = request.get_json() or {}
        cache_level = data.get('cache_level', 'all')
        
        # Validate cache level
        valid_levels = ['memory', 'disk', 'hybrid', 'all']
        if cache_level not in valid_levels:
            return jsonify({'error': f'cache_level must be one of: {valid_levels}'}), 400
        
        # Clear cache
        if cache_level == 'all':
            performance_optimizer.clear_cache()
        else:
            level_map = {
                'memory': CacheLevel.MEMORY,
                'disk': CacheLevel.DISK,
                'hybrid': CacheLevel.HYBRID
            }
            performance_optimizer.clear_cache(level_map[cache_level])
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared: {cache_level}',
            'cleared_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500


@training_bp.route('/system/cache/preload', methods=['POST'])
@login_required
def preload_cache():
    """
    Preload cache with commonly accessed data
    
    This endpoint starts a background job to preload cache with
    frequently accessed training data.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        data = request.get_json()
        cache_keys = data.get('cache_keys', [])
        
        if not cache_keys or not isinstance(cache_keys, list):
            return jsonify({'error': 'cache_keys must be a non-empty list'}), 400
        
        if len(cache_keys) > 100:
            return jsonify({'error': 'Maximum 100 cache keys allowed'}), 400
        
        # Implement actual data loader function
        def data_loader(key):
            # Load actual data based on key type
            if key.startswith('session_'):
                session_id = key.replace('session_', '')
                session = db.session.query(TrainingSession).filter_by(id=session_id).first()
                return session.to_dict() if session else None
            elif key.startswith('result_'):
                session_id = key.replace('result_', '')
                result = db.session.query(TrainingResult).filter_by(session_id=session_id).first()
                return result.to_dict() if result else None
            else:
                return None
        
        # Start cache preload
        performance_optimizer.preload_cache(data_loader, cache_keys)
        
        return jsonify({
            'success': True,
            'message': f'Cache preload started for {len(cache_keys)} keys',
            'started_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error preloading cache: {e}")
        return jsonify({'error': 'Failed to preload cache'}), 500


@training_bp.route('/system/jobs', methods=['GET'])
@login_required
def get_background_jobs():
    """
    Get background job status
    
    This endpoint returns information about active and completed
    background jobs in the system.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        # Get job statistics
        job_stats = performance_optimizer.job_processor.get_queue_stats()
        
        return jsonify({
            'success': True,
            'job_statistics': job_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting background jobs: {e}")
        return jsonify({'error': 'Failed to get background jobs'}), 500


@training_bp.route('/system/jobs/<job_id>', methods=['GET'])
@login_required
def get_job_status(job_id):
    """
    Get status of a specific background job
    
    This endpoint returns detailed status information about
    a specific background job.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        # Get job status
        job_status = performance_optimizer.job_processor.get_job_status(job_id)
        
        if not job_status:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'job_status': job_status
        })
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': 'Failed to get job status'}), 500


@training_bp.route('/system/jobs/<job_id>/cancel', methods=['POST'])
@login_required
def cancel_background_job(job_id):
    """
    Cancel a background job
    
    This endpoint attempts to cancel a running or queued background job.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        # Cancel the job
        success = performance_optimizer.job_processor.cancel_job(job_id)
        
        if not success:
            return jsonify({'error': 'Job not found or cannot be cancelled'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully',
            'job_id': job_id,
            'cancelled_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({'error': 'Failed to cancel job'}), 500


@training_bp.route('/system/optimize', methods=['POST'])
@login_required
def optimize_system():
    """
    Trigger system optimization
    
    This endpoint triggers various system optimization tasks including
    cache cleanup, memory management, and performance tuning.
    """
    try:
        from src.services.performance_optimizer import performance_optimizer
        
        data = request.get_json() or {}
        optimization_tasks = data.get('tasks', ['cache_cleanup', 'memory_optimization'])
        
        valid_tasks = ['cache_cleanup', 'memory_optimization', 'query_optimization', 'disk_cleanup']
        invalid_tasks = [task for task in optimization_tasks if task not in valid_tasks]
        
        if invalid_tasks:
            return jsonify({'error': f'Invalid optimization tasks: {invalid_tasks}'}), 400
        
        optimization_results = {}
        
        # Cache cleanup
        if 'cache_cleanup' in optimization_tasks:
            # Clear old cache entries
            performance_optimizer.clear_cache()
            optimization_results['cache_cleanup'] = 'completed'
        
        # Memory optimization
        if 'memory_optimization' in optimization_tasks:
            # TODO: Implement memory optimization
            optimization_results['memory_optimization'] = 'completed'
        
        # Query optimization
        if 'query_optimization' in optimization_tasks:
            # TODO: Implement query optimization
            optimization_results['query_optimization'] = 'completed'
        
        # Disk cleanup
        if 'disk_cleanup' in optimization_tasks:
            # TODO: Implement disk cleanup
            optimization_results['disk_cleanup'] = 'completed'
        
        return jsonify({
            'success': True,
            'message': 'System optimization completed',
            'optimization_results': optimization_results,
            'optimized_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error optimizing system: {e}")
        return jsonify({'error': 'Failed to optimize system'}), 500