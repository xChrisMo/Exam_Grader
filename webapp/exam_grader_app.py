#!/usr/bin/env python3
"""
Exam Grader Flask Web Application
Modern educational assessment platform with AI-powered grading capabilities.
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Flask imports
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

# Project imports
try:
    from src.config.unified_config import config
    from src.database import db, User, MarkingGuide, Submission, GradingResult, DatabaseUtils
    from src.security.session_manager import SecureSessionManager
    from src.security.secrets_manager import secrets_manager, initialize_secrets
    from src.security.flask_session_interface import SecureSessionInterface
    from src.services.ocr_service import OCRService
    from src.services.llm_service import LLMService
    from src.services.mapping_service import MappingService
    from src.services.grading_service import GradingService
    from src.services.file_cleanup_service import FileCleanupService
    from src.parsing.parse_submission import parse_student_submission
    from src.parsing.parse_guide import parse_marking_guide
    from utils.logger import logger
    from utils.input_sanitizer import sanitize_form_data, validate_file_upload
    from utils.loading_states import loading_manager, get_loading_state_for_template
    from webapp.auth import init_auth, login_required, get_current_user
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize Flask application
app = Flask(__name__)

# Load and validate configuration
try:
    config.validate()
    app.config.update(config.get_flask_config())
    app.config['SECRET_KEY'] = config.security.secret_key
    logger.info(f"Configuration loaded for environment: {config.environment}")
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to load configuration: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize CSRF protection
try:
    csrf = CSRFProtect(app)
    logger.info("CSRF protection initialized")
except Exception as e:
    logger.error(f"Failed to initialize CSRF protection: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to initialize CSRF protection: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize database
try:
    db.init_app(app)
    logger.info("Database initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to initialize database: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize security components
try:
    initialize_secrets()
    session_manager = SecureSessionManager(
        config.security.secret_key,
        config.security.session_timeout
    )
    # Set the custom session interface for Flask
    app.session_interface = SecureSessionInterface(session_manager, app.config['SECRET_KEY'])
    logger.info("Security components initialized")
except Exception as e:
    logger.error(f"Failed to initialize security: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to initialize security: {e}", file=sys.stderr)
    sys.exit(1)

# Initialize authentication system
try:
    init_auth(app, session_manager)
    logger.info("Authentication system initialized")
except Exception as e:
    logger.error(f"Failed to initialize authentication: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to initialize authentication: {e}", file=sys.stderr)
    sys.exit(1)

def allowed_file(filename):
    """Check if file type is allowed."""
    if not filename:
        return False
    ext = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in config.files.supported_formats

# Initialize services
try:
    ocr_api_key = secrets_manager.get_secret('HANDWRITING_OCR_API_KEY')
    llm_api_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')

    ocr_service = OCRService(api_key=ocr_api_key) if ocr_api_key else None
    llm_service = LLMService(api_key=llm_api_key) if llm_api_key else None
    mapping_service = MappingService(llm_service=llm_service)
    grading_service = GradingService(llm_service=llm_service, mapping_service=mapping_service)

    file_cleanup_service = FileCleanupService(config)
    file_cleanup_service.start_scheduled_cleanup()

    logger.info("Services initialized")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    print(f"[CRITICAL ERROR] Failed to initialize services: {e}", file=sys.stderr)
    ocr_service = None
    llm_service = None
    mapping_service = None
    grading_service = None
    file_cleanup_service = None
    sys.exit(1)

# Utility functions

def get_config_value(key: str, default=None):
    """Get configuration value with fallback."""
    return getattr(config, key, default)

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0.0

def get_storage_stats() -> Dict[str, Any]:
    """Get storage statistics."""
    try:
        temp_size = 0
        output_size = 0

        temp_dir = str(config.files.temp_dir)
        output_dir = str(config.files.output_dir)

        if os.path.exists(temp_dir):
            temp_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(temp_dir)
                for filename in filenames
            ) / (1024 * 1024)

        if os.path.exists(output_dir):
            output_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(output_dir)
                for filename in filenames
            ) / (1024 * 1024)

        max_file_size = config.files.max_file_size_mb

        return {
            'temp_size_mb': round(temp_size, 2),
            'output_size_mb': round(output_size, 2),
            'total_size_mb': round(temp_size + output_size, 2),
            'max_size_mb': max_file_size * 10
        }
    except Exception as e:
        logger.error(f"Error calculating storage stats: {str(e)}")
        return {
            'temp_size_mb': 0.0,
            'output_size_mb': 0.0,
            'total_size_mb': 0.0,
            'max_size_mb': 160.0
        }

# Service status cache
_service_status_cache = {}
_service_status_cache_time = 0
SERVICE_STATUS_CACHE_DURATION = 300  # 5 minutes

def get_service_status() -> Dict[str, bool]:
    """Check status of all services with caching."""
    global _service_status_cache, _service_status_cache_time

    current_time = time.time()
    if (current_time - _service_status_cache_time) < SERVICE_STATUS_CACHE_DURATION and _service_status_cache:
        return _service_status_cache

    try:
        # Check service availability
        ocr_available = bool(ocr_service and ocr_service.api_key)
        llm_available = bool(llm_service and llm_service.api_key)

        # Check database
        storage_available = False
        try:
            from flask import has_app_context
            if has_app_context():
                User.query.count()
                storage_available = True
            else:
                with app.app_context():
                    User.query.count()
                    storage_available = True
        except Exception:
            storage_available = False

        # Cache result
        _service_status_cache = {
            'ocr_status': ocr_available,
            'llm_status': llm_available,
            'storage_status': storage_available,
            'config_status': True,
            'guide_storage_available': storage_available,
            'submission_storage_available': storage_available
        }
        _service_status_cache_time = current_time
        return _service_status_cache

    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        return {
            'ocr_status': False,
            'llm_status': False,
            'storage_status': False,
            'config_status': True,
            'guide_storage_available': False,
            'submission_storage_available': False
        }

# Error handlers
@app.errorhandler(413)
def too_large(e):
    flash(f'File too large. Maximum size is {config.files.max_file_size_mb}MB.', 'error')
    return redirect(request.url)

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html',
                         error_code=404,
                         error_message="Page not found",
                         service_status=get_service_status()), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error",
                         service_status=get_service_status()), 500

@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please wait before trying again.',
            'status_code': 429
        }), 429
    else:
        flash('Too many requests. Please wait before trying again.', 'warning')
        return render_template('error.html',
                             error_code=429,
                             error_message="Rate limit exceeded. Please wait before trying again."), 429

# Template context processor
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    try:
        loading_manager.auto_cleanup()
        loading_states = get_loading_state_for_template()
    except Exception:
        loading_states = {'loading_operations': {}, 'has_active_operations': False, 'total_active_operations': 0}

    try:
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
    except Exception:
        csrf_token = ''

    return {
        'app_version': '2.0.0',
        'current_year': datetime.now().year,
        'service_status': get_service_status(),
        'storage_stats': get_storage_stats(),
        'loading_states': loading_states,
        'csrf_token': csrf_token
    }

# Routes
@app.route('/landing')
def landing():
    """Public landing page."""
    try:
        # Check if user is authenticated
        current_user = get_current_user()
        is_authenticated = current_user is not None

        context = {
            'page_title': 'Welcome to Exam Grader',
            'is_authenticated': is_authenticated,
            'current_user': current_user
        }
        return render_template('landing.html', **context)
    except Exception as e:
        logger.error(f"Error loading landing page: {str(e)}")
        # Fallback to basic landing page
        return render_template('landing.html',
                             page_title='Welcome to Exam Grader',
                             is_authenticated=False,
                             current_user=None)

@app.route('/')
def root():
    """Root route - redirect based on authentication status."""
    try:
        current_user = get_current_user()
        if current_user:
            # User is authenticated, redirect to dashboard
            return redirect(url_for('dashboard'))
        else:
            # User is not authenticated, show landing page
            return redirect(url_for('landing'))
    except Exception as e:
        logger.error(f"Error in root route: {str(e)}")
        # Fallback to landing page
        return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash('Please log in to access the dashboard.', 'error')
            return redirect(url_for('auth.login'))

        # Calculate dashboard statistics from database (user-specific) with session fallback
        from src.database.models import Submission, MarkingGuide, GradingResult

        # Single optimized query to get all submission statistics
        submission_stats = db.session.query(
            db.func.count(Submission.id).label('total'),
            db.func.count(db.case((Submission.processing_status == 'completed', 1))).label('processed')
        ).filter(Submission.user_id == current_user.id).first()

        total_submissions = submission_stats.total if submission_stats else 0
        processed_submissions = submission_stats.processed if submission_stats else 0

        # If no database submissions, check session data as fallback
        if total_submissions == 0:
            session_submissions = session.get('submissions', [])
            total_submissions = len(session_submissions)
            processed_submissions = len([s for s in session_submissions if s.get('processed', False)])
            logger.info(f"Dashboard: Using session data fallback. Total: {total_submissions}, Processed: {processed_submissions}")
            logger.info(f"Dashboard: Raw session['submissions']: {session_submissions}")

        logger.info(f"Dashboard: Calculated total_submissions: {total_submissions}, processed_submissions: {processed_submissions}")

        # Check if a guide is currently loaded in session (primary check)
        guide_uploaded = session.get('guide_uploaded', False)

        # Fallback: check if any guide exists in database
        if not guide_uploaded:
            guide_uploaded = MarkingGuide.query.filter_by(user_id=current_user.id).limit(1).first() is not None

        # Get recent submissions as activity (user-specific) - limited to 5
        recent_submissions = Submission.query.filter_by(user_id=current_user.id).order_by(
            Submission.created_at.desc()
        ).limit(5).all()

        # Build activity list efficiently from database
        recent_activity = [
            {
                'type': 'submission_upload',
                'message': f'Processed submission: {submission.filename}',
                'timestamp': submission.created_at.isoformat(),
                'icon': 'document'
            }
            for submission in recent_submissions
        ]

        # If no database submissions, use session activity as fallback
        if not recent_activity:
            session_activity = session.get('recent_activity', [])
            recent_activity = session_activity[:5]  # Limit to 5 most recent
            logger.info(f"Using session activity: {len(recent_activity)} items")

        # Calculate average score from grading results (user-specific) - optimized
        avg_result = db.session.query(db.func.avg(GradingResult.percentage)).join(
            Submission, GradingResult.submission_id == Submission.id
        ).filter(Submission.user_id == current_user.id).scalar()
        avg_score = round(avg_result, 1) if avg_result else 0
        last_score = avg_score  # Use average as last score for now

        service_status = get_service_status()
        context = {
            'page_title': 'Dashboard',
            'total_submissions': total_submissions,
            'processed_submissions': processed_submissions,
            'guide_uploaded': guide_uploaded,
            'last_score': last_score,
            'avg_score': avg_score,
            'recent_activity': recent_activity,
            'submissions': [s.to_dict() for s in recent_submissions],  # Convert to dict for template
            'service_status': service_status,  # Add service_status for dashboard
            'guide_storage_available': service_status.get('guide_storage_available', False),
            'submission_storage_available': service_status.get('submission_storage_available', False)
        }
        return render_template('dashboard.html', **context)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'error')
        return render_template('dashboard.html',
                             page_title='Dashboard',
                             total_submissions=0,
                             processed_submissions=0,
                             guide_uploaded=False,
                             last_score=0,
                             avg_score=0,
                             recent_activity=[],
                             submissions=[])

@app.route('/upload-guide', methods=['GET', 'POST'])
@login_required
def upload_guide():
    """Upload and process marking guide."""
    if request.method == 'GET':
        return render_template('upload_guide.html', page_title='Upload Marking Guide')

    # CRITICAL DEBUG: This should appear in logs if route is being called
    logger.info("=== UPLOAD GUIDE ROUTE CALLED ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request files: {list(request.files.keys())}")

    try:
        if 'guide_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['guide_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('File type not supported. Please upload a PDF, Word document, or image file.', 'error')
            return redirect(request.url)

        # Create temp directory if it doesn't exist
        temp_dir = str(config.files.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, f"guide_{uuid.uuid4().hex}_{filename}")
        file.save(file_path)

        # Process guide with LLM extraction
        try:
            # Debug: Check if parse_marking_guide is available
            logger.info(f"Debug: parse_marking_guide in globals: {'parse_marking_guide' in globals()}")
            logger.info(f"Debug: parse_marking_guide function: {globals().get('parse_marking_guide', 'NOT FOUND')}")

            if 'parse_marking_guide' in globals():
                logger.info("Debug: Calling parse_marking_guide function")
                guide, error_message = parse_marking_guide(file_path)
                if error_message:
                    flash(f'Error processing guide: {error_message}', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
                if guide:
                    # Extract questions and marks using LLM service
                    questions = []
                    total_marks = 0
                    extraction_method = 'none'

                    try:
                        # Debug logging for LLM extraction conditions
                        logger.info(f"LLM extraction debug - mapping_service available: {mapping_service is not None}")
                        logger.info(f"LLM extraction debug - guide.raw_content length: {len(guide.raw_content) if guide.raw_content else 0}")

                        # Import and use the mapping service for LLM extraction
                        if mapping_service and guide.raw_content:
                            logger.info("Using LLM service to extract questions and marks from guide content")
                            logger.info(f"Guide content preview: {guide.raw_content[:200]}...")

                            extraction_result = mapping_service.extract_questions_and_total_marks(guide.raw_content)
                            logger.info(f"LLM extraction result: {extraction_result}")

                            if extraction_result:
                                questions = extraction_result.get('questions', [])
                                total_marks = extraction_result.get('total_marks', 0)
                                extraction_method = extraction_result.get('extraction_method', 'llm')

                                logger.info(f"LLM extraction successful: {len(questions)} questions, {total_marks} total marks")
                            else:
                                logger.warning("LLM extraction returned empty result")
                        else:
                            if not mapping_service:
                                logger.warning("LLM service not available - mapping_service is None")
                            if not guide.raw_content:
                                logger.warning("No content to extract from - guide.raw_content is empty")

                    except Exception as llm_error:
                        logger.error(f"LLM extraction failed: {str(llm_error)}")
                        logger.error(f"LLM extraction error traceback: ", exc_info=True)
                        # Continue with empty questions/marks rather than failing completely

                    guide_data = {
                        'raw_content': guide.raw_content,
                        'filename': filename,
                        'questions': questions,
                        'total_marks': total_marks,
                        'extraction_method': extraction_method,
                        'processed_at': datetime.now().isoformat()
                    }
                else:
                    flash('Error: Could not process guide.', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
            else:
                # Create basic guide data structure if parse_marking_guide is not available
                logger.warning("Debug: parse_marking_guide NOT found in globals - using fallback")
                logger.warning(f"Debug: Available globals keys: {list(globals().keys())[:20]}...")  # Show first 20 keys
                guide_data = {
                    'filename': filename,
                    'questions': [],
                    'total_marks': 0,
                    'extraction_method': 'none',
                    'processed_at': datetime.now().isoformat()
                }
        except Exception as parse_error:
            logger.error(f"Error parsing guide: {str(parse_error)}")
            flash(f'Error parsing guide: {str(parse_error)}', 'error')
            os.remove(file_path)
            return redirect(request.url)



        # Store guide in database
        logger.info("Storing guide in database.")
        try:
            from src.database.models import MarkingGuide, User

            # Get current logged-in user
            current_user = get_current_user()
            if not current_user:
                flash('Error: User session expired. Please log in again.', 'error')
                os.remove(file_path)
                return redirect(url_for('auth.login'))

            # Create enhanced description with extraction information
            questions_count = len(guide_data.get('questions', []))
            total_marks = guide_data.get('total_marks', 0.0)
            extraction_method = guide_data.get('extraction_method', 'none')

            if extraction_method == 'llm' and questions_count > 0:
                description = f"Uploaded guide: {filename} | LLM-extracted {questions_count} questions | Total marks: {total_marks}"
            elif extraction_method == 'regex' and questions_count > 0:
                description = f"Uploaded guide: {filename} | Regex-extracted {questions_count} questions | Total marks: {total_marks}"
            else:
                description = f"Uploaded guide: {filename} | No questions extracted"

            # Create marking guide record
            marking_guide = MarkingGuide(
                user_id=current_user.id,
                title=guide_data.get('title', filename),
                description=description,
                filename=filename,
                file_path=file_path,  # Keep the file path for now
                file_size=os.path.getsize(file_path),
                file_type=filename.split('.')[-1].lower(),
                content_text=guide_data.get('raw_content', ''),
                questions=guide_data.get('questions', []),
                total_marks=total_marks
            )

            db.session.add(marking_guide)
            db.session.commit()
            guide_id = marking_guide.id

            logger.info(f"Guide stored in database with ID: {guide_id}")
            session['guide_uploaded'] = True

        except Exception as storage_error:
            logger.error(f"Error storing guide in database: {str(storage_error)}")
            db.session.rollback()
            flash(f'Error storing guide: {str(storage_error)}', 'error')
            os.remove(file_path)
            return redirect(request.url)

        logger.info(f"Guide uploaded successfully: {filename}")

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")

        flash('Marking guide uploaded and processed successfully!', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Error uploading guide: {str(e)}")
        flash('Error uploading guide. Please try again.', 'error')
        return redirect(request.url)

@app.route('/upload-submission', methods=['GET', 'POST'])
@login_required
def upload_submission():
    """Upload and process student submission."""
    if request.method == 'GET':
        return render_template('upload_submission.html', page_title='Upload Submission')

    try:

        files = request.files.getlist('file')
        if not files or all(f.filename == '' for f in files):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return jsonify({'success': False, 'error': 'No files selected.'}), 400
            flash('No files selected.', 'error')
            return redirect(request.url)

        temp_dir = str(config.files.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        uploaded_count = 0
        failed_count = 0
        submissions_data = session.get('submissions', [])

        for file in files:
            if file.filename == '':
                continue

            if not allowed_file(file.filename):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return jsonify({'success': False, 'error': f'File type not supported for {file.filename}. Skipping.'}), 400
                flash(f'File type not supported for {file.filename}. Skipping.', 'error')
                failed_count += 1
                continue

            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_dir, f"submission_{uuid.uuid4().hex}_{filename}")
            try:
                file.save(file_path)

                answers = {}
                raw_text = ''
                error = None

                if 'parse_student_submission' in globals():
                    answers, raw_text, error = parse_student_submission(file_path)

                if error:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                        return jsonify({'success': False, 'error': f'Error processing {filename}: {error}'}), 400
                    flash(f'Error processing {filename}: {error}', 'error')
                    failed_count += 1
                    os.remove(file_path)
                    continue
                elif not answers and not raw_text:
                    # Fallback if parsing fails or returns empty, but no explicit error
                    answers = {'extracted_text': f'Sample text from {filename}'}
                    raw_text = f'Raw text content from {filename}'

                logger.info(f"Before storing in session - filename: {filename}, raw_text length: {len(raw_text) if raw_text else 0}, answers keys: {list(answers.keys()) if answers else 'None'}")

                submission_id = str(uuid.uuid4())

                # Try to store in database first, fallback to session
                try:
                    from src.database.models import Submission
                    from flask import current_app

                    current_user = get_current_user()
                    if current_user:
                        # Get file info for database storage
                        file_size = get_file_size_mb(file_path) * 1024 * 1024  # Convert to bytes
                        file_type = Path(filename).suffix.lower()

                        # Store in database with all required fields
                        submission = Submission(
                            user_id=current_user.id,
                            filename=filename,
                            file_path=file_path,  # Store the path
                            file_size=int(file_size),
                            file_type=file_type,
                            content_text=raw_text,
                            answers=answers,
                            processing_status='completed'
                        )
                        db.session.add(submission)
                        db.session.commit()
                        submission_id = str(submission.id)
                        logger.info(f"Stored submission in database with ID: {submission_id}")




                except Exception as storage_error:
                    logger.warning(f"Database storage failed: {str(storage_error)}")

                uploaded_count += 1

                activity = session.get('recent_activity', [])
                activity.insert(0, {
                    'type': 'submission_upload',
                    'message': f'Uploaded submission: {filename}',
                    'timestamp': datetime.now().isoformat(),
                    'icon': 'upload'
                })
                session['recent_activity'] = activity[:10]

            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                flash(f'Error processing {filename}: {str(e)}', 'error')
                failed_count += 1
            finally:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")

        if uploaded_count > 0:
            flash(f'{uploaded_count} submission(s) uploaded and processed successfully!', 'success')
            logger.info(f'{uploaded_count} submission(s) uploaded successfully.')
        if failed_count > 0:
            flash(f'{failed_count} submission(s) failed to upload or process. Check logs for details.', 'error')

        return redirect(url_for('dashboard'))

    except RequestEntityTooLarge:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return jsonify({'success': False, 'error': f'File too large. Max size is {config.max_file_size_mb}MB.'}), 413
        flash(f'File too large. Max size is {config.max_file_size_mb}MB.', 'error')
        return redirect(request.url)
    except Exception as e:
        logger.error(f"Error uploading submission: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        flash('Error uploading submission. Please try again.', 'error')
        return redirect(request.url)

@app.route('/submissions')
@login_required
def view_submissions():
    """View all submissions from both database and session."""
    try:
        submissions = []

        # Get current user
        current_user = get_current_user()

        # Get submissions from database first
        if current_user:
            try:
                from src.database.models import Submission
                db_submissions = Submission.query.filter_by(user_id=current_user.id).order_by(
                    Submission.created_at.desc()
                ).all()

                for submission in db_submissions:
                    submissions.append({
                        'id': str(submission.id),
                        'filename': submission.filename,
                        'uploaded_at': submission.created_at.isoformat(),
                        'processed': submission.processing_status == 'completed',
                        'size_mb': round(submission.file_size / (1024 * 1024), 2) if submission.file_size else 0,
                        'source': 'database'
                    })
                logger.info(f"Loaded {len(db_submissions)} submissions from database")
            except Exception as db_error:
                logger.warning(f"Error loading database submissions: {str(db_error)}")

        logger.info(f"Total submissions to display: {len(submissions)}")

        context = {
            'page_title': 'Submissions',
            'submissions': submissions
        }
        return render_template('submissions.html', **context)
    except Exception as e:
        logger.error(f"Error viewing submissions: {str(e)}")
        flash('Error loading submissions. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/results')
def view_results():
    """View grading results."""
    try:
        if not session.get('last_grading_result'):
            flash('No grading results available.', 'warning')
            return redirect(url_for('dashboard'))

        # Get grading results from database
        # Assuming we want to display results for the last processed batch
        # This might need a more robust way to identify the 'current' batch
        # For now, let's fetch all grading results and filter/group them as needed
        # Or, if we store a batch_id in session, we can use that to query.
        # For simplicity, let's fetch all and process.
        all_grading_results = GradingResult.query.all()
        if not all_grading_results:
            flash('No grading results available in the database.', 'warning')
            return redirect(url_for('dashboard'))

        grading_results = {}
        for res in all_grading_results:
            grading_results[res.submission_id] = {
                'filename': res.submission.filename if res.submission else 'Unknown',
                'status': 'completed',
                'timestamp': res.created_at.isoformat() if res.created_at else '',
                'score': res.score,
                'percentage': res.percentage,
                'max_score': res.max_score,
                'feedback': res.feedback,
                'criteria_scores': res.detailed_feedback,
                'mappings': [], # Mappings are part of the Mapping model, not directly in GradingResult
                'metadata': {}
            }

        # Calculate batch summary
        total_submissions = len(grading_results)
        scores = [result.get('score', 0) for result in grading_results.values()]
        avg_score = sum(scores) / len(scores) if scores else 0
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0

        # Grade distribution
        grade_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in scores:
            letter = get_letter_grade(score)[0]  # Get first character (A, B, C, D, F)
            if letter in grade_distribution:
                grade_distribution[letter] += 1

        # Format results for template
        results_list = []
        for submission_id, result in grading_results.items():
            results_list.append({
                'submission_id': submission_id,
                'filename': result.get('filename', 'Unknown'),
                'score': result.get('score', 0),
                'letter_grade': result.get('letter_grade', 'F'),
                'total_questions': len(result.get('question_scores', [])),
                'graded_at': result.get('timestamp', '')
            })

        # Sort results by score (highest first)
        results_list.sort(key=lambda x: x['score'], reverse=True)

        context = {
            'page_title': 'Grading Results',
            'has_results': bool(grading_results),
            'successful_grades': total_submissions,
            'batch_summary': {
                'total_submissions': total_submissions,
                'average_score': round(avg_score, 1),
                'highest_score': highest_score,
                'lowest_score': lowest_score,
                'score_distribution': grade_distribution
            },
            'results_list': results_list
        }

        return render_template('results.html', **context)

    except Exception as e:
        logger.error(f"Error viewing results: {str(e)}")
        flash('Error loading results. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/process-ai-grading', methods=['POST'])
@csrf.exempt
def process_ai_grading():
    max_questions = request.json.get('max_questions', None)
    """API endpoint to process unified AI-powered mapping and grading with progress tracking."""
    try:
        guide_id = request.json.get('guide_id')
        submission_ids = request.json.get('submission_ids', [])

        if not guide_id or not submission_ids:
            return jsonify({'error': 'Missing guide ID or submission IDs'}), 400

        guide = MarkingGuide.query.get(guide_id)
        if not guide:
            return jsonify({'error': 'Marking guide not found'}), 404

        submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
        if not submissions:
            return jsonify({'error': 'No submissions found for the provided IDs'}), 404

        # Check if services are available
        if not mapping_service:
            return jsonify({'error': 'AI services not available'}), 503

        # Process AI grading (mapping + grading combined)
        grading_results = {}
        successful_gradings = 0
        failed_gradings = 0

        # Get guide content from multiple sources
        guide_content = guide.content_text

        if not guide_content:
            return jsonify({'error': 'Guide content not available'}), 400

        # Process each submission with combined AI mapping and grading
        for submission in submissions:
            submission_id = submission.get('id')
            if not submission_id:
                continue

            try:
                # Get submission data from database
                db_submission = next((s for s in submissions if s.id == submission_id), None)
                if not db_submission:
                    logger.warning(f"No data found for submission {submission_id} in the provided list.")
                    failed_gradings += 1
                    continue

                submission_data = {
                    'filename': db_submission.filename,
                    'content': db_submission.content_text,
                    'answers': db_submission.answers
                }

                if not submission_data:
                    try:
                        db_submission = Submission.query.get(submission_id)
                        if db_submission:
                            submission_data = {
                                'filename': db_submission.filename,
                                'content': db_submission.content_text,
                                'answers': db_submission.answers
                            }
                    except Exception as e:
                        logger.warning(f"Could not retrieve submission from database: {str(e)}")

                if not submission_data:
                    logger.warning(f"No data found for submission {submission_id}")
                    failed_gradings += 1
                    continue

                # Get submission content
                submission_content = submission_data.get('content', '')
                if not submission_content and submission_data.get('answers'):
                    submission_content = '\n'.join([
                        f"Answer {i+1}: {answer}"
                        for i, answer in enumerate(submission_data.get('answers', {}).values())
                    ])

                if not submission_content:
                    logger.warning(f"No content found for submission {submission_id}")
                    failed_gradings += 1
                    continue

                # Use grading service for combined mapping and grading
                try:
                    logger.info(f"Starting AI processing for submission {submission_id}")

                    # The grading service internally handles mapping and grading
                    grading_result, grading_error = grading_service.grade_submission(
                        guide_content,
                        submission_content,
                        max_questions=max_questions
                    )

                    if grading_error:
                        logger.error(f"AI grading failed for submission {submission_id}: {grading_error}")
                        failed_gradings += 1
                        continue

                    if grading_result and grading_result.get('status') == 'success':
                        # Store comprehensive grading results
                        grading_results[submission_id] = {
                            'filename': submission.get('filename', 'Unknown'),
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'score': grading_result.get('score', 0),
                            'percentage': grading_result.get('percentage', 0),
                            'max_score': grading_result.get('max_score', 0),
                            'feedback': grading_result.get('feedback', ''),
                            'criteria_scores': grading_result.get('criteria_scores', []),
                            'mappings': grading_result.get('mappings', []),
                            'metadata': grading_result.get('metadata', {})
                        }
                        # Save grading result to database
                        try:
                            new_grading_result = GradingResult(
                                submission_id=submission_id,
                                mapping_id=grading_result.get('mapping_id'), # Assuming mapping_id is returned
                                score=grading_result.get('score', 0),
                                max_score=grading_result.get('max_score', 0),
                                percentage=grading_result.get('percentage', 0),
                                feedback=grading_result.get('feedback', ''),
                                detailed_feedback=grading_result.get('criteria_scores', []) # Or a more appropriate field
                            )
                            db.session.add(new_grading_result)
                            db.session.commit()
                            successful_gradings += 1
                            logger.info(f"AI processing completed for {submission_id}: {grading_result.get('percentage', 0)}%")
                        except Exception as db_e:
                            db.session.rollback()
                            logger.error(f"Database error saving grading result for {submission_id}: {str(db_e)}")
                            failed_gradings += 1
                            continue
                    else:
                        logger.error(f"Invalid grading result for submission {submission_id}")
                        failed_gradings += 1

                except Exception as e:
                    logger.error(f"Error in AI processing for submission {submission_id}: {str(e)}")
                    failed_gradings += 1
                    continue

            except Exception as e:
                logger.error(f"Error processing submission {submission_id}: {str(e)}")
                failed_gradings += 1
                continue



        # Calculate overall statistics
        total_score = sum(result.get('score', 0) for result in grading_results.values())
        total_max_score = sum(result.get('max_score', 0) for result in grading_results.values())
        average_percentage = sum(result.get('percentage', 0) for result in grading_results.values()) / len(grading_results) if grading_results else 0

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'ai_grading_complete',
            'message': f'AI processing completed: {successful_gradings} successful, {failed_gradings} failed',
            'timestamp': datetime.now().isoformat(),
            'icon': 'check'
        })
        session['recent_activity'] = activity[:10]

        return jsonify({
            'success': True,
            'message': f'AI processing completed: {successful_gradings} successful, {failed_gradings} failed',
            'results': grading_results,
            'summary': {
                'successful': successful_gradings,
                'failed': failed_gradings,
                'total': len(submissions),
                'total_score': total_score,
                'total_max_score': total_max_score,
                'average_percentage': round(average_percentage, 1)
            }
        })

    except Exception as e:
        logger.error(f"Error in process_ai_grading: {str(e)}")
        return jsonify({'error': f'AI processing failed: {str(e)}'}), 500


@app.route('/api/test-unified', methods=['GET', 'POST'])
@csrf.exempt
def test_unified_api():
    """Test endpoint to verify unified AI API is working."""
    try:
        # Get detailed session information
        guide_uploaded = session.get('guide_uploaded', False)
        submissions = session.get('submissions', [])
        guide_data = session.get('guide_data')
        guide_content = session.get('guide_raw_content', '')
        guide_filename = session.get('guide_filename', '')

        # Check what data is available
        has_guide_content = bool(guide_content or (guide_data and guide_data.get('questions')))
        has_submissions = len(submissions) > 0

        return jsonify({
            'success': True,
            'message': 'Unified AI API is working',
            'session_data': {
                'guide_uploaded': guide_uploaded,
                'submissions_count': len(submissions),
                'guide_id': session.get('guide_id'),
                'guide_filename': guide_filename,
                'has_guide_content': has_guide_content,
                'has_submissions': has_submissions,
                'guide_content_length': len(guide_content),
                'guide_data_available': guide_data is not None
            },
            'ready_for_processing': has_guide_content and has_submissions,
            'missing_requirements': [
                'marking guide' if not has_guide_content else None,
                'submissions' if not has_submissions else None
            ]
        })
    except Exception as e:
        logger.error(f"Error in test_unified_api: {str(e)}")
        return jsonify({'error': f'Test failed: {str(e)}'}), 500


@app.route('/api/process-unified-ai', methods=['POST'])
@csrf.exempt
def process_unified_ai():
    """API endpoint for unified AI processing with real-time progress tracking."""
    try:
        logger.info("Starting unified AI processing endpoint")

        # Get max_questions from request, default to None if not provided
        data = request.get_json()
        max_questions = data.get('max_questions')
        logger.info(f"Received max_questions: {max_questions}")

        # Check session data with detailed logging
        guide_uploaded = session.get('guide_uploaded', False)
        submissions = session.get('submissions', [])
        guide_data = session.get('guide_data')
        guide_content = session.get('guide_raw_content', '')

        logger.info(f"Session data check:")
        logger.info(f"  - guide_uploaded: {guide_uploaded}")
        logger.info(f"  - submissions count: {len(submissions)}")
        logger.info(f"  - guide_data available: {guide_data is not None}")
        logger.info(f"  - guide_content length: {len(guide_content)}")

        # Check if we have the minimum required data
        if not guide_uploaded and not guide_data:
            logger.warning("No guide uploaded or available in session")
            return jsonify({
                'error': 'No marking guide available. Please upload a marking guide first.',
                'details': 'guide_not_uploaded'
            }), 400

        if not submissions or len(submissions) == 0:
            logger.warning("No submissions available in session")
            return jsonify({
                'error': 'No submissions available. Please upload submissions first.',
                'details': 'no_submissions'
            }), 400

        # Get guide and submissions from session or storage
        guide_id = session.get('guide_id')
        submissions = session.get('submissions', [])

        if not guide_id or not submissions:
            return jsonify({'error': 'Missing guide or submissions data'}), 400

        # Check if services are available
        if not mapping_service:
            return jsonify({'error': 'AI services not available'}), 503

        # Get guide content with fallbacks
        if not guide_content:
            # Try alternative sources for guide content
            guide_content = session.get('guide_content', '')
            if not guide_content and guide_data:
                # If we have guide_data but no raw content, try to reconstruct
                questions = guide_data.get('questions', [])
                if questions:
                    guide_content = "\n".join([f"Question {i+1}: {q.get('text', q)}" for i, q in enumerate(questions)])
                    logger.info(f"Reconstructed guide content from questions: {len(guide_content)} chars")

        if not guide_content:
            return jsonify({
                'error': 'Guide content not available. Please re-upload your marking guide.',
                'details': 'guide_content_missing'
            }), 400

        logger.info(f"Starting unified AI processing for {len(submissions)} submissions")

        # Initialize unified AI service with error handling
        try:
            logger.info("Importing unified AI services...")
            from src.services.unified_ai_service import UnifiedAIService
            from src.services.progress_tracker import progress_tracker
            logger.info("Services imported successfully")

            unified_ai_service = UnifiedAIService(
                mapping_service=mapping_service,
                grading_service=grading_service if 'grading_service' in globals() else None,
                llm_service=llm_service if 'llm_service' in globals() else None
            )
            logger.info("Unified AI service created successfully")
        except ImportError as e:
            logger.error(f"Failed to import unified AI services: {str(e)}")
            return jsonify({'error': f'Service import failed: {str(e)}'}), 500
        except Exception as e:
            logger.error(f"Failed to create unified AI service: {str(e)}")
            return jsonify({'error': f'Service creation failed: {str(e)}'}), 500

        # Create progress tracking session with error handling
        try:
            session_id = session.sid  # Use SecureFlaskSession's sid property
            logger.info(f"Creating progress session for {len(submissions)} submissions")
            progress_id = progress_tracker.create_session(session_id, len(submissions))
            logger.info(f"Progress session created: {progress_id}")

            # Store progress ID in session for frontend polling
            session['current_progress_id'] = progress_id

            # Create progress callback
            progress_callback = progress_tracker.create_progress_callback(progress_id)
            logger.info("Progress callback created")
        except Exception as e:
            logger.error(f"Failed to create progress tracking: {str(e)}")
            return jsonify({'error': f'Progress tracking failed: {str(e)}'}), 500

        # Process with unified AI service with detailed error handling
        try:
            logger.info("Starting unified AI processing...")
            result, error = unified_ai_service.process_unified_ai_grading(
                marking_guide_content=guide_content,
                submissions=submissions,
                progress_callback=progress_callback,
                max_questions=max_questions
            )
            logger.info("Unified AI processing completed")

            if error:
                logger.error(f"Unified AI processing returned error: {error}")
                progress_tracker.complete_session(progress_id, success=False, message=error)
                return jsonify({'error': error}), 500
        except Exception as e:
            logger.error(f"Exception during unified AI processing: {str(e)}")
            progress_tracker.complete_session(progress_id, success=False, message=str(e))
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500

        # Mark progress as completed
        progress_tracker.complete_session(progress_id, success=True, message="Processing completed successfully")

        # Extract results for session storage
        grading_results = result.get('results', [])
        summary = result.get('summary', {})

        # Save grading results to database
        logger.info(f"Grading results received: {grading_results}")
        for res in grading_results:
            try:
                # Ensure submission_id is a string
                submission_id_str = str(res.get('submission_id'))
                
                # Fetch the submission from the database
                submission = Submission.query.get(submission_id_str)

                if submission:
                    # Update submission status
                    submission.processing_status = 'completed'
                    db.session.add(submission)

                    # Create and save GradingResult
                    grading_result_db = GradingResult(
                        submission_id=submission_id_str,
                        guide_id=guide_id,
                        overall_score=res.get('score', 0),
                        max_score=res.get('max_score', 0),
                        percentage=res.get('percentage', 0),
                        letter_grade=res.get('letter_grade', 'N/A'),
                        feedback=res.get('feedback', 'No feedback provided'),
                        detailed_results=res.get('detailed_results', {})
                    )
                    db.session.add(grading_result_db)
                    db.session.commit()
                    logger.info(f"Grading result for submission {submission_id_str} saved to DB.")
                else:
                    logger.warning(f"Submission {submission_id_str} not found in DB. Skipping DB save for this result.")
            except Exception as db_e:
                db.session.rollback()
                logger.error(f"Database error saving grading result for {res.get('filename', 'Unknown')}: {str(db_e)}")

        # Update session with results
        session['grading_results'] = grading_results
        session['last_grading_summary'] = summary

        # Update the 'processed' status for submissions in the session and database
        session_submissions = session.get('submissions', [])
        updated_session_submissions = []
        for s in session_submissions:
            submission_id = s.get('id')
            logger.info(f"Processing session submission {submission_id}. Current processed status: {s.get('processed', False)}")
            matching_result = next((res for res in grading_results if res.get('submission_id') == submission_id and res.get('status') != 'error'), None)
            logger.info(f"Matching result for {submission_id}: {matching_result is not None}. Status in grading_results: {next((res.get('status') for res in grading_results if res.get('submission_id') == submission_id), 'N/A')}")

            if matching_result:
                s['processed'] = True
                # Also update in database if it exists there
                try:
                    db_submission = Submission.query.get(submission_id)
                    if db_submission:
                        db_submission.processing_status = 'completed'
                        db.session.add(db_submission)
                        db.session.commit()
                        logger.info(f"Submission {submission_id} status updated to 'completed' in DB.")
                except Exception as db_e:
                    db.session.rollback()
                    logger.error(f"Error updating submission {submission_id} status in DB: {str(db_e)}")
            updated_session_submissions.append(s)
        session['submissions'] = updated_session_submissions

        # Update recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'action': 'Unified AI Processing',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'details': f'Processed {len(submissions)} submissions in {summary.get("processing_time", 0):.1f}s'
        })
        session['recent_activity'] = activity[:10]

        logger.info(f"Unified AI processing completed: {summary.get('average_percentage', 0):.1f}% average")

        return jsonify({
            'success': True,
            'message': result.get('message', 'Processing completed'),
            'results': grading_results,
            'summary': summary,
            'progress_id': progress_id,
            'metadata': result.get('metadata', {})
        })

    except Exception as e:
        logger.error(f"Error in process_unified_ai: {str(e)}")
        return jsonify({'error': f'Unified AI processing failed: {str(e)}'}), 500


@app.route('/api/progress/<progress_id>', methods=['GET'])
@csrf.exempt
def get_progress(progress_id):
    """API endpoint to get real-time progress updates."""
    try:
        from src.services.progress_tracker import progress_tracker

        progress_update = progress_tracker.get_progress(progress_id)

        if not progress_update:
            return jsonify({'error': 'Progress ID not found'}), 404

        # Convert progress update to dictionary
        from dataclasses import asdict
        progress_data = asdict(progress_update)

        return jsonify({
            'success': True,
            'progress': progress_data
        })

    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return jsonify({'error': f'Failed to get progress: {str(e)}'}), 500


@app.route('/api/progress/<progress_id>/history', methods=['GET'])
@csrf.exempt
def get_progress_history(progress_id):
    """API endpoint to get full progress history."""
    try:
        from src.services.progress_tracker import progress_tracker

        history = progress_tracker.get_progress_history(progress_id)

        if not history:
            return jsonify({'error': 'Progress ID not found'}), 404

        # Convert progress updates to dictionaries
        from dataclasses import asdict
        history_data = [asdict(update) for update in history]

        return jsonify({
            'success': True,
            'history': history_data,
            'total_updates': len(history_data)
        })

    except Exception as e:
        logger.error(f"Error getting progress history: {str(e)}")
        return jsonify({'error': f'Failed to get progress history: {str(e)}'}), 500

def get_letter_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 97: return "A+"
    elif score >= 93: return "A"
    elif score >= 90: return "A-"
    elif score >= 87: return "B+"
    elif score >= 83: return "B"
    elif score >= 80: return "B-"
    elif score >= 77: return "C+"
    elif score >= 73: return "C"
    elif score >= 70: return "C-"
    elif score >= 67: return "D+"
    elif score >= 63: return "D"
    elif score >= 60: return "D-"
    else: return "F"

@app.route('/api/process-mapping', methods=['POST'])
@csrf.exempt
def process_mapping():
    """Legacy API endpoint - redirects to AI processing."""
    logger.info("Legacy mapping endpoint called - redirecting to AI processing")
    return process_ai_grading()

@app.route('/api/process-grading', methods=['POST'])
@csrf.exempt
def process_grading():
    """Legacy API endpoint - redirects to AI processing."""
    logger.info("Legacy grading endpoint called - redirecting to AI processing")
    return process_ai_grading()

# Additional routes for enhanced functionality
@app.route('/marking-guides')
@login_required
def marking_guides():
    """View marking guide library with optimized performance and authentication."""
    try:
        guides = []

        # Get stored guides from database (optimized)
        try:
            from src.database.models import MarkingGuide
            current_user = get_current_user()
            if current_user:
                # Use efficient database query
                db_guides = MarkingGuide.query.filter_by(
                    user_id=current_user.id,
                    is_active=True
                ).order_by(MarkingGuide.created_at.desc()).limit(50).all()

                for guide in db_guides:
                    guide_data = {
                        'id': str(guide.id),  # Ensure ID is a string
                        'name': guide.title,  # For backward compatibility
                        'title': guide.title,  # Primary field
                        'filename': guide.filename,
                        'description': guide.description or f'Database guide - {guide.title}',
                        'questions': guide.questions or [],
                        'total_marks': guide.total_marks or 0,
                        'extraction_method': 'database',
                        'created_at': guide.created_at.isoformat(),
                        'created_by': current_user.username,
                        'is_session_guide': False
                    }
                    guides.append(guide_data)
                    logger.debug(f"Added guide to list: ID={guide_data['id']}, Title={guide_data['title']}")
                logger.info(f"Loaded {len(db_guides)} guides from database")
        except Exception as db_error:
            logger.error(f"Error loading guides from database: {str(db_error)}")

        # Calculate statistics
        total_guides = len(guides)
        total_questions = sum(len(guide.get('questions', [])) for guide in guides)
        total_marks_all = sum(guide.get('total_marks', 0) for guide in guides)

        # Get extraction method statistics
        extraction_methods = {}
        for guide in guides:
            method = guide.get('extraction_method', 'unknown')
            extraction_methods[method] = extraction_methods.get(method, 0) + 1

        # Ensure all guides have proper fields and valid IDs
        valid_guides = []
        for guide in guides:
            if 'extraction_method' not in guide or not guide['extraction_method']:
                guide['extraction_method'] = 'unknown'

            # Ensure ID is valid and not None
            if not guide.get('id') or guide['id'] in [None, 'None', '']:
                logger.warning(f"Guide with invalid ID found, skipping: {guide}")
                continue  # Skip guides with invalid IDs

            # Ensure title/name exists
            if not guide.get('title') and not guide.get('name'):
                guide['title'] = guide.get('filename', 'Untitled Guide')
                guide['name'] = guide['title']

            # Sanitize text fields to prevent JSON parsing issues
            def sanitize_text(text):
                if not text:
                    return text
                # Remove control characters that can break JSON
                import re
                # Remove control characters except tab, newline, and carriage return
                text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(text))
                return text

            # Sanitize all text fields
            guide['title'] = sanitize_text(guide.get('title', ''))
            guide['name'] = sanitize_text(guide.get('name', ''))
            guide['filename'] = sanitize_text(guide.get('filename', ''))
            guide['description'] = sanitize_text(guide.get('description', ''))
            guide['created_by'] = sanitize_text(guide.get('created_by', ''))

            # Sanitize questions if they exist
            if guide.get('questions'):
                for question in guide['questions']:
                    if isinstance(question, dict):
                        for key, value in question.items():
                            if isinstance(value, str):
                                question[key] = sanitize_text(value)

            valid_guides.append(guide)

        guides = valid_guides  # Use only valid guides

        context = {
            'page_title': 'Marking Guide Library',
            'guides': guides,
            'saved_guides': guides,  # Template expects this variable
            'current_guide': session.get('guide_filename', None),
            'statistics': {
                'total_guides': total_guides,
                'total_questions': total_questions,
                'total_marks': total_marks_all,
                'extraction_methods': extraction_methods
            }
        }

        return render_template('marking_guides.html', **context)
    except Exception as e:
        logger.error(f"Error loading guide library: {str(e)}")
        flash('Error loading guide library. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/create-guide')
def create_guide():
    """Create new marking guide."""
    try:
        context = {
            'page_title': 'Create Marking Guide'
        }
        return render_template('create_guide.html', **context)
    except Exception as e:
        logger.error(f"Error loading create guide page: {str(e)}")
        flash('Error loading create guide page. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/guide/<guide_id>')
@login_required
def view_guide_content(guide_id):
    """View detailed content of a specific marking guide"""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash('Please log in to view guides', 'error')
            return redirect(url_for('auth.login'))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()

        if not guide:
            flash('Marking guide not found', 'error')
            return redirect(url_for('marking_guides'))

        # Prepare context for template
        context = {
            'page_title': f'Guide: {guide.title}',
            'guide': guide,
            'filename': guide.filename,
            'raw_content': guide.content_text or 'No content available',
            'questions': guide.questions or [],
            'total_marks': guide.total_marks or 0,
            'created_at': guide.created_at.isoformat() if guide.created_at else None
        }

        return render_template('guide_content.html', **context)

    except Exception as e:
        logger.error(f"Error viewing guide content: {str(e)}")
        flash('Error loading guide content. Please try again.', 'error')
        return redirect(url_for('marking_guides'))

@app.route('/use_guide/<guide_id>')
@login_required
def use_guide(guide_id):
    """Set active marking guide for the session and enable dashboard components"""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash('Please log in to use guides', 'error')
            return redirect(url_for('auth.login'))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()

        if not guide:
            flash('Marking guide not found', 'error')
            return redirect(url_for('marking_guides'))

        # Set comprehensive session data for dashboard activation
        session['guide_id'] = guide.id
        session['guide_uploaded'] = True  # Critical for dashboard component activation
        session['guide_filename'] = guide.filename or guide.title
        session['guide_content'] = guide.content_text or ''
        session['guide_raw_content'] = guide.content_text or ''

        # Set guide data structure for AI processing
        session['guide_data'] = {
            'filename': guide.filename or guide.title,
            'questions': guide.questions or [],
            'total_marks': guide.total_marks or 0,
            'extraction_method': 'database',
            'processed_at': guide.created_at.isoformat() if guide.created_at else datetime.now().isoformat()
        }

        # Set current guide for backward compatibility
        session['current_guide'] = {
            'id': guide.id,
            'name': guide.title,
            'description': guide.description,
            'total_marks': guide.total_marks
        }

        session.modified = True

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'guide_loaded',
            'message': f'Loaded marking guide: {guide.title}',
            'timestamp': datetime.now().isoformat(),
            'icon': 'check'
        })
        session['recent_activity'] = activity[:10]

        logger.info(f"Guide loaded successfully: {guide.title} (ID: {guide.id})")
        flash(f'Marking guide "{guide.title}" loaded successfully! Dashboard components are now active.', 'success')
        return redirect(url_for('dashboard'))

    except SQLAlchemyError as e:
        logger.error(f"Database error in use_guide: {str(e)}")
        flash('Error accessing guide database', 'error')
        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Unexpected error in use_guide: {str(e)}")
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('marking_guides'))

@app.route('/clear-session-guide', methods=['GET', 'POST'])
@login_required
def clear_session_guide():
    """Clear the current session guide."""
    try:
        session.pop('guide_data', None)
        session.pop('guide_filename', None)
        session.pop('guide_raw_content', None)
        session.pop('guide_uploaded', None)
        session.pop('guide_id', None)
        session.modified = True
        flash('Session guide cleared successfully.', 'success')
        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Error clearing session guide: {str(e)}")
        flash('Error clearing session guide. Please try again.', 'error')
        return redirect(url_for('marking_guides'))

@app.route('/view-submission/<submission_id>')
def view_submission_content(submission_id):
    """View content of a specific submission."""
    try:
        submissions = session.get('submissions', [])
        logger.info(f"Attempting to view submission {submission_id}. Total submissions in session: {len(submissions)}")
        submission = next((s for s in submissions if s.get('id') == submission_id), None)

        if not submission:
            logger.warning(f"Submission {submission_id} not found in session.")

        if not submission:
            flash('Submission not found.', 'error')
            return redirect(url_for('view_submissions'))

        logger.info(f"Found submission {submission_id}. Filename: {submission.get('filename')}, Raw text length: {len(submission.get('raw_text', ''))}")

        context = {
            'page_title': f'Submission: {submission.get("filename", "Unknown")}',
            'submission_id': submission_id,
            'filename': submission.get('filename', 'Unknown'),
            'raw_text': submission.get('raw_text', ''),
            'extracted_answers': submission.get('extracted_answers', {}),
            'processed': submission.get('processed', False),
            'uploaded_at': submission.get('upload_date', ''),
            'file_size': submission.get('size_mb', 0) * 1024  # Convert to KB
        }
        return render_template('submission_content.html', **context)
    except Exception as e:
        logger.error(f"Error viewing submission content: {str(e)}")
        flash('Error loading submission content. Please try again.', 'error')
        return redirect(url_for('view_submissions'))

@app.route('/settings')
def settings():
    """Application settings page."""
    try:
        # Default settings
        default_settings = {
            'max_file_size': 16,
            'allowed_formats': ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'],
            'auto_process': True,
            'save_temp_files': False,
            'notification_level': 'all',
            'theme': 'light',
            'language': 'en'
        }

        # Available options
        available_formats = ['.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
        notification_levels = [
            {'value': 'all', 'label': 'All Notifications'},
            {'value': 'important', 'label': 'Important Only'},
            {'value': 'errors', 'label': 'Errors Only'},
            {'value': 'none', 'label': 'No Notifications'}
        ]
        themes = [
            {'value': 'light', 'label': 'Light Theme'},
            {'value': 'dark', 'label': 'Dark Theme'},
            {'value': 'auto', 'label': 'Auto (System)'}
        ]
        languages = [
            {'value': 'en', 'label': 'English'},
            {'value': 'es', 'label': 'Spanish'},
            {'value': 'fr', 'label': 'French'},
            {'value': 'de', 'label': 'German'}
        ]

        context = {
            'page_title': 'Settings',
            'settings': default_settings,
            'available_formats': available_formats,
            'notification_levels': notification_levels,
            'themes': themes,
            'languages': languages,
            'service_status': get_service_status(),
            'storage_stats': get_storage_stats()
        }
        return render_template('settings.html', **context)
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        flash('Error loading settings. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/export-results')
@csrf.exempt
def export_results():
    """API endpoint to export grading results."""
    try:
        if not session.get('grading_results'):
            return jsonify({
                'success': False,
                'error': 'No grading results available'
            }), 404

        grading_results = session.get('grading_results', {})

        # Format data for export
        export_data = {
            'batch_summary': {
                'total_submissions': len(grading_results),
                'average_score': session.get('last_score', 0),
                'timestamp': datetime.now().isoformat(),
                'guide_id': session.get('guide_id', ''),
                'guide_filename': session.get('guide_filename', '')
            },
            'results': []
        }

        # Add individual results
        for submission_id, result in grading_results.items():
            export_data['results'].append({
                'submission_id': submission_id,
                'filename': result.get('filename', 'Unknown'),
                'score': result.get('score', 0),
                'letter_grade': result.get('letter_grade', 'F'),
                'feedback': result.get('feedback', ''),
                'strengths': result.get('strengths', []),
                'weaknesses': result.get('weaknesses', []),
                'question_scores': result.get('question_scores', []),
                'timestamp': result.get('timestamp', datetime.now().isoformat())
            })

        # Generate filename for export
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"exam_results_{timestamp}.json"

        # Note: results_storage service is not available
        # Results are returned directly to the client
        logger.info(f"Results prepared for export: {filename}")

        return jsonify({
            'success': True,
            'message': 'Results exported successfully',
            'filename': filename,
            'data': export_data
        })

    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/delete-guide/<guide_id>')
@login_required
def delete_guide(guide_id):
    """Delete a marking guide (legacy route for backward compatibility)."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash('Please log in to delete guides', 'error')
            return redirect(url_for('auth.login'))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()

        if not guide:
            flash('Marking guide not found', 'error')
            return redirect(url_for('marking_guides'))

        # Store guide name for flash message
        guide_name = guide.title

        # Check if this guide is currently active in session
        current_guide_id = session.get('guide_id')
        was_active_guide = str(current_guide_id) == str(guide_id)

        # Delete the guide
        db.session.delete(guide)
        db.session.commit()

        # Clear session if this was the active guide
        if was_active_guide:
            session.pop('guide_id', None)
            session.pop('guide_uploaded', None)
            session.pop('guide_filename', None)
            session.pop('guide_data', None)
            session.modified = True
            logger.info(f"Cleared active guide from session: {guide_name}")
            flash(f'Active guide "{guide_name}" deleted and cleared from session', 'warning')
        else:
            flash(f'Marking guide "{guide_name}" deleted successfully', 'success')

        logger.info(f"Guide deleted successfully: {guide_name} (ID: {guide_id})")
        return redirect(url_for('marking_guides'))

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_guide: {str(e)}")
        db.session.rollback()
        flash('Error deleting guide from database', 'error')
        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Unexpected error in delete_guide: {str(e)}")
        flash('An unexpected error occurred while deleting the guide', 'error')
        return redirect(url_for('marking_guides'))

@app.route('/api/delete-guide', methods=['POST'])
@csrf.exempt
@login_required
def api_delete_guide():
    """AJAX endpoint to delete a marking guide."""
    try:
        # Get guide ID from request
        data = request.get_json()
        if not data or 'guide_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Guide ID is required'
            }), 400

        guide_id = data['guide_id']

        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()

        if not guide:
            return jsonify({
                'success': False,
                'error': 'Marking guide not found'
            }), 404

        # Store guide name for response
        guide_name = guide.title

        # Check if this guide is currently active in session
        current_guide_id = session.get('guide_id')
        was_active_guide = str(current_guide_id) == str(guide_id)

        # Delete the guide
        db.session.delete(guide)
        db.session.commit()

        # Clear session if this was the active guide
        if was_active_guide:
            session.pop('guide_id', None)
            session.pop('guide_uploaded', None)
            session.pop('guide_filename', None)
            session.pop('guide_data', None)
            session.modified = True
            logger.info(f"Cleared active guide from session: {guide_name}")

        logger.info(f"Guide deleted successfully via API: {guide_name} (ID: {guide_id})")

        return jsonify({
            'success': True,
            'message': f'Marking guide "{guide_name}" deleted successfully',
            'guide_id': guide_id,
            'guide_name': guide_name,
            'was_active_guide': was_active_guide  # Tell frontend if this was the active guide
        })

    except SQLAlchemyError as e:
        logger.error(f"Database error in api_delete_guide: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error occurred while deleting guide'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in api_delete_guide: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@app.route('/api/service-status')
@csrf.exempt
def api_service_status():
    """API endpoint to check service status asynchronously."""
    try:
        status = get_service_status()
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': {
                'ocr_status': False,
                'llm_status': False,
                'storage_status': False,
                'config_status': True
            }
        }), 500

@app.route('/api/delete-submission', methods=['POST'])
@csrf.exempt
def delete_submission():
    """API endpoint to delete a submission."""
    try:
        logger.info(f"Delete submission request - Headers: {request.headers}")
        logger.info(f"Delete submission request - Data: {request.data}")
        submission_id = request.json.get('submission_id')
        if not submission_id:
            logger.warning("Delete submission: No submission_id provided.")
            return jsonify({'success': False, 'message': 'No submission ID provided.'}), 400

        # Try to delete from database first
        submission = Submission.query.get(submission_id)
        if submission:
            db.session.delete(submission)
            db.session.commit()
            logger.info(f"Submission {submission_id} deleted successfully from database.")
            add_recent_activity('submission_deleted', f'Submission {submission_id[:8]}... deleted.', 'trash')
            return jsonify({'success': True, 'message': 'Submission deleted successfully.'})
        else:
            # Fallback to session if not found in DB (e.g., old session data)
            submissions = session.get('submissions', [])
            initial_len = len(submissions)
            submissions = [s for s in submissions if s.get('id') != submission_id]
            session['submissions'] = submissions

            if len(submissions) < initial_len:
                logger.info(f"Submission {submission_id} deleted successfully from session.")
                add_recent_activity('submission_deleted', f'Submission {submission_id[:8]}... deleted.', 'trash')
                return jsonify({'success': True, 'message': 'Submission deleted successfully.'})
            else:
                logger.warning(f"Submission {submission_id} not found for deletion.")
                return jsonify({'success': False, 'message': 'Submission not found.'}), 404

    except Exception as e:
        logger.error(f"Error deleting submission: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error.'}), 500


@app.route('/api/delete-grading-result', methods=['POST'])
@csrf.exempt
def delete_grading_result():
    """API endpoint to delete a grading result."""
    try:
        grading_result_id = request.json.get('grading_result_id')
        if not grading_result_id:
            logger.warning("Delete grading result: No grading_result_id provided.")
            return jsonify({'success': False, 'message': 'No grading result ID provided.'}), 400

        grading_result = GradingResult.query.get(grading_result_id)
        if grading_result:
            db.session.delete(grading_result)
            db.session.commit()
            logger.info(f"Grading result {grading_result_id} deleted successfully from database.")
            add_recent_activity('grading_result_deleted', f'Grading result {grading_result_id[:8]}... deleted.', 'trash')
            return jsonify({'success': True, 'message': 'Grading result deleted successfully.'})
        else:
            logger.warning(f"Grading result {grading_result_id} not found for deletion.")
            return jsonify({'success': False, 'message': 'Grading result not found.'}), 404

    except Exception as e:
        logger.error(f"Error deleting grading result: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error.'}), 500


@app.route('/api/clear-cache', methods=['POST'])
@csrf.exempt
def clear_cache():
    """API endpoint to clear application cache."""
    try:
        from utils.cache import cache_clear, cache_stats

        # Get cache stats before clearing
        stats_before = cache_stats()

        # Clear the cache
        cache_clear()

        # Get stats after clearing
        stats_after = cache_stats()

        logger.info(f"Cache cleared successfully. Entries before: {stats_before.get('total_entries', 0)}, after: {stats_after.get('total_entries', 0)}")

        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'stats': {
                'entries_cleared': stats_before.get('total_entries', 0),
                'cache_size_before': stats_before.get('total_entries', 0),
                'cache_size_after': stats_after.get('total_entries', 0)
            }
        })

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing cache: {str(e)}'
        }), 500


@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """API endpoint to get cache statistics."""
    try:
        from utils.cache import cache_stats

        stats = cache_stats()

        return jsonify({
            'status': 'ok',
            'cache_stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting cache stats: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("[START] Starting Exam Grader Web Application...")

    # Get configuration values
    host = getattr(config, 'HOST', '127.0.0.1')
    port = getattr(config, 'PORT', 5000)
    debug = getattr(config, 'DEBUG', True)

    print(f"[DASHBOARD] Dashboard: http://{host}:{port}")
    print(f"[DEBUG] Debug mode: {debug}")

    app.run(
        host=host,
        port=port,
        debug=debug
    )
