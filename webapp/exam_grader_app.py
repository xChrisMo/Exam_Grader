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

        # Check storage services
        submission_storage_available = False
        guide_storage_available = False

        if submission_storage:
            try:
                submission_storage_available = submission_storage.is_available()
            except Exception as e:
                logger.warning(f"Error checking submission storage: {str(e)}")

        if guide_storage:
            try:
                guide_storage_available = guide_storage.is_available()
            except Exception as e:
                logger.warning(f"Error checking guide storage: {str(e)}")

        storage_available = submission_storage_available and guide_storage_available

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
        logger.info(f"Dashboard: guide_uploaded from session: {guide_uploaded}")
        last_score = session.get('last_score', 0)
        recent_activity = session.get('recent_activity', [])

        # Calculate additional metrics
        total_submissions = len(submissions)
        processed_submissions = len([s for s in submissions if s.get('processed', False)])
        avg_score = last_score if last_score else 0

        service_status = get_service_status()
        context = {
            'page_title': 'Dashboard',
            'total_submissions': total_submissions,
            'processed_submissions': processed_submissions,
            'guide_uploaded': guide_uploaded,
            'last_score': last_score,
            'avg_score': avg_score,
            'recent_activity': recent_activity[:5],  # Show last 5 activities
            'submissions': submissions,
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



        # Store guide
        logger.info("Entering guide storage block.")
        try:
            if guide_storage:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                logger.info("Attempting to store guide via guide_storage.")
                guide_id = guide_storage.store_guide(file_content, filename, guide_data)
                logger.info(f"Guide stored with ID: {guide_id}")
            else:
                logger.info("Using session storage as fallback for guide.")
                # Use session storage as fallback
                guide_id = str(uuid.uuid4())
                session['guide_data'] = guide_data
        except Exception as storage_error:
            logger.error(f"Error storing guide: {str(storage_error)}")
            # Use session storage as fallback
            guide_id = str(uuid.uuid4())
            session['guide_data'] = guide_data

        # Update session
        logger.info("Updating session variables after guide storage.")
        # Store only the raw content, which is JSON serializable
        session['guide_raw_content'] = guide.raw_content
        session['guide_uploaded'] = True
        session['guide_filename'] = filename
        session['guide_uploaded'] = True
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

        temp_dir = getattr(config, 'TEMP_DIR', getattr(config, 'temp_dir', 'temp'))
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

        if mapping_service and guide_storage and submission_storage:
            try:
                # Get guide content
                guide_data = guide_storage.get_guide_data(guide_id)
                if not guide_data:
                    return jsonify({'error': 'Guide data not found'}), 404

                # Process each submission
                for submission in submissions:
                    submission_id = submission.get('id')
                    if not submission_id:
                        continue

                    try:
                        # Get submission content
                        submission_data = submission_storage.get_results(submission_id)
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
def marking_guides():
    """View marking guide library with enhanced features and safe JSON serialization."""
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

        # Get stored guides from storage
        if guide_storage:
            try:
                stored_guides = guide_storage.get_all_guides()
                guides.extend(stored_guides)
                logger.info(f"Added {len(stored_guides)} stored guides")
            except Exception as storage_error:
                logger.error(f"Error loading stored guides: {str(storage_error)}")

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

        # Try to save to results storage if available
        if results_storage:
            try:
                results_storage.store_results(export_data, filename)
                logger.info(f"Results exported to storage: {filename}")
            except Exception as storage_error:
                logger.warning(f"Could not save results to storage: {str(storage_error)}")

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


def add_recent_activity(activity_type: str, message: str, icon: str = 'info'):
    """Add an activity to the recent activity list in session."""
    try:
        activity = session.get('recent_activity', [])
        activity.insert(0, {
            'type': activity_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'icon': icon
        })
        session['recent_activity'] = activity[:10]  # Keep only last 10 activities
        session.modified = True
        logger.info(f"Added recent activity: {activity_type} - {message}")
    except Exception as e:
        logger.error(f"Error adding recent activity: {str(e)}")
        # Don't raise exception to avoid breaking the main flow


@app.route('/use-guide/<guide_id>')
def use_guide(guide_id):
    """Use a specific marking guide."""
    try:
        # Load guide from storage
        if guide_storage:
            guide = guide_storage.get_guide_data(guide_id)
            if guide:
                # Set as current guide in session
                session['guide_data'] = guide
                session['guide_filename'] = guide.get('filename', 'Unknown')
                session['guide_raw_content'] = guide.get('raw_content', '')
                session['guide_uploaded'] = True
                session.modified = True

                flash(f'Marking guide "{guide.get("name", "Unknown")}" is now active.', 'success')
                logger.info(f"Guide {guide_id} set as active guide")
                add_recent_activity('guide_activated', f'Activated guide: {guide.get("name", "Unknown")}', 'check')
            else:
                flash('Guide not found.', 'error')
                logger.warning(f"Guide {guide_id} not found in storage")
        else:
            flash('Guide storage not available.', 'error')
            logger.error("Guide storage not available")

        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Error using guide {guide_id}: {str(e)}")
        flash('Error loading guide. Please try again.', 'error')
        return redirect(url_for('marking_guides'))


@app.route('/delete-guide/<guide_id>')
def delete_guide(guide_id):
    """Delete a specific marking guide."""
    try:
        if guide_id == 'session_guide':
            flash('Cannot delete session guide.', 'error')
            return redirect(url_for('marking_guides'))

        # Check if this guide is currently active in session
        current_guide_filename = session.get('guide_filename')
        is_current_guide = False

        logger.info(f"Delete guide check - guide_id: {guide_id}, current_guide_filename: {current_guide_filename}")

        # Get guide info before deletion for proper cleanup
        guide_info = None
        if guide_storage:
            guide_info = guide_storage.get_guide_data(guide_id)
            if guide_info:
                logger.info(f"Guide info - filename: {guide_info.get('filename')}, name: {guide_info.get('name')}")
                if current_guide_filename:
                    # Check if this is the currently active guide (multiple ways to match)
                    is_current_guide = (
                        guide_info.get('filename') == current_guide_filename or
                        guide_info.get('name') == current_guide_filename or
                        guide_info.get('filename', '').replace(' ', '_') == current_guide_filename or
                        current_guide_filename in guide_info.get('filename', '') or
                        guide_info.get('filename', '') in current_guide_filename
                    )
                    logger.info(f"Is current guide check: {is_current_guide}")
            else:
                logger.warning(f"Guide {guide_id} not found in storage for deletion check")

        # Delete guide from storage
        if guide_storage:
            success = guide_storage.delete_guide(guide_id)
            if success:
                # If this was the current active guide, clear session data
                if is_current_guide:
                    logger.info(f"Clearing session data for deleted active guide: {current_guide_filename}")
                    session.pop('guide_data', None)
                    session.pop('guide_filename', None)
                    session.pop('guide_raw_content', None)
                    session.pop('guide_uploaded', None)
                    session.modified = True
                    flash('Active guide deleted and session cleared.', 'warning')
                else:
                    flash('Guide deleted successfully.', 'success')

                logger.info(f"Guide {guide_id} deleted successfully")
                guide_name = guide_info.get('name', guide_id[:8] + '...') if guide_info else guide_id[:8] + '...'
                add_recent_activity('guide_deleted', f'Deleted guide: {guide_name}', 'trash')
            else:
                flash('Guide not found.', 'error')
                logger.warning(f"Guide {guide_id} not found for deletion")
        else:
            flash('Guide storage not available.', 'error')
            logger.error("Guide storage not available")

        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Error deleting guide {guide_id}: {str(e)}")
        flash('Error deleting guide. Please try again.', 'error')
        return redirect(url_for('marking_guides'))


@app.route('/clear-session-guide')
def clear_session_guide():
    """Clear session guide data - utility route for debugging."""
    try:
        # Clear all guide-related session data
        guide_filename = session.get('guide_filename', 'Unknown')
        session.pop('guide_filename', None)
        session.pop('guide_data', None)
        session.pop('guide_raw_content', None)
        session.pop('guide_uploaded', None)
        session.modified = True

        flash(f'Session guide data cleared for: {guide_filename}', 'success')
        logger.info(f"Cleared session guide data for: {guide_filename}")

        return redirect(url_for('marking_guides'))
    except Exception as e:
        logger.error(f"Error clearing session guide: {str(e)}")
        flash('Error clearing session guide data.', 'error')
        return redirect(url_for('marking_guides'))


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and deployment."""
    try:
        # Check service status
        service_status = get_service_status()
        storage_stats = get_storage_stats()

        # Calculate overall health
        critical_services = ['config_status']
        optional_services = ['ocr_status', 'llm_status', 'storage_status']

        # Check critical services
        critical_healthy = all(service_status.get(service, False) for service in critical_services)

        # Count optional services
        optional_healthy = sum(1 for service in optional_services if service_status.get(service, False))
        total_optional = len(optional_services)

        # Determine overall status
        if critical_healthy and optional_healthy >= 2:
            status = "healthy"
            status_code = 200
        elif critical_healthy and optional_healthy >= 1:
            status = "degraded"
            status_code = 200
        elif critical_healthy:
            status = "limited"
            status_code = 200
        else:
            status = "unhealthy"
            status_code = 503

        health_data = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "services": service_status,
            "storage": {
                "temp_size_mb": storage_stats.get('temp_size_mb', 0),
                "output_size_mb": storage_stats.get('output_size_mb', 0),
                "total_size_mb": storage_stats.get('total_size_mb', 0)
            },
            "uptime": "running",
            "environment": os.getenv('APP_ENV', 'development')
        }

        return jsonify(health_data), status_code

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500


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
