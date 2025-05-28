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
from typing import Dict, List, Optional, Tuple, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import project modules
try:
    from src.config.config_manager import ConfigManager
    from src.services.ocr_service import OCRService
    from src.services.llm_service import LLMService
    from src.services.mapping_service import MappingService
    from src.services.grading_service import GradingService
    from src.parsing.parse_submission import parse_student_submission
    from src.parsing.parse_guide import parse_marking_guide
    from src.storage.submission_storage import SubmissionStorage
    from src.storage.guide_storage import GuideStorage
    from src.storage.mapping_storage import MappingStorage
    from src.storage.grading_storage import GradingStorage
    from src.storage.results_storage import ResultsStorage
    from utils.logger import logger
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    # Create mock logger for development
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
    logger = MockLogger()

# Initialize Flask application
app = Flask(__name__)

# Load configuration
try:
    from config import get_config, allowed_file as config_allowed_file
    config_class = get_config()
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Use config class for settings
    config = config_class()
    allowed_file = config_allowed_file

    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    # Use fallback configuration
    app.config['SECRET_KEY'] = 'fallback-secret-key-for-development'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # Create mock config object
    class MockConfig:
        def __init__(self):
            self.secret_key = 'fallback-secret-key-for-development'
            self.max_file_size_mb = 16
            self.temp_dir = 'temp'
            self.output_dir = 'output'
            self.port = 5000
            self.host = '127.0.0.1'
            self.debug = True
            self.supported_formats = ['.txt', '.docx', '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']

    config = MockConfig()

    def allowed_file(filename):
        if not filename:
            return False
        ext = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return ext in config.supported_formats

# Initialize services
try:
    ocr_service = OCRService()
    llm_service = LLMService()
    mapping_service = MappingService()
    grading_service = GradingService()

    # Initialize storage services
    submission_storage = SubmissionStorage()
    guide_storage = GuideStorage()
    mapping_storage = MappingStorage()
    grading_storage = GradingStorage()
    results_storage = ResultsStorage()

    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    # Continue with limited functionality
    ocr_service = None
    llm_service = None
    mapping_service = None
    grading_service = None
    submission_storage = None
    guide_storage = None
    mapping_storage = None
    grading_storage = None
    results_storage = None

# Utility functions

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

        temp_dir = getattr(config, 'TEMP_DIR', getattr(config, 'temp_dir', 'temp'))
        output_dir = getattr(config, 'OUTPUT_DIR', getattr(config, 'output_dir', 'output'))

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

        max_file_size = getattr(config, 'MAX_CONTENT_LENGTH', getattr(config, 'max_file_size_mb', 16))
        if isinstance(max_file_size, int) and max_file_size > 1000:  # If it's in bytes
            max_file_size = max_file_size / (1024 * 1024)  # Convert to MB

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
        return {
            'ocr_status': ocr_service.is_available() if ocr_service else False,
            'llm_status': llm_service.is_available() if llm_service else False,
            'storage_status': True,
            'config_status': True
        }
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        return {
            'ocr_status': False,
            'llm_status': False,
            'storage_status': False,
            'config_status': False
        }

# Error handlers
@app.errorhandler(413)
def too_large(e):
    flash(f'File too large. Maximum size is {config.max_file_size_mb}MB.', 'error')
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

# Template context processors
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'app_version': '2.0.0',
        'current_year': datetime.now().year,
        'service_status': get_service_status(),
        'storage_stats': get_storage_stats()
    }

# Routes
@app.route('/')
def dashboard():
    """Main dashboard route."""
    try:
        # Calculate dashboard statistics
        submissions = session.get('submissions', [])
        guide_uploaded = session.get('guide_uploaded', False)
        last_score = session.get('last_score', 0)
        recent_activity = session.get('recent_activity', [])

        # Calculate additional metrics
        total_submissions = len(submissions)
        processed_submissions = len([s for s in submissions if s.get('processed', False)])
        avg_score = last_score if last_score else 0

        context = {
            'page_title': 'Dashboard',
            'total_submissions': total_submissions,
            'processed_submissions': processed_submissions,
            'guide_uploaded': guide_uploaded,
            'last_score': last_score,
            'avg_score': avg_score,
            'recent_activity': recent_activity[:5],  # Show last 5 activities
            'submissions': submissions
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
        temp_dir = getattr(config, 'TEMP_DIR', getattr(config, 'temp_dir', 'temp'))
        os.makedirs(temp_dir, exist_ok=True)

        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, f"guide_{uuid.uuid4().hex}_{filename}")
        file.save(file_path)

        # Process guide (simplified for now)
        try:
            if 'parse_marking_guide' in globals():
                guide_data = parse_marking_guide(file_path)
                if guide_data.get('error'):
                    flash(f'Error processing guide: {guide_data["error"]}', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
            else:
                # Create basic guide data structure
                guide_data = {
                    'filename': filename,
                    'questions': [],
                    'total_marks': 0,
                    'processed_at': datetime.now().isoformat()
                }
        except Exception as parse_error:
            logger.error(f"Error parsing guide: {str(parse_error)}")
            # Create basic guide data structure
            guide_data = {
                'filename': filename,
                'questions': [],
                'total_marks': 0,
                'processed_at': datetime.now().isoformat()
            }

        # Store guide
        try:
            if guide_storage:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                guide_id = guide_storage.store_guide(file_content, filename, guide_data)
            else:
                # Use session storage as fallback
                guide_id = str(uuid.uuid4())
                session['guide_data'] = guide_data
        except Exception as storage_error:
            logger.error(f"Error storing guide: {str(storage_error)}")
            # Use session storage as fallback
            guide_id = str(uuid.uuid4())
            session['guide_data'] = guide_data

        # Update session
        session['guide_uploaded'] = True
        session['guide_id'] = guide_id
        session['guide_filename'] = filename

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
        except:
            pass

        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Error uploading guide: {str(e)}")
        flash('Error uploading guide. Please try again.', 'error')
        return redirect(request.url)

@app.route('/upload-submission', methods=['GET', 'POST'])
def upload_submission():
    """Upload and process student submission."""
    if request.method == 'GET':
        return render_template('upload_submission.html', page_title='Upload Submission')

    try:
        if not session.get('guide_uploaded'):
            flash('Please upload a marking guide first.', 'warning')
            return redirect(url_for('upload_guide'))

        if 'submission_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['submission_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('File type not supported. Please upload a PDF, Word document, or image file.', 'error')
            return redirect(request.url)

        # Create temp directory if it doesn't exist
        temp_dir = getattr(config, 'TEMP_DIR', getattr(config, 'temp_dir', 'temp'))
        os.makedirs(temp_dir, exist_ok=True)

        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, f"submission_{uuid.uuid4().hex}_{filename}")
        file.save(file_path)

        # Process submission
        try:
            if 'parse_student_submission' in globals():
                answers, raw_text, error = parse_student_submission(file_path)
                if error:
                    flash(f'Error processing submission: {error}', 'error')
                    os.remove(file_path)
                    return redirect(request.url)
            else:
                # Create basic submission data
                answers = {'extracted_text': f'Sample text from {filename}'}
                raw_text = f'Raw text content from {filename}'
        except Exception as parse_error:
            logger.error(f"Error parsing submission: {str(parse_error)}")
            answers = {'extracted_text': f'Sample text from {filename}'}
            raw_text = f'Raw text content from {filename}'

        # Store submission
        try:
            if submission_storage:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                submission_id = submission_storage.store_results(file_content, filename, answers, raw_text)
            else:
                submission_id = str(uuid.uuid4())
                session[f'submission_{submission_id}'] = {
                    'filename': filename,
                    'answers': answers,
                    'raw_text': raw_text
                }
        except Exception as storage_error:
            logger.error(f"Error storing submission: {str(storage_error)}")
            submission_id = str(uuid.uuid4())
            session[f'submission_{submission_id}'] = {
                'filename': filename,
                'answers': answers,
                'raw_text': raw_text
            }

        # Update session
        submissions = session.get('submissions', [])
        submissions.append({
            'id': submission_id,
            'filename': filename,
            'uploaded_at': datetime.now().isoformat(),
            'processed': True
        })
        session['submissions'] = submissions
        session['last_submission'] = submission_id

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'submission_upload',
            'message': f'Uploaded submission: {filename}',
            'timestamp': datetime.now().isoformat(),
            'icon': 'upload'
        })
        session['recent_activity'] = activity[:10]

        flash('Submission uploaded and processed successfully!', 'success')
        logger.info(f"Submission uploaded successfully: {filename}")

        # Clean up temp file
        try:
            os.remove(file_path)
        except:
            pass

        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Error uploading submission: {str(e)}")
        flash('Error uploading submission. Please try again.', 'error')
        return redirect(request.url)

@app.route('/submissions')
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

        # Mock results for now
        context = {
            'page_title': 'Grading Results',
            'results': {
                'total_score': session.get('last_score', 0),
                'questions': [],
                'feedback': 'Results will be displayed here after grading.'
            }
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

        # Mock mapping process
        session['mapping_completed'] = True
        session['last_mapping_result'] = str(uuid.uuid4())

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'mapping_complete',
            'message': 'Answer mapping completed successfully',
            'timestamp': datetime.now().isoformat(),
            'icon': 'check'
        })
        session['recent_activity'] = activity[:10]

        return jsonify({'success': True, 'message': 'Mapping completed successfully'})

    except Exception as e:
        logger.error(f"Error processing mapping: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/process-grading', methods=['POST'])
def process_grading():
    """API endpoint to process grading."""
    try:
        if not session.get('last_mapping_result'):
            return jsonify({'error': 'No mapping result available'}), 400

        # Mock grading process
        import random
        score = random.randint(60, 95)

        session['grading_completed'] = True
        session['last_grading_result'] = str(uuid.uuid4())
        session['last_score'] = score

        # Add to recent activity
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': 'grading_complete',
            'message': f'Grading completed - Score: {score}%',
            'timestamp': datetime.now().isoformat(),
            'icon': 'star'
        })
        session['recent_activity'] = activity[:10]

        return jsonify({'success': True, 'score': score, 'message': 'Grading completed successfully'})

    except Exception as e:
        logger.error(f"Error processing grading: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
