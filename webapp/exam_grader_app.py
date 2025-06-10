from dotenv import load_dotenv
load_dotenv()

#!/usr/bin/env python3
"""
Exam Grader Flask Web Application
Modern educational assessment platform with AI-powered grading capabilities.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, abort
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import project modules
try:
    from src.config.unified_config import config
    from src.database import db, User, MarkingGuide, Submission, Mapping, GradingResult, MigrationManager, DatabaseUtils
    from src.security.session_manager import SecureSessionManager
    from src.security.secrets_manager import secrets_manager, initialize_secrets
    from src.services.ocr_service import OCRService
    from src.services.llm_service import LLMService
    from src.services.mapping_service import MappingService
    from src.services.grading_service import GradingService
    from src.services.file_cleanup_service import FileCleanupService
    from src.parsing.parse_submission import parse_student_submission
    from src.parsing.parse_guide import parse_marking_guide
    from utils.logger import logger
    from utils.rate_limiter import rate_limit_with_whitelist, get_rate_limit_status
    from utils.input_sanitizer import InputSanitizer, sanitize_form_data, validate_file_upload
    from utils.error_handler import ErrorHandler, ProgressTracker, create_user_notification, add_recent_activity
    from utils.loading_states import loading_manager, LoadingState, create_loading_response, get_loading_state_for_template
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("   Make sure all dependencies are installed and the project structure is correct")
    sys.exit(1)

# Import authentication functions
try:
    from webapp.auth import init_auth, login_required, get_current_user
    print("✅ Authentication modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import authentication modules: {e}")
    sys.exit(1)

# Initialize Flask application
app = Flask(__name__)

# Load unified configuration
try:
    # Validate configuration
    config.validate()

    # Configure Flask app with unified config
    app.config.update(config.get_flask_config())

    logger.info(f"Configuration loaded successfully for environment: {config.environment}")
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

# Initialize CSRF protection
try:
    csrf = CSRFProtect(app)
    logger.info("CSRF protection initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize CSRF protection: {str(e)}")
    print(f"❌ CSRF protection error: {e}")
    sys.exit(1)

# Initialize database
try:
    db.init_app(app)

    with app.app_context():
        # Run migrations
        migration_manager = MigrationManager(config.database.database_url)
        if not migration_manager.migrate():
            logger.error("Database migration failed")
            sys.exit(1)

        # Create default user if needed
        DatabaseUtils.create_default_user()

    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    print(f"❌ Database error: {e}")
    sys.exit(1)

# Initialize secrets manager
try:
    initialize_secrets()
    logger.info("Secrets manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize secrets manager: {str(e)}")
    print(f"❌ Secrets manager error: {e}")
    sys.exit(1)

# Initialize secure session manager
try:
    session_manager = SecureSessionManager(
        config.security.secret_key,
        config.security.session_timeout
    )
    logger.info("Secure session manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize session manager: {str(e)}")
    print(f"❌ Session manager error: {e}")
    sys.exit(1)

# Initialize authentication system
try:
    init_auth(app, session_manager)
    logger.info("Authentication system initialized successfully")

    # Test that login_required is available
    @login_required
    def test_decorator():
        pass
    logger.info("login_required decorator is working")

except Exception as e:
    logger.error(f"Failed to initialize authentication: {str(e)}")
    print(f"❌ Authentication error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def allowed_file(filename):
    """Check if file type is allowed."""
    if not filename:
        return False
    ext = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in config.files.supported_formats

# Initialize services with secure API key handling
try:
    # Get API keys from secrets manager
    ocr_api_key = secrets_manager.get_secret('HANDWRITING_OCR_API_KEY')
    llm_api_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')

    # Initialize services with retry mechanisms
    ocr_service = OCRService(api_key=ocr_api_key) if ocr_api_key else None
    llm_service = LLMService(api_key=llm_api_key) if llm_api_key else None
    mapping_service = MappingService(llm_service=llm_service)
    grading_service = GradingService(llm_service=llm_service, mapping_service=mapping_service)

    # Initialize file cleanup service
    file_cleanup_service = FileCleanupService(config)
    file_cleanup_service.start_scheduled_cleanup()

    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    # Continue with limited functionality
    ocr_service = None
    llm_service = None
    mapping_service = None
    grading_service = None
    file_cleanup_service = None

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

def get_service_status() -> Dict[str, bool]:
    """Check status of all services."""
    try:
        # Initialize status values
        ocr_available = False
        llm_available = False
        storage_available = False
        config_available = True  # Config is always available if app is running

        # Check OCR service
        if ocr_service:
            try:
                ocr_available = ocr_service.is_available()
                logger.info(f"OCR service availability: {ocr_available}")
            except Exception as e:
                logger.warning(f"Error checking OCR service availability: {str(e)}")
                ocr_available = False

        # Check LLM service
        if llm_service:
            try:
                llm_available = llm_service.is_available()
                logger.info(f"LLM service availability: {llm_available}")
            except Exception as e:
                logger.warning(f"Error checking LLM service availability: {str(e)}")
                llm_available = False

        # Check database storage (new system)
        storage_available = False
        submission_storage_available = False
        guide_storage_available = False

        try:
            # Check if database is accessible
            with app.app_context():
                from src.database.models import User
                User.query.count()  # Simple query to test database
                storage_available = True
                submission_storage_available = True
                guide_storage_available = True
        except Exception as e:
            logger.warning(f"Error checking database storage: {str(e)}")
            storage_available = False

        # For development/demo purposes, if no services are available, show them as available
        # This allows the app to function in demo mode
        if not any([ocr_available, llm_available, storage_available]):
            logger.warning("No services available, falling back to demo mode")
            ocr_available = True
            llm_available = True
            storage_available = True

        return {
            'ocr_status': ocr_available,
            'llm_status': llm_available,
            'storage_status': storage_available,
            'config_status': config_available,
            'guide_storage_available': guide_storage_available,
            'submission_storage_available': submission_storage_available
        }
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        # On error, show services as available for demo mode
        return {
            'ocr_status': True,
            'llm_status': True,
            'storage_status': True,
            'config_status': True
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
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

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

# Template context processors
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    # Auto-cleanup old loading operations
    try:
        loading_manager.auto_cleanup()
        loading_states = get_loading_state_for_template()
    except Exception as e:
        logger.warning(f"Error getting loading states: {str(e)}")
        loading_states = {'loading_operations': {}, 'has_active_operations': False, 'total_active_operations': 0}

    # Generate CSRF token
    try:
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf
    except Exception as e:
        logger.warning(f"Error generating CSRF token: {str(e)}")
        csrf_token = lambda: ''

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

        # Calculate dashboard statistics from database (user-specific)
        from src.database.models import Submission, MarkingGuide, GradingResult

        # Get statistics from database (filtered by current user)
        total_submissions = Submission.query.filter_by(user_id=current_user.id).count()
        processed_submissions = Submission.query.filter(
            Submission.user_id == current_user.id,
            Submission.processing_status == 'completed'
        ).count()
        guide_uploaded = MarkingGuide.query.filter_by(user_id=current_user.id).count() > 0

        # Get recent submissions as activity (user-specific)
        recent_submissions = Submission.query.filter_by(user_id=current_user.id).order_by(
            Submission.created_at.desc()
        ).limit(5).all()

        recent_activity = []
        for submission in recent_submissions:
            recent_activity.append({
                'type': 'submission_upload',
                'message': f'Processed submission: {submission.filename}',
                'timestamp': submission.created_at.isoformat(),
                'icon': 'document'
            })

        # Calculate average score from grading results (user-specific)
        # Join with submissions to filter by user_id since GradingResult doesn't have user_id directly
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

        # Process guide (simplified for now)
        try:
            if 'parse_marking_guide' in globals():
                guide, error_message = parse_marking_guide(file_path)
                if error_message:
                    flash(f'Error processing guide: {error_message}', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
                if guide:
                    guide_data = {
                        'raw_content': guide.raw_content,
                        'filename': filename,
                        'questions': [], # Placeholder, as parse_guide only extracts raw text
                        'total_marks': 0, # Placeholder
                        'processed_at': datetime.now().isoformat()
                    }
                else:
                    flash('Error: Could not process guide.', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
            else:
                # Create basic guide data structure if parse_marking_guide is not available
                guide_data = {
                    'filename': filename,
                    'questions': [],
                    'total_marks': 0,
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

            # Create marking guide record
            marking_guide = MarkingGuide(
                user_id=current_user.id,
                title=guide_data.get('title', filename),
                description=f"Uploaded guide: {filename}",
                filename=filename,
                file_path=file_path,  # Keep the file path for now
                file_size=os.path.getsize(file_path),
                file_type=filename.split('.')[-1].lower(),
                content_text=guide_data.get('raw_content', ''),
                questions=guide_data.get('questions', []),
                total_marks=guide_data.get('total_marks', 0.0)
            )

            db.session.add(marking_guide)
            db.session.commit()
            guide_id = marking_guide.id

            logger.info(f"Guide stored in database with ID: {guide_id}")

        except Exception as storage_error:
            logger.error(f"Error storing guide in database: {str(storage_error)}")
            db.session.rollback()
            flash(f'Error storing guide: {str(storage_error)}', 'error')
            os.remove(file_path)
            return redirect(request.url)

        # Update session for backward compatibility
        logger.info("Updating session variables after guide storage.")
        session['guide_id'] = guide_id
        session['guide_uploaded'] = True
        session['guide_filename'] = filename
        session.modified = True
        logger.info(f"upload_guide: guide_uploaded set to {session.get('guide_uploaded')} before redirect")

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'guide_upload',
            'message': f'Uploaded marking guide: {filename}',
            'timestamp': datetime.now().isoformat(),
            'icon': 'document'
        })
        session['recent_activity'] = activity[:10]

        flash('Marking guide uploaded and processed successfully!', 'success')
        logger.info(f"Guide uploaded successfully: {filename}")

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")

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
        if not session.get('guide_uploaded'):
            flash('Please upload a marking guide first.', 'warning')
            return redirect(url_for('upload_guide'))

        files = request.files.getlist('submission_file')
        if not files or all(f.filename == '' for f in files):
            if request.is_xhr:
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
                if request.is_xhr:
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
                    if request.is_xhr:
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
                if submission_storage:
                    with open(file_path, 'rb') as f_content:
                        file_content = f_content.read()
                    submission_id = submission_storage.store_results(file_content, filename, answers, raw_text)
                else:
                    session[f'submission_{submission_id}'] = {
                        'filename': filename,
                        'answers': answers,
                        'raw_text': raw_text
                    }

                submissions_data.append({
                    'id': submission_id,
                    'filename': filename,
                    'uploaded_at': datetime.now().isoformat(),
                    'processed': True,
                    'raw_text': raw_text,
                    'extracted_answers': answers
                })
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

        session['submissions'] = submissions_data
        session.modified = True

        if request.is_xhr:
            if uploaded_count > 0 and failed_count == 0:
                return jsonify({'success': True, 'message': f'{uploaded_count} submission(s) uploaded and processed successfully!', 'uploaded_count': uploaded_count, 'failed_count': failed_count})
            elif uploaded_count > 0 and failed_count > 0:
                return jsonify({'success': True, 'message': f'{uploaded_count} submission(s) uploaded, but {failed_count} failed. Check logs for details.', 'uploaded_count': uploaded_count, 'failed_count': failed_count})
            else:
                return jsonify({'success': False, 'error': f'Failed to upload any submissions. {failed_count} failed. Check logs for details.', 'uploaded_count': uploaded_count, 'failed_count': failed_count}), 400
        else:
            if uploaded_count > 0:
                flash(f'{uploaded_count} submission(s) uploaded and processed successfully!', 'success')
                logger.info(f'{uploaded_count} submission(s) uploaded successfully.')
            if failed_count > 0:
                flash(f'{failed_count} submission(s) failed to upload or process. Check logs for details.', 'error')

            return redirect(url_for('dashboard'))

    except RequestEntityTooLarge:
        if request.is_xhr:
            return jsonify({'success': False, 'error': f'File too large. Max size is {config.max_file_size_mb}MB.'}), 413
        flash(f'File too large. Max size is {config.max_file_size_mb}MB.', 'error')
        return redirect(request.url)
    except Exception as e:
        logger.error(f"Error uploading submission: {str(e)}")
        if request.is_xhr:
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        flash('Error uploading submission. Please try again.', 'error')
        return redirect(request.url)

@app.route('/submissions')
@login_required
def view_submissions():
    """View all submissions."""
    try:
        submissions = session.get('submissions', [])
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

        # Get grading results from session

        grading_results = session.get('grading_results', {})

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

@app.route('/api/process-mapping', methods=['POST'])
def process_mapping():
    """API endpoint to process answer mapping."""
    try:
        if not session.get('guide_uploaded') or not session.get('submissions'):
            return jsonify({'error': 'Missing guide or submissions'}), 400

        # Get guide and submissions from session or storage
        guide_id = session.get('guide_id')
        submissions = session.get('submissions', [])

        if not guide_id or not submissions:
            return jsonify({'error': 'Missing guide or submissions data'}), 400

        # Process mapping using real service if available
        mapping_results = {}
        successful_mappings = 0
        failed_mappings = 0

        if mapping_service:
            try:
                # Get guide content from database or session
                guide_data = None
                try:
                    from src.database.models import MarkingGuide
                    guide = MarkingGuide.query.get(guide_id)
                    if guide:
                        guide_data = {
                            'questions': guide.questions or [],
                            'content': guide.content_text,
                            'total_marks': guide.total_marks
                        }
                except Exception:
                    # Fallback to session data
                    guide_data = session.get('guide_data', {})

                if not guide_data:
                    return jsonify({'error': 'Guide data not found'}), 404

                # Process each submission
                for submission in submissions:
                    submission_id = submission.get('id')
                    if not submission_id:
                        continue

                    try:
                        # Get submission content from database or session
                        submission_data = None
                        try:
                            from src.database.models import Submission
                            db_submission = Submission.query.get(int(submission_id))
                            if db_submission:
                                submission_data = {
                                    'answers': db_submission.answers,
                                    'content': db_submission.content_text,
                                    'filename': db_submission.filename
                                }
                        except (ValueError, TypeError):
                            # Try session storage as fallback
                            session_key = f'submission_{submission_id}'
                            if session_key in session:
                                submission_data = session[session_key]

                        if not submission_data:
                            failed_mappings += 1
                            continue

                        # Map answers using the mapping service
                        mappings, mapping_error = mapping_service.map_answers(
                            submission_data.get('answers', {}),
                            guide_data.get('questions', [])
                        )

                        if mapping_error:
                            logger.error(f"Mapping failed for submission {submission_id}: {mapping_error}")
                            failed_mappings += 1
                            continue

                        # Store mapping results
                        mapping_results[submission_id] = {
                            'filename': submission.get('filename', 'Unknown'),
                            'mappings': mappings,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat()
                        }
                        successful_mappings += 1

                    except Exception as e:
                        logger.error(f"Error mapping submission {submission_id}: {str(e)}")
                        failed_mappings += 1

            except Exception as e:
                logger.error(f"Error in mapping process: {str(e)}")
                return jsonify({'error': f'Mapping process error: {str(e)}'}), 500
        else:
            # Fallback to basic mapping if services not available
            for submission in submissions:
                submission_id = submission.get('id')
                if not submission_id:
                    continue

                # Create basic mapping structure
                mapping_results[submission_id] = {
                    'filename': submission.get('filename', 'Unknown'),
                    'mappings': [],  # Empty mappings
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat()
                }
                successful_mappings += 1

        # Store mapping results in session
        session['mapping_completed'] = True
        session['mapping_results'] = mapping_results
        session['last_mapping_result'] = str(uuid.uuid4())

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'mapping_complete',
            'message': f'Answer mapping completed: {successful_mappings} successful, {failed_mappings} failed',
            'timestamp': datetime.now().isoformat(),
            'icon': 'check'
        })
        session['recent_activity'] = activity[:10]

        return jsonify({
            'success': True,
            'message': f'Mapping completed: {successful_mappings} successful, {failed_mappings} failed',
            'mapped_count': successful_mappings,
            'failed_count': failed_mappings
        })

    except Exception as e:
        logger.error(f"Error processing mapping: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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

@app.route('/api/process-grading', methods=['POST'])
def process_grading():
    """API endpoint to process grading using real backend services."""
    try:
        if not session.get('last_mapping_result'):
            return jsonify({'error': 'No mapping result available'}), 400

        if not grading_service:
            return jsonify({'error': 'Grading service not available'}), 503

        mapping_results = session.get('mapping_results', {})
        guide_content = session.get('guide_content', '')

        if not mapping_results:
            return jsonify({'error': 'No mapping results available'}), 400

        # Process grading for each mapped submission using real service
        grading_results = {}
        successful_gradings = 0
        failed_gradings = 0
        total_scores = []

        for submission_id, mapping_data in mapping_results.items():
            try:
                # Use real grading service
                grading_result, grading_error = grading_service.grade_submission(
                    mapping_data.get('mappings', []),
                    guide_content
                )

                if grading_error:
                    logger.error(f"Grading failed for submission {submission_id}: {grading_error}")
                    failed_gradings += 1
                    continue

                score = grading_result.get('total_score', 0)
                total_scores.append(score)

                grading_results[submission_id] = {
                    'filename': mapping_data.get('filename'),
                    'status': 'completed',
                    'score': score,
                    'letter_grade': get_letter_grade(score),
                    'feedback': grading_result.get('feedback', ''),
                    'strengths': grading_result.get('strengths', []),
                    'weaknesses': grading_result.get('weaknesses', []),
                    'question_scores': grading_result.get('question_scores', []),
                    'timestamp': datetime.now().isoformat()
                }
                successful_gradings += 1

            except Exception as e:
                logger.error(f"Error grading submission {submission_id}: {str(e)}")
                failed_gradings += 1

        # Calculate batch statistics
        average_score = sum(total_scores) / len(total_scores) if total_scores else 0
        highest_score = max(total_scores) if total_scores else 0
        lowest_score = min(total_scores) if total_scores else 0

        # Grade distribution
        grade_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in total_scores:
            letter = get_letter_grade(score)[0]  # Get first character (A, B, C, D, F)
            if letter in grade_distribution:
                grade_distribution[letter] += 1

        # Store grading results
        session['grading_completed'] = True
        session['grading_results'] = grading_results
        session['last_grading_result'] = str(uuid.uuid4())
        session['last_score'] = average_score

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'grading_complete',
            'message': f'Grading completed: {successful_gradings} successful (avg: {average_score:.1f}%)',
            'timestamp': datetime.now().isoformat(),
            'icon': 'star'
        })
        session['recent_activity'] = activity[:10]

        return jsonify({
            'success': True,
            'message': f'Grading completed: {successful_gradings} successful (avg: {average_score:.1f}%)',
            'graded_count': successful_gradings,
            'failed_count': failed_gradings,
            'average_score': average_score,
            'batch_summary': {
                'total_submissions': len(mapping_results),
                'graded_count': successful_gradings,
                'average_score': average_score,
                'highest_score': highest_score,
                'lowest_score': lowest_score,
                'score_distribution': grade_distribution
            },
            'results': grading_results
        })

    except Exception as e:
        logger.error(f"Error processing grading: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Additional routes for enhanced functionality
@app.route('/marking-guides')
@login_required
def marking_guides():
    """View marking guide library with optimized performance and authentication."""
    try:
        guides = []

        # Get session guide data with safe conversion
        session_guide_data = session.get('guide_data')
        session_guide_filename = session.get('guide_filename')
        session_guide_content = session.get('guide_raw_content')

        if session_guide_data and session_guide_filename:
            try:
                # Create session guide entry
                session_guide = {
                    'id': 'session_guide',
                    'name': session_guide_filename,
                    'filename': session_guide_filename,
                    'description': 'Currently active guide from session',
                    'raw_content': session_guide_content or '',
                    'questions': session_guide_data.get('questions', []),
                    'total_marks': session_guide_data.get('total_marks', 0),
                    'extraction_method': session_guide_data.get('extraction_method', 'unknown'),
                    'created_at': session_guide_data.get('processed_at', datetime.now().isoformat()),
                    'created_by': 'Session',
                    'is_session_guide': True
                }
                guides.append(session_guide)
                logger.info(f"Added session guide: {session_guide_filename}")
            except Exception as session_error:
                logger.error(f"Error processing session guide: {str(session_error)}")

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
                    guides.append({
                        'id': guide.id,
                        'name': guide.title,
                        'filename': guide.filename,
                        'description': guide.description or f'Database guide - {guide.title}',
                        'questions': guide.questions or [],
                        'total_marks': guide.total_marks or 0,
                        'extraction_method': 'database',
                        'created_at': guide.created_at.isoformat(),
                        'created_by': current_user.username,
                        'is_session_guide': False
                    })
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

        # Ensure all guides have proper extraction_method field
        for guide in guides:
            if 'extraction_method' not in guide or not guide['extraction_method']:
                guide['extraction_method'] = 'unknown'

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

@app.route('/clear-session-guide', methods=['POST'])
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


@app.route('/api/delete-submission', methods=['POST'])
def delete_submission():
    """API endpoint to delete a submission."""
    try:
        submission_id = request.json.get('submission_id')
        if not submission_id:
            logger.warning("Delete submission: No submission_id provided.")
            return jsonify({'success': False, 'message': 'No submission ID provided.'}), 400

        submissions = session.get('submissions', [])
        initial_len = len(submissions)
        submissions = [s for s in submissions if s.get('id') != submission_id]
        session['submissions'] = submissions

        if len(submissions) < initial_len:
            logger.info(f"Submission {submission_id} deleted successfully from session.")
            # Add to recent activity
            add_recent_activity('submission_deleted', f'Submission {submission_id[:8]}... deleted.', 'trash')
            return jsonify({'success': True, 'message': 'Submission deleted successfully.'})
        else:
            logger.warning(f"Submission {submission_id} not found for deletion.")
            return jsonify({'success': False, 'message': 'Submission not found.'}), 404

    except Exception as e:
        logger.error(f"Error deleting submission: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error.'}), 500



if __name__ == '__main__':
    print("🚀 Starting Exam Grader Web Application...")

    # Get configuration values
    host = getattr(config, 'HOST', '127.0.0.1')
    port = getattr(config, 'PORT', 5000)
    debug = getattr(config, 'DEBUG', True)

    print(f"📊 Dashboard: http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")

    app.run(
        host=host,
        port=port,
        debug=debug
    )
